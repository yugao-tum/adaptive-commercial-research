#!/usr/bin/env python3
"""Validate real target-field outcomes from a pilot before broad collection."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TERMINAL_COVERAGE_STATES = {"checked_hit", "checked_no_confirmation", "blocked"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected a JSON object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name}:{line_no}: expected a JSON object")
        value["_line"] = line_no
        rows.append(value)
    return rows


def row_order(row: dict[str, Any]) -> tuple[str, str, int]:
    return (str(row.get("retrieved_at") or ""), str(row.get("attempt_id") or ""), int(row.get("_line", 0)))


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("--target-id", action="append", default=[])
    p.add_argument("--batch-id", action="append", default=[])
    p.add_argument("--shard-id", action="append", type=int, default=[])
    p.add_argument("--output")
    p.add_argument("--strict", action="store_true", help="Fail on unchecked or internally inconsistent target-field cells")
    return p


def main() -> int:
    args = parser().parse_args()
    root = Path(args.run_directory).expanduser().resolve()
    field_contract = load_json(root / "field_contract.json")
    targets = load_jsonl(root / "target_queue.jsonl")
    coverage = load_jsonl(root / "coverage.jsonl")
    observations = load_jsonl(root / "observations.jsonl")

    target_ids = set(args.target_id)
    batch_ids = set(args.batch_id)
    shard_ids = set(args.shard_id)
    selected = []
    for row in targets:
        if target_ids and row.get("target_id") not in target_ids:
            continue
        if batch_ids and row.get("batch_id") not in batch_ids:
            continue
        if shard_ids and row.get("shard_id") not in shard_ids:
            continue
        selected.append(row)
    selected_ids = {str(row.get("target_id")) for row in selected}
    if not selected:
        print("ERROR: no pilot targets matched the filters", file=sys.stderr)
        return 2

    allowed_fields = set(field_contract.get("required_fields", [])) | set(field_contract.get("optional_fields", []))
    extractor_fields = set(field_contract.get("extractor_output_fields", []))
    errors: list[str] = []
    warnings: list[str] = []
    latest_coverage: dict[tuple[str, str], dict[str, Any]] = {}
    for row in coverage:
        target_id = str(row.get("target_id") or "")
        field = str(row.get("field_scope") or "")
        if target_id not in selected_ids or not field:
            continue
        key = (target_id, field)
        if key not in latest_coverage or row_order(row) > row_order(latest_coverage[key]):
            latest_coverage[key] = row

    observations_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        target_id = str(row.get("target_id") or "")
        field = str(row.get("field") or "")
        if target_id in selected_ids:
            observations_by_cell[(target_id, field)].append(row)
            if field not in allowed_fields:
                errors.append(f"observations.jsonl:{row['_line']}: field {field!r} is outside the field contract")
            if field not in extractor_fields:
                errors.append(f"observations.jsonl:{row['_line']}: field {field!r} is not declared by the extractor")

    field_states: dict[str, Counter[str]] = defaultdict(Counter)
    terminal_targets = 0
    planned_cells = 0
    terminal_cells = 0
    hit_cells = 0
    for target in selected:
        target_id = str(target.get("target_id"))
        fields = target.get("coverage_fields", [])
        if not isinstance(fields, list):
            errors.append(f"target {target_id}: coverage_fields must be a list")
            continue
        target_terminal = True
        for field in fields:
            planned_cells += 1
            key = (target_id, str(field))
            state = str(latest_coverage.get(key, {}).get("state") or "unchecked")
            field_states[str(field)][state] += 1
            terminal = state in TERMINAL_COVERAGE_STATES
            if terminal:
                terminal_cells += 1
            else:
                target_terminal = False
                message = f"target {target_id} field {field}: no terminal pilot outcome"
                (errors if args.strict else warnings).append(message)
            observed = bool(observations_by_cell.get(key))
            if state == "checked_hit":
                hit_cells += 1
                if not observed:
                    errors.append(f"target {target_id} field {field}: checked_hit has no observation")
            elif observed:
                errors.append(f"target {target_id} field {field}: observation conflicts with coverage state {state!r}")
        if target_terminal:
            terminal_targets += 1

    summary = {
        "selected_targets": len(selected),
        "planned_target_field_cells": planned_cells,
        "terminal_target_field_cells": terminal_cells,
        "target_field_terminalization_rate": rate(terminal_cells, planned_cells),
        "terminal_targets": terminal_targets,
        "target_terminalization_rate": rate(terminal_targets, len(selected)),
        "hit_cells": hit_cells,
        "observations": sum(len(rows) for rows in observations_by_cell.values()),
        "fields": {field: dict(sorted(states.items())) for field, states in sorted(field_states.items())},
        "warnings": len(warnings),
        "errors": len(errors),
        "passed": not errors and (not args.strict or not warnings),
    }
    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
