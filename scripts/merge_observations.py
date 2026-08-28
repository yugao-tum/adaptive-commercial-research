#!/usr/bin/env python3
"""Deterministically materialize append-only research observations."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REQUIRED = {
    "observation_id",
    "run_id",
    "observation_key",
    "object_type",
    "object_id",
    "field",
    "field_kind",
    "value",
    "source_id",
    "evidence_type",
    "source_strength",
    "observed_at",
    "retrieved_at",
    "route_version",
    "parser_version",
    "raw_hash",
}
FIELD_KINDS = {"static", "slowly_changing", "dynamic"}
STRENGTH = {
    "unknown": 0,
    "weak_signal": 1,
    "independent_secondary": 2,
    "official_secondary": 3,
    "direct_primary": 4,
}


def parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty ISO-8601 string")
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_no, raw in enumerate(handle, 1):
                if not raw.strip():
                    continue
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"{path}:{line_no}: expected a JSON object")
                value["_input_path"] = str(path)
                value["_input_line"] = line_no
                records.append(value)
    return records


def validate(record: dict[str, Any]) -> None:
    missing = sorted(REQUIRED - record.keys())
    if missing:
        raise ValueError(f"{record.get('_input_path')}:{record.get('_input_line')}: missing {missing}")
    if record["field_kind"] not in FIELD_KINDS:
        raise ValueError(f"{record['observation_id']}: invalid field_kind {record['field_kind']!r}")
    if record["source_strength"] not in STRENGTH:
        raise ValueError(f"{record['observation_id']}: invalid source_strength {record['source_strength']!r}")
    parse_time(record["observed_at"], f"{record['observation_id']}.observed_at")
    parse_time(record["retrieved_at"], f"{record['observation_id']}.retrieved_at")


def rank(record: dict[str, Any]) -> tuple[Any, ...]:
    observed = parse_time(record["observed_at"], "observed_at")
    retrieved = parse_time(record["retrieved_at"], "retrieved_at")
    strength = STRENGTH[record["source_strength"]]
    if record["field_kind"] == "dynamic":
        return (observed, strength, retrieved, record["observation_id"])
    return (strength, observed, retrieved, record["observation_id"])


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+", help="Observation JSONL files")
    p.add_argument("--output", required=True, help="Materialized current-view JSONL")
    p.add_argument("--conflicts", required=True, help="Conflict JSONL")
    p.add_argument(
        "--current-run-id",
        help="When set, dynamic fields with no valid observation in this run are omitted rather than silently backfilled",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    records = read_jsonl(Path(p).expanduser().resolve() for p in args.inputs)

    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        validate(record)
        clean = {k: v for k, v in record.items() if not k.startswith("_input_")}
        observation_id = clean["observation_id"]
        if observation_id in by_id and canonical(by_id[observation_id]) != canonical(clean):
            raise ValueError(f"observation_id {observation_id!r} has conflicting payloads")
        by_id[observation_id] = clean

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in by_id.values():
        if record["value"] is not None and record.get("value_state", "present") == "present":
            groups[record["observation_key"]].append(record)

    current: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for key in sorted(groups):
        candidates = groups[key]
        kinds = {row["field_kind"] for row in candidates}
        if len(kinds) != 1:
            raise ValueError(f"observation_key {key!r} mixes field_kind values: {sorted(kinds)}")

        if args.current_run_id and next(iter(kinds)) == "dynamic":
            current_candidates = [row for row in candidates if row["run_id"] == args.current_run_id]
            if not current_candidates:
                conflicts.append(
                    {
                        "observation_key": key,
                        "conflict_type": "stale_only",
                        "selected_observation_id": None,
                        "alternative_observation_ids": sorted(row["observation_id"] for row in candidates),
                        "values": sorted({canonical(row["value"]) for row in candidates}),
                    }
                )
                continue
            candidates = current_candidates

        ordered = sorted(candidates, key=rank, reverse=True)
        selected = dict(ordered[0])
        selected["selected_from_observation_id"] = selected["observation_id"]
        selected["alternative_observation_ids"] = sorted(row["observation_id"] for row in ordered[1:])
        current.append(selected)

        values = {canonical(row["value"]) for row in ordered}
        if len(values) > 1:
            conflicts.append(
                {
                    "observation_key": key,
                    "conflict_type": "competing_values",
                    "selected_observation_id": selected["observation_id"],
                    "alternative_observation_ids": sorted(row["observation_id"] for row in ordered[1:]),
                    "values": sorted(values),
                }
            )

    atomic_write_jsonl(Path(args.output).expanduser().resolve(), current)
    atomic_write_jsonl(Path(args.conflicts).expanduser().resolve(), conflicts)
    print(
        json.dumps(
            {
                "input_records": len(records),
                "unique_observations": len(by_id),
                "materialized_keys": len(current),
                "conflicts": len(conflicts),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
