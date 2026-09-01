#!/usr/bin/env python3
"""Append an auditable discovery-frontier event to a schema 1.5 research run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METHODS = {
    "bounded_plan",
    "sitemap",
    "feed",
    "category",
    "pagination",
    "cursor",
    "site_search",
    "query",
    "identifier_enumeration",
    "registry",
    "api",
    "export",
    "other",
}
STATES = {"pending", "active", "paused", "exhausted", "blocked"}


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(prefix: str, value: object) -> str:
    digest = hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def version_at_least(value: object, minimum: tuple[int, int, int]) -> bool:
    try:
        parts = tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return False
    return len(parts) == 3 and parts >= minimum


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
        rows.append(value)
    return rows


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    rendered = "".join(stable_json(row) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def parse_dimensions(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"dimension must use key=value: {raw!r}")
        key, value = (part.strip() for part in raw.split("=", 1))
        if not key or not value:
            raise ValueError(f"dimension must have a non-empty key and value: {raw!r}")
        if key in result:
            raise ValueError(f"duplicate dimension key: {key!r}")
        result[key] = value
    return dict(sorted(result.items()))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("--frontier-id", help="Stable existing frontier ID; derived when omitted")
    p.add_argument("--parent-frontier-id")
    p.add_argument("--source-class", required=True)
    p.add_argument("--method", required=True, choices=sorted(METHODS))
    p.add_argument("--entrypoint", required=True)
    p.add_argument("--state", required=True, choices=sorted(STATES))
    p.add_argument("--dimension", action="append", default=[], help="Stable key=value frontier dimension")
    p.add_argument("--query")
    p.add_argument("--alias")
    p.add_argument("--market")
    p.add_argument("--cursor")
    p.add_argument("--event-at", help="UTC event time; defaults to now")
    p.add_argument("--new-target-count", type=int, default=0)
    p.add_argument("--duplicate-target-count", type=int, default=0)
    p.add_argument("--invalid-target-count", type=int, default=0)
    p.add_argument("--end-reason")
    p.add_argument("--blocker-reason")
    return p


def main() -> int:
    args = parser().parse_args()
    root = Path(args.run_directory).expanduser().resolve()
    manifest = load_json(root / "run_manifest.json")
    if not version_at_least(manifest.get("schema_version"), (1, 5, 0)):
        raise ValueError("record_discovery_frontier.py requires run schema 1.5.0 or later")

    for label in ("source_class", "entrypoint"):
        value = getattr(args, label)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be a non-empty string")
    for label in ("new_target_count", "duplicate_target_count", "invalid_target_count"):
        value = getattr(args, label)
        if value < 0:
            raise ValueError(f"{label} must be non-negative")
    if args.state == "exhausted" and not args.end_reason:
        raise ValueError("exhausted frontier requires --end-reason")
    if args.state == "blocked" and not args.blocker_reason:
        raise ValueError("blocked frontier requires --blocker-reason")

    dimensions = parse_dimensions(args.dimension)
    identity = {
        "source_class": args.source_class.strip(),
        "discovery_method": args.method,
        "entrypoint": args.entrypoint.strip(),
        "dimensions": dimensions,
        "query": args.query,
        "alias": args.alias,
        "market": args.market,
    }
    frontier_id = args.frontier_id or stable_id("FRONTIER", identity)
    row = {
        "frontier_event_id": None,
        "frontier_id": frontier_id,
        "run_id": manifest.get("run_id"),
        "goal_id": manifest.get("goal_id"),
        **identity,
        "parent_frontier_id": args.parent_frontier_id,
        "state": args.state,
        "cursor": args.cursor,
        "event_at": args.event_at or utc_now(),
        "new_target_count": args.new_target_count,
        "duplicate_target_count": args.duplicate_target_count,
        "invalid_target_count": args.invalid_target_count,
        "end_reason": args.end_reason,
        "blocker_reason": args.blocker_reason,
    }
    row["frontier_event_id"] = stable_id("FREV", {key: value for key, value in row.items() if key != "frontier_event_id"})

    path = root / "discovery_frontier.jsonl"
    existing = load_jsonl(path)
    for prior in existing:
        if prior.get("frontier_id") != frontier_id:
            continue
        prior_identity = {key: prior.get(key) for key in identity}
        if prior_identity != identity:
            raise ValueError(f"frontier_id {frontier_id!r} conflicts with its existing identity")
    event_map = {str(item.get("frontier_event_id")): item for item in existing}
    prior_event = event_map.get(str(row["frontier_event_id"]))
    if prior_event is not None and prior_event != row:
        raise ValueError(f"frontier_event_id {row['frontier_event_id']!r} conflicts with an existing event")
    appended = prior_event is None
    if appended:
        atomic_write_jsonl(path, existing + [row])

    print(json.dumps({**row, "registry_appended": appended}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
