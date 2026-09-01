#!/usr/bin/env python3
"""Create a versioned research-run package without overwriting existing work."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.4.0"
JSONL_FILES = (
    "sources.jsonl",
    "target_queue.jsonl",
    "collection_attempts.jsonl",
    "coverage.jsonl",
    "observations.jsonl",
    "raw_artifacts.jsonl",
    "tasks.jsonl",
    "claims.jsonl",
    "current_view.jsonl",
    "conflicts.jsonl",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, help="New or empty run directory")
    p.add_argument("--goal", required=True, help="Concrete research objective")
    p.add_argument("--decision-use", required=True, help="Decision the research will support")
    p.add_argument(
        "--mode",
        required=True,
        choices=("operating-architecture", "coverage-sweep", "structured-extraction", "enrichment-audit", "mixed"),
    )
    p.add_argument("--depth", required=True, choices=("quick", "standard", "exhaustive"))
    p.add_argument("--in-scope", action="append", default=[])
    p.add_argument("--out-of-scope", action="append", default=[])
    p.add_argument("--required-field", action="append", default=[], help="Field required for acceptance")
    p.add_argument("--optional-field", action="append", default=[], help="In-scope field collected when evidence exposes it")
    p.add_argument("--excluded-field", action="append", default=[], help="Field excluded from retrieval and acceptance")
    p.add_argument("--deliverable", action="append", default=[])
    p.add_argument("--must-preserve", action="append", default=[])
    p.add_argument("--success", action="append", default=[])
    p.add_argument("--stop", action="append", default=[])
    p.add_argument("--assumption", action="append", default=[])
    p.add_argument(
        "--cost-unit",
        help="Single unit used by every collection_attempts.jsonl cost value, for example USD or credits",
    )
    p.add_argument("--as-of", help="Research time boundary; defaults to current UTC time")
    p.add_argument("--goal-id", help="Existing goal ID; generated when omitted")
    p.add_argument("--run-id", help="Existing run ID; generated when omitted")
    return p


def main() -> int:
    args = parser().parse_args()
    field_groups: dict[str, list[str]] = {}
    for label, raw_values in (
        ("required", args.required_field),
        ("optional", args.optional_field),
        ("excluded", args.excluded_field),
    ):
        values = [value.strip() for value in raw_values]
        if any(not value for value in values):
            print(f"Refusing empty {label} field name", file=sys.stderr)
            return 2
        if len(values) != len(set(values)):
            print(f"Refusing duplicate {label} field names", file=sys.stderr)
            return 2
        field_groups[label] = values
    for left, right in (("required", "optional"), ("required", "excluded"), ("optional", "excluded")):
        overlap = sorted(set(field_groups[left]) & set(field_groups[right]))
        if overlap:
            print(f"Field sets {left} and {right} overlap: {overlap}", file=sys.stderr)
            return 2

    output = Path(args.output).expanduser().resolve()
    if output.exists() and not output.is_dir():
        print(f"Refusing to initialize over a file: {output}", file=sys.stderr)
        return 2
    if output.exists() and any(output.iterdir()):
        print(f"Refusing to initialize non-empty directory: {output}", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)

    goal_id = args.goal_id or f"goal-{uuid.uuid4()}"
    run_id = args.run_id or f"run-{uuid.uuid4()}"
    created_at = utc_now()
    as_of = args.as_of or created_at

    contract = {
        "schema_version": SCHEMA_VERSION,
        "goal_id": goal_id,
        "goal": args.goal,
        "decision_use": args.decision_use,
        "mode": args.mode,
        "depth": args.depth,
        "in_scope": args.in_scope,
        "out_of_scope": args.out_of_scope,
        "required_fields": field_groups["required"],
        "optional_fields": field_groups["optional"],
        "excluded_fields": field_groups["excluded"],
        "deliverables": args.deliverable,
        "must_preserve": args.must_preserve,
        "success_conditions": args.success,
        "stop_conditions": args.stop,
        "assumptions": args.assumption,
        "as_of": as_of,
        "change_log": [],
    }
    snapshot = stable_hash(contract)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "goal_id": goal_id,
        "mode": args.mode,
        "depth": args.depth,
        "created_at": created_at,
        "as_of": as_of,
        "input_snapshot": snapshot,
        "cost_unit": args.cost_unit,
        "coordination": {
            "assessed": False,
            "independent_lane_count": 0,
            "child_agent_decision": "unassessed",
            "child_agent_reason": None,
            "external_executor_decisions": [],
        },
        "route_registry_version": None,
        "parser_versions": {},
        "status": "initialized",
    }
    data_dictionary = {
        "schema_version": SCHEMA_VERSION,
        "goal_id": goal_id,
        "unit_of_analysis": None,
        "key_fields": [],
        "fields": {
            field: {}
            for field in field_groups["required"] + field_groups["optional"]
        },
    }
    field_contract = {
        "schema_version": SCHEMA_VERSION,
        "goal_id": goal_id,
        "required_fields": field_groups["required"],
        "optional_fields": field_groups["optional"],
        "excluded_fields": field_groups["excluded"],
        "extractor_output_fields": [],
        "acceptance_fields": [],
    }
    coverage_plan = {
        "schema_version": SCHEMA_VERSION,
        "goal_id": goal_id,
        "dimensions": [],
        "required_source_classes": [],
        "required_cells": [],
        "required_fields": field_groups["required"],
        "completion_rule": None,
    }

    write_json(output / "goal_contract.json", contract)
    write_json(output / "run_manifest.json", manifest)
    write_json(output / "data_dictionary.json", data_dictionary)
    write_json(output / "field_contract.json", field_contract)
    write_json(output / "coverage_plan.json", coverage_plan)
    for name in JSONL_FILES:
        (output / name).write_text("", encoding="utf-8")

    print(
        json.dumps(
            {
                "run_directory": str(output),
                "schema_version": SCHEMA_VERSION,
                "goal_id": goal_id,
                "run_id": run_id,
                "depth": args.depth,
                "mode": args.mode,
                "input_snapshot": snapshot,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
