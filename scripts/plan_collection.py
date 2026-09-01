#!/usr/bin/env python3
"""Expand a bounded collection specification into stable targets, coverage cells, and shards."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit


PLANNER_VERSION = "1.0.0"
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
TRACKING_PREFIXES = ("utm_",)


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def version_at_least(value: object, minimum: tuple[int, int, int]) -> bool:
    try:
        parts = tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return False
    return len(parts) == 3 and parts >= minimum


def stable_id(prefix: str, value: object) -> str:
    digest = hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


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


def atomic_write_json(path: Path, value: object) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_write_text(path, rendered)


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    rendered = "".join(stable_json(row) + "\n" for row in rows)
    atomic_write_text(path, rendered)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def canonicalize_locator(locator: str) -> str:
    locator = locator.strip()
    parts = urlsplit(locator)
    if not parts.scheme or not parts.netloc:
        return locator
    host = (parts.hostname or "").lower()
    if parts.port:
        default = (parts.scheme.lower() == "http" and parts.port == 80) or (
            parts.scheme.lower() == "https" and parts.port == 443
        )
        netloc = host if default else f"{host}:{parts.port}"
    else:
        netloc = host
    if parts.username or parts.password:
        raise ValueError("locator must not contain embedded credentials")
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_KEYS
        and not any(key.lower().startswith(prefix) for prefix in TRACKING_PREFIXES)
    ]
    query.sort()
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", urlencode(query), ""))


def string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label}: expected a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}: expected non-empty strings")
        result.append(item.strip())
    if len(result) != len(set(result)):
        raise ValueError(f"{label}: duplicate values")
    return result


def matches_exclusion(rule: dict[str, Any], context: dict[str, Any]) -> bool:
    return all(context.get(key) == value for key, value in rule.items())


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("--spec", required=True, help="JSON plan with axes, templates, and exclusions")
    p.add_argument("--shards", type=int, help="Override spec shard_count")
    return p


def main() -> int:
    args = parser().parse_args()
    root = Path(args.run_directory).expanduser().resolve()
    spec_path = Path(args.spec).expanduser().resolve()
    manifest = load_json(root / "run_manifest.json")
    if not version_at_least(manifest.get("schema_version"), (1, 3, 0)):
        raise ValueError("plan_collection.py requires run schema 1.3.0 or later")
    goal = load_json(root / "goal_contract.json")
    field_contract = load_json(root / "field_contract.json")
    coverage_plan = load_json(root / "coverage_plan.json")
    spec = load_json(spec_path)

    axes_value = spec.get("axes", {})
    if not isinstance(axes_value, dict) or not axes_value:
        raise ValueError("spec.axes must be a non-empty object")
    axes: dict[str, list[Any]] = {}
    for name, values in axes_value.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(values, list) or not values:
            raise ValueError("every axis must have a non-empty name and value list")
        for value in values:
            if isinstance(value, (dict, list)):
                raise ValueError(f"axis {name!r}: values must be scalar")
        axes[name] = sorted(values, key=stable_json)

    templates = spec.get("templates")
    if not isinstance(templates, list) or not templates:
        raise ValueError("spec.templates must be a non-empty list")
    exclusions = spec.get("exclude", [])
    if not isinstance(exclusions, list) or any(not isinstance(item, dict) for item in exclusions):
        raise ValueError("spec.exclude must be a list of partial-match objects")

    shard_count = args.shards if args.shards is not None else spec.get("shard_count", 1)
    if not isinstance(shard_count, int) or isinstance(shard_count, bool) or shard_count < 1:
        raise ValueError("shard_count must be a positive integer")
    planned_at = spec.get("planned_at") or manifest.get("created_at")
    if not isinstance(planned_at, str) or not planned_at:
        raise ValueError("spec.planned_at or run_manifest.created_at is required")

    required_fields = set(string_list(field_contract.get("required_fields"), "required_fields"))
    optional_fields = set(string_list(field_contract.get("optional_fields"), "optional_fields"))
    excluded_fields = set(string_list(field_contract.get("excluded_fields"), "excluded_fields"))
    allowed_fields = required_fields | optional_fields

    generated_targets: dict[str, dict[str, Any]] = {}
    generated_coverage: dict[str, dict[str, Any]] = {}
    template_ids: set[str] = set()
    for template in sorted(templates, key=lambda item: str(item.get("template_id", ""))):
        if not isinstance(template, dict):
            raise ValueError("every template must be an object")
        template_id = template.get("template_id")
        if not isinstance(template_id, str) or not template_id:
            raise ValueError("template_id must be a non-empty string")
        if template_id in template_ids:
            raise ValueError(f"duplicate template_id {template_id!r}")
        template_ids.add(template_id)
        vary_by = string_list(template.get("vary_by", sorted(axes)), f"template {template_id}.vary_by")
        unknown_axes = sorted(set(vary_by) - set(axes))
        if unknown_axes:
            raise ValueError(f"template {template_id}: unknown axes {unknown_axes}")
        fixed_dimensions = template.get("fixed_dimensions", {})
        if not isinstance(fixed_dimensions, dict):
            raise ValueError(f"template {template_id}.fixed_dimensions must be an object")
        encode_axes = set(string_list(template.get("url_encode_axes", []), f"template {template_id}.url_encode_axes"))
        if not encode_axes <= set(vary_by) | set(fixed_dimensions):
            raise ValueError(f"template {template_id}: url_encode_axes must be dimensions")
        coverage_fields = set(
            string_list(template.get("coverage_fields", sorted(required_fields)), f"template {template_id}.coverage_fields")
        )
        outside_contract = sorted(coverage_fields - allowed_fields)
        if outside_contract:
            raise ValueError(f"template {template_id}: fields outside contract {outside_contract}")
        if coverage_fields & excluded_fields:
            raise ValueError(f"template {template_id}: excluded fields cannot be planned")
        locator_template = template.get("locator_template")
        if not isinstance(locator_template, str) or not locator_template:
            raise ValueError(f"template {template_id}.locator_template is required")
        priority = template.get("priority", 100)
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise ValueError(f"template {template_id}.priority must be an integer")

        combinations = itertools.product(*(axes[name] for name in vary_by))
        for combination in combinations:
            dimensions = {**fixed_dimensions, **dict(zip(vary_by, combination, strict=True))}
            exclusion_context = {"template_id": template_id, **dimensions}
            if any(matches_exclusion(rule, exclusion_context) for rule in exclusions):
                continue
            rendered_context = {
                key: quote_plus(str(value)) if key in encode_axes else value
                for key, value in dimensions.items()
            }
            try:
                original_locator = locator_template.format_map(rendered_context)
            except KeyError as exc:
                raise ValueError(f"template {template_id}: missing locator dimension {exc.args[0]!r}") from exc
            locator = canonicalize_locator(original_locator)
            identity_axes = string_list(template.get("identity_axes", vary_by), f"template {template_id}.identity_axes")
            if not set(identity_axes) <= set(dimensions):
                raise ValueError(f"template {template_id}: identity_axes must be dimensions")
            identity = {
                "target_type": template.get("target_type", "source_target"),
                "route_id": template.get("route_id"),
                "locator": locator,
                "dimensions": {key: dimensions[key] for key in sorted(identity_axes)},
            }
            target_id = stable_id("T", identity)
            shard_id = int(hashlib.sha256(target_id.encode("utf-8")).hexdigest(), 16) % shard_count
            row = {
                "target_id": target_id,
                "run_id": manifest.get("run_id"),
                "goal_id": goal.get("goal_id"),
                "template_id": template_id,
                "target_type": template.get("target_type", "source_target"),
                "page_type": template.get("page_type", "unknown"),
                "source_class": template.get("source_class", "unknown"),
                "route_id": template.get("route_id", "unassigned"),
                "locator": locator,
                "original_locator": original_locator,
                "dimensions": dimensions,
                "coverage_fields": sorted(coverage_fields),
                "priority": priority,
                "shard_id": shard_id,
                "partition_key": f"{template_id}:shard-{shard_id:03d}",
                "batch_id": f"batch-{template_id}-shard-{shard_id:03d}",
                "planned_at": planned_at,
                "planner_version": PLANNER_VERSION,
            }
            existing_generated = generated_targets.get(target_id)
            if existing_generated is not None and existing_generated != row:
                raise ValueError(f"target identity collision for {target_id}")
            generated_targets[target_id] = row
            for field in sorted(coverage_fields):
                cell_id = stable_id("CELL", {"target_id": target_id, "field": field})
                generated_coverage[cell_id] = {
                    "attempt_id": stable_id("PLAN", {"cell_id": cell_id}),
                    "cell_id": cell_id,
                    "run_id": manifest.get("run_id"),
                    "target_id": target_id,
                    "source_class": row["source_class"],
                    "object_scope": dimensions,
                    "field_scope": field,
                    "market": dimensions.get("market"),
                    "state": "unchecked",
                    "retrieved_at": planned_at,
                    "source_ids": [],
                    "route_id": row["route_id"],
                }

    target_path = root / "target_queue.jsonl"
    coverage_path = root / "coverage.jsonl"
    existing_targets = load_jsonl(target_path)
    existing_target_map = {str(row.get("target_id")): row for row in existing_targets}
    if len(existing_target_map) != len(existing_targets):
        raise ValueError("target_queue.jsonl contains duplicate target_id values")
    new_targets = []
    for target_id, row in sorted(generated_targets.items()):
        existing = existing_target_map.get(target_id)
        if existing is not None and existing != row:
            raise ValueError(f"existing target {target_id} conflicts with the current plan")
        if existing is None:
            new_targets.append(row)

    existing_coverage = load_jsonl(coverage_path)
    existing_cells = {str(row.get("cell_id")) for row in existing_coverage}
    new_coverage = [row for cell_id, row in sorted(generated_coverage.items()) if cell_id not in existing_cells]
    atomic_write_jsonl(target_path, existing_targets + new_targets)
    atomic_write_jsonl(coverage_path, existing_coverage + new_coverage)

    required_cells = coverage_plan.get("required_cells", [])
    if not isinstance(required_cells, list):
        raise ValueError("coverage_plan.required_cells must be a list")
    coverage_plan["required_cells"] = sorted(set(map(str, required_cells)) | set(generated_coverage))
    dimensions = coverage_plan.get("dimensions", [])
    if not isinstance(dimensions, list):
        raise ValueError("coverage_plan.dimensions must be a list")
    coverage_plan["dimensions"] = sorted(set(map(str, dimensions)) | set(axes) | {"target", "field"})
    coverage_plan["planner_version"] = PLANNER_VERSION
    coverage_plan["last_plan_hash"] = hashlib.sha256(stable_json(spec).encode("utf-8")).hexdigest()
    coverage_plan["shard_count"] = shard_count
    atomic_write_json(root / "coverage_plan.json", coverage_plan)

    print(
        json.dumps(
            {
                "generated_targets": len(generated_targets),
                "new_targets": len(new_targets),
                "generated_coverage_cells": len(generated_coverage),
                "new_coverage_cells": len(new_coverage),
                "shard_count": shard_count,
                "targets_by_shard": {
                    str(shard): sum(row["shard_id"] == shard for row in generated_targets.values())
                    for shard in range(shard_count)
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
