#!/usr/bin/env python3
"""Validate a research-run package and its cross-file references."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "goal_contract.json",
    "run_manifest.json",
    "data_dictionary.json",
    "coverage_plan.json",
    "sources.jsonl",
    "coverage.jsonl",
    "observations.jsonl",
    "tasks.jsonl",
    "claims.jsonl",
    "current_view.jsonl",
    "conflicts.jsonl",
)
COVERAGE_STATES = {"checked_hit", "checked_no_confirmation", "blocked", "unchecked"}
TASK_STATES = {"pending", "leased", "completed", "blocked", "failed", "cancelled"}
ACTIVE_TASK_STATES = {"pending", "leased"}
FIELD_KINDS = {"static", "slowly_changing", "dynamic"}
SOURCE_STRENGTHS = {"direct_primary", "official_secondary", "independent_secondary", "weak_signal", "unknown"}
SOURCE_STATES = {"ready", "degraded", "blocked", "unknown"}
ACCESS_CLASSES = {"public", "internal", "private", "restricted"}


def stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name}: expected a JSON object")
        return {}
    return value


def load_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        errors.append(f"{path.name}: {exc}")
        return rows
    for line_no, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{line_no}: invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.name}:{line_no}: expected a JSON object")
            continue
        value["_line"] = line_no
        rows.append(value)
    return rows


def require(row: dict[str, Any], fields: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(field for field in fields if field not in row)
    if missing:
        errors.append(f"{label}: missing {missing}")


def duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def as_list(value: Any, label: str, errors: list[str]) -> list[Any]:
    if isinstance(value, list):
        return value
    errors.append(f"{label}: expected a list")
    return []


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    return p


def main() -> int:
    args = parser().parse_args()
    root = Path(args.run_directory).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for name in REQUIRED_FILES:
        if not (root / name).is_file():
            errors.append(f"missing required file: {name}")
    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        return 1

    goal = load_json(root / "goal_contract.json", errors)
    manifest = load_json(root / "run_manifest.json", errors)
    data_dictionary = load_json(root / "data_dictionary.json", errors)
    coverage_plan = load_json(root / "coverage_plan.json", errors)
    require(
        goal,
        {"schema_version", "goal_id", "goal", "decision_use", "mode", "depth", "in_scope", "out_of_scope", "deliverables", "must_preserve", "success_conditions", "stop_conditions", "assumptions", "as_of", "change_log"},
        "goal_contract.json",
        errors,
    )
    require(
        manifest,
        {"schema_version", "run_id", "goal_id", "mode", "depth", "created_at", "as_of", "input_snapshot", "status"},
        "run_manifest.json",
        errors,
    )
    for field in ("schema_version", "goal_id", "mode", "depth", "as_of"):
        if goal.get(field) != manifest.get(field):
            errors.append(f"goal_contract.json and run_manifest.json disagree on {field}")
    if goal.get("depth") not in {"quick", "standard", "exhaustive"}:
        errors.append(f"invalid depth: {goal.get('depth')!r}")
    if manifest.get("input_snapshot") and stable_hash(goal) != manifest.get("input_snapshot"):
        errors.append("goal_contract.json no longer matches run_manifest.json input_snapshot")

    require(data_dictionary, {"schema_version", "goal_id", "unit_of_analysis", "key_fields", "fields"}, "data_dictionary.json", errors)
    require(coverage_plan, {"schema_version", "goal_id", "dimensions", "required_source_classes", "required_cells", "completion_rule"}, "coverage_plan.json", errors)
    for name, value in (("data_dictionary.json", data_dictionary), ("coverage_plan.json", coverage_plan)):
        if value.get("schema_version") != manifest.get("schema_version"):
            errors.append(f"{name}: schema_version mismatch")
        if value.get("goal_id") != manifest.get("goal_id"):
            errors.append(f"{name}: goal_id mismatch")

    sources = load_jsonl(root / "sources.jsonl", errors)
    coverage = load_jsonl(root / "coverage.jsonl", errors)
    observations = load_jsonl(root / "observations.jsonl", errors)
    tasks = load_jsonl(root / "tasks.jsonl", errors)
    claims = load_jsonl(root / "claims.jsonl", errors)
    current = load_jsonl(root / "current_view.jsonl", errors)
    conflicts = load_jsonl(root / "conflicts.jsonl", errors)

    source_ids: set[str] = set()
    for row in sources:
        label = f"sources.jsonl:{row['_line']}"
        require(row, {"source_id", "source_type", "strength_grade", "access_class", "locator", "retrieved_at", "state"}, label, errors)
        if row.get("strength_grade") not in SOURCE_STRENGTHS:
            errors.append(f"{label}: invalid strength_grade {row.get('strength_grade')!r}")
        if row.get("state") not in SOURCE_STATES:
            errors.append(f"{label}: invalid state {row.get('state')!r}")
        if row.get("access_class") not in ACCESS_CLASSES:
            errors.append(f"{label}: invalid access_class {row.get('access_class')!r}")
        if row.get("source_id") in source_ids:
            errors.append(f"{label}: duplicate source_id {row.get('source_id')!r}")
        source_ids.add(row.get("source_id"))

    cell_attempt_ids: list[str] = []
    for row in coverage:
        label = f"coverage.jsonl:{row['_line']}"
        require(row, {"attempt_id", "cell_id", "run_id", "source_class", "object_scope", "field_scope", "market", "state", "retrieved_at"}, label, errors)
        if row.get("state") not in COVERAGE_STATES:
            errors.append(f"{label}: invalid state {row.get('state')!r}")
        if row.get("state") == "blocked" and not row.get("blocker_reason"):
            errors.append(f"{label}: blocked state requires blocker_reason")
        for source_id in as_list(row.get("source_ids", []), f"{label}.source_ids", errors):
            if source_id not in source_ids:
                errors.append(f"{label}: unknown source_id {source_id!r}")
        cell_attempt_ids.append(row.get("attempt_id"))
    for value in duplicates([v for v in cell_attempt_ids if isinstance(v, str)]):
        errors.append(f"duplicate coverage attempt_id {value!r}")

    observation_ids: set[str] = set()
    observation_keys: set[str] = set()
    for row in observations:
        label = f"observations.jsonl:{row['_line']}"
        require(
            row,
            {"observation_id", "run_id", "observation_key", "object_type", "object_id", "field", "field_kind", "value", "source_id", "evidence_type", "source_strength", "observed_at", "retrieved_at", "route_version", "parser_version", "raw_hash"},
            label,
            errors,
        )
        if row.get("observation_id") in observation_ids:
            errors.append(f"{label}: duplicate observation_id {row.get('observation_id')!r}")
        observation_ids.add(row.get("observation_id"))
        if row.get("observation_key"):
            observation_keys.add(row["observation_key"])
        if row.get("source_id") not in source_ids:
            errors.append(f"{label}: unknown source_id {row.get('source_id')!r}")
        if row.get("field_kind") not in FIELD_KINDS:
            errors.append(f"{label}: invalid field_kind {row.get('field_kind')!r}")
        if row.get("source_strength") not in SOURCE_STRENGTHS:
            errors.append(f"{label}: invalid source_strength {row.get('source_strength')!r}")

    task_ids: set[str] = set()
    active_partitions: list[str] = []
    for row in tasks:
        label = f"tasks.jsonl:{row['_line']}"
        require(row, {"task_id", "goal_id", "input_snapshot", "partition_key", "owner", "status", "attempt"}, label, errors)
        if row.get("task_id") in task_ids:
            errors.append(f"{label}: duplicate task_id {row.get('task_id')!r}")
        task_ids.add(row.get("task_id"))
        if row.get("goal_id") != manifest.get("goal_id"):
            errors.append(f"{label}: goal_id mismatch")
        if row.get("input_snapshot") != manifest.get("input_snapshot"):
            errors.append(f"{label}: input_snapshot mismatch")
        if row.get("status") not in TASK_STATES:
            errors.append(f"{label}: invalid status {row.get('status')!r}")
        if row.get("status") in ACTIVE_TASK_STATES and row.get("partition_key"):
            active_partitions.append(row["partition_key"])
    for value in duplicates(active_partitions):
        errors.append(f"multiple active task leases for partition_key {value!r}")

    claim_ids: set[str] = set()
    for row in claims:
        label = f"claims.jsonl:{row['_line']}"
        require(row, {"claim_id", "text", "status", "confidence", "source_ids", "counterevidence_source_ids", "gap_ids"}, label, errors)
        if row.get("claim_id") in claim_ids:
            errors.append(f"{label}: duplicate claim_id {row.get('claim_id')!r}")
        claim_ids.add(row.get("claim_id"))
        support = as_list(row.get("source_ids"), f"{label}.source_ids", errors)
        counter = as_list(row.get("counterevidence_source_ids"), f"{label}.counterevidence_source_ids", errors)
        as_list(row.get("gap_ids"), f"{label}.gap_ids", errors)
        for source_id in support + counter:
            if source_id not in source_ids:
                errors.append(f"{label}: unknown source_id {source_id!r}")

    current_keys: list[str] = []
    for row in current:
        label = f"current_view.jsonl:{row['_line']}"
        require(row, {"observation_key", "selected_from_observation_id"}, label, errors)
        current_keys.append(row.get("observation_key"))
        if row.get("selected_from_observation_id") not in observation_ids:
            errors.append(f"{label}: selected observation does not exist")
    for value in duplicates([v for v in current_keys if isinstance(v, str)]):
        errors.append(f"duplicate current_view observation_key {value!r}")

    for row in conflicts:
        label = f"conflicts.jsonl:{row['_line']}"
        require(row, {"observation_key", "conflict_type", "selected_observation_id", "alternative_observation_ids"}, label, errors)
        selected = row.get("selected_observation_id")
        if selected is not None and selected not in observation_ids:
            errors.append(f"{label}: selected observation does not exist")
        for observation_id in as_list(row.get("alternative_observation_ids"), f"{label}.alternative_observation_ids", errors):
            if observation_id not in observation_ids:
                errors.append(f"{label}: unknown alternative observation {observation_id!r}")

    if observations and not coverage:
        warnings.append("observations exist but coverage.jsonl is empty")
    if goal.get("depth") in {"standard", "exhaustive"} and not data_dictionary.get("unit_of_analysis"):
        warnings.append("data_dictionary.json has no unit_of_analysis")
    if goal.get("depth") in {"standard", "exhaustive"} and not coverage_plan.get("required_source_classes"):
        warnings.append("coverage_plan.json has no required_source_classes")
    if goal.get("depth") == "exhaustive" and not coverage_plan.get("required_cells"):
        errors.append("exhaustive run has no required coverage cells")
    if goal.get("depth") == "exhaustive" and not goal.get("stop_conditions"):
        warnings.append("exhaustive run has no explicit stop_conditions")
    if claims and not current and observations:
        warnings.append("claims exist but current_view.jsonl is empty")

    if args.strict and warnings:
        errors.extend(f"strict: {warning}" for warning in warnings)

    summary = {
        "sources": len(sources),
        "coverage_attempts": len(coverage),
        "observations": len(observations),
        "tasks": len(tasks),
        "claims": len(claims),
        "current_rows": len(current),
        "conflicts": len(conflicts),
        "warnings": len(warnings),
        "errors": len(errors),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
