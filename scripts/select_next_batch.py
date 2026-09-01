#!/usr/bin/env python3
"""Select the next collection batch from coverage debt and observed route yield."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELECTOR_VERSION = "1.0.0"
SUCCESS_STATUSES = {"success", "partial"}
TERMINAL_COVERAGE_STATES = {"checked_hit", "checked_no_confirmation"}
HARD_ROUTE_FAILURES = {"blocked", "access_denied", "challenge_blocked", "invalid_target"}
ACTIVE_TASK_STATES = {"pending", "leased"}
TERMINAL_FRONTIER_STATES = {"exhausted", "blocked"}


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
        value["_line"] = line_no
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


def file_snapshot(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
    return digest.hexdigest()


def latest_rows(rows: list[dict[str, Any]], key_field: str, time_field: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get(key_field)
        if not isinstance(key, str) or not key:
            continue
        order = (str(row.get(time_field) or ""), int(row.get("_line", 0)))
        prior = latest.get(key)
        prior_order = (str(prior.get(time_field) or ""), int(prior.get("_line", 0))) if prior else None
        if prior_order is None or order > prior_order:
            latest[key] = row
    return latest


def attempt_order(row: dict[str, Any]) -> tuple[str, int, str, int]:
    attempt_no = row.get("attempt_no")
    return (
        str(row.get("finished_at") or ""),
        attempt_no if isinstance(attempt_no, int) else 0,
        str(row.get("attempt_id") or ""),
        int(row.get("_line", 0)),
    )


def build_route_metrics(attempts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    executions: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in attempts:
        route = str(row.get("route_id") or row.get("adapter") or "unassigned")
        attempt_no = row.get("attempt_no") if isinstance(row.get("attempt_no"), int) else 0
        executions[(str(row.get("target_id")), route, attempt_no)].append(row)

    by_route: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (_, route, _), rows in executions.items():
        ordered = sorted(rows, key=attempt_order)
        terminal = ordered[-1]
        by_route[route].append(
            {
                "success": terminal.get("status") in SUCCESS_STATUSES,
                "new_records": sum(
                    int(row.get("new_record_count", 0))
                    for row in rows
                    if isinstance(row.get("new_record_count", 0), int)
                ),
                "elapsed_ms": sum(
                    int(row.get("elapsed_ms", 0))
                    for row in rows
                    if isinstance(row.get("elapsed_ms"), int)
                ),
                "cost_values": [
                    float(row["cost"])
                    for row in rows
                    if isinstance(row.get("cost"), (int, float)) and not isinstance(row.get("cost"), bool)
                ],
                "blocked": terminal.get("status") in HARD_ROUTE_FAILURES,
            }
        )

    metrics: dict[str, dict[str, Any]] = {}
    for route, rows in by_route.items():
        count = len(rows)
        successes = sum(bool(row["success"]) for row in rows)
        new_records = sum(int(row["new_records"]) for row in rows)
        average_elapsed = sum(int(row["elapsed_ms"]) for row in rows) / count if count else 0.0
        cost_values = [value for row in rows for value in row["cost_values"]]
        average_cost = sum(cost_values) / len(cost_values) if cost_values else None
        success_probability = (successes + 1) / (count + 2)
        expected_new_records = (new_records + 0.5) / (count + 1)
        latency_penalty = 1 + average_elapsed / 60000
        cost_penalty = 1 + average_cost if average_cost is not None else 1
        utility = success_probability * expected_new_records / (latency_penalty * cost_penalty)
        metrics[route] = {
            "executions": count,
            "success_probability": round(success_probability, 6),
            "expected_new_records": round(expected_new_records, 6),
            "average_elapsed_ms": round(average_elapsed, 3),
            "average_cost": round(average_cost, 6) if average_cost is not None else None,
            "blocked_share": round(sum(bool(row["blocked"]) for row in rows) / count, 6),
            "utility": round(utility, 9),
        }
    return metrics


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("--limit", type=int, required=True, help="Maximum targets in the next bounded batch")
    p.add_argument("--exploration-slots", type=int, help="Reserve slots for routes without current-run evidence")
    p.add_argument("--max-attempts-per-target-route", type=int, help="Cap identical target-route executions")
    p.add_argument("--decided-at", help="Decision time; defaults to current UTC time")
    p.add_argument("--dry-run", action="store_true", help="Print the decision without appending its ledger row")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.limit < 1:
        raise ValueError("--limit must be a positive integer")
    root = Path(args.run_directory).expanduser().resolve()
    manifest = load_json(root / "run_manifest.json")
    if not version_at_least(manifest.get("schema_version"), (1, 5, 0)):
        raise ValueError("select_next_batch.py requires run schema 1.5.0 or later")
    field_contract = load_json(root / "field_contract.json")
    coverage_plan = load_json(root / "coverage_plan.json")
    targets = load_jsonl(root / "target_queue.jsonl")
    attempts = load_jsonl(root / "collection_attempts.jsonl")
    coverage = load_jsonl(root / "coverage.jsonl")
    tasks = load_jsonl(root / "tasks.jsonl")
    frontiers = load_jsonl(root / "discovery_frontier.jsonl")

    control = manifest.get("collection_control")
    if not isinstance(control, dict):
        raise ValueError("run_manifest.json.collection_control must be an object")
    exploration_slots = args.exploration_slots
    if exploration_slots is None:
        exploration_slots = control.get("exploration_slots", 1)
    max_attempts = args.max_attempts_per_target_route
    if max_attempts is None:
        max_attempts = control.get("max_attempts_per_target_route", 2)
    if not isinstance(exploration_slots, int) or isinstance(exploration_slots, bool) or exploration_slots < 0:
        raise ValueError("exploration slots must be a non-negative integer")
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
        raise ValueError("max attempts per target route must be a positive integer")
    exploration_slots = min(exploration_slots, args.limit)

    required_fields = {
        str(field) for field in field_contract.get("required_fields", []) if isinstance(field, str) and field
    }
    required_source_classes = {
        str(value) for value in coverage_plan.get("required_source_classes", []) if isinstance(value, str) and value
    }
    latest_coverage = latest_rows(coverage, "cell_id", "retrieved_at")
    coverage_by_target_field = {
        (str(row.get("target_id")), str(row.get("field_scope"))): row for row in latest_coverage.values()
    }
    route_metrics = build_route_metrics(attempts)
    attempts_by_target_route: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    attempts_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attempts:
        target_id = str(row.get("target_id"))
        route = str(row.get("route_id") or row.get("adapter") or "unassigned")
        attempts_by_target_route[(target_id, route)].append(row)
        attempts_by_target[target_id].append(row)

    active_partitions = {
        str(row.get("partition_key"))
        for row in tasks
        if row.get("status") in ACTIVE_TASK_STATES and row.get("partition_key")
    }
    exclusion_counts: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    unresolved_required_total = 0
    actionable_required_total = 0
    blocked_unrunnable = 0

    for target in targets:
        target_id = str(target.get("target_id"))
        target_attempts = sorted(attempts_by_target.get(target_id, []), key=attempt_order)
        last_attempt = target_attempts[-1] if target_attempts else None
        next_route = last_attempt.get("next_route_id") if last_attempt else None
        fields = [str(field) for field in target.get("coverage_fields", []) if isinstance(field, str)]
        target_required = [field for field in fields if not required_fields or field in required_fields]
        required_gaps = []
        actionable_required = []
        terminal_blocked = []
        for field in target_required:
            state = coverage_by_target_field.get((target_id, field), {}).get("state")
            if state in TERMINAL_COVERAGE_STATES:
                continue
            required_gaps.append(field)
            if state == "blocked" and not (isinstance(next_route, str) and next_route):
                terminal_blocked.append(field)
            else:
                actionable_required.append(field)
        unresolved_required_total += len(required_gaps)
        actionable_required_total += len(actionable_required)
        if not actionable_required:
            exclusion_counts[
                "blocked_coverage_terminal" if terminal_blocked else "required_coverage_terminal"
            ] += 1
            continue
        partition_key = str(target.get("partition_key") or "")
        if partition_key in active_partitions:
            exclusion_counts["active_partition_lease"] += 1
            continue

        routes = [
            str(route)
            for route in target.get("route_candidates", [target.get("route_id", "unassigned")])
            if isinstance(route, str) and route
        ]
        if isinstance(next_route, str) and next_route and next_route not in routes:
            routes.insert(0, next_route)
        routes = list(dict.fromkeys(routes))
        eligible_routes: list[tuple[float, str, dict[str, Any]]] = []
        for route in routes:
            route_attempts = attempts_by_target_route.get((target_id, route), [])
            max_attempt_no = max(
                (int(row.get("attempt_no", 0)) for row in route_attempts if isinstance(row.get("attempt_no"), int)),
                default=0,
            )
            route_last = max(route_attempts, key=attempt_order) if route_attempts else None
            if max_attempt_no >= max_attempts:
                continue
            if (
                route_last
                and route_last.get("status") in HARD_ROUTE_FAILURES
                and not (isinstance(next_route, str) and next_route and next_route == route)
            ):
                continue
            metrics = route_metrics.get(
                route,
                {
                    "executions": 0,
                    "success_probability": 0.5,
                    "expected_new_records": 0.5,
                    "average_elapsed_ms": None,
                    "average_cost": None,
                    "blocked_share": None,
                    "utility": 0.25,
                },
            )
            eligible_routes.append((float(metrics["utility"]), route, metrics))
        if not eligible_routes:
            exclusion_counts["retry_or_route_exhausted"] += 1
            blocked_unrunnable += 1
            continue

        _, selected_route, metrics = sorted(eligible_routes, key=lambda item: (-item[0], item[1]))[0]
        priority = target.get("priority") if isinstance(target.get("priority"), int) else 0
        source_class = str(target.get("source_class") or "unknown")
        candidate = {
            "target_id": target_id,
            "partition_key": partition_key,
            "source_class": source_class,
            "selected_route_id": selected_route,
            "required_fields": sorted(actionable_required),
            "coverage_debt": len(actionable_required),
            "required_source_class": source_class in required_source_classes,
            "static_priority": priority,
            "route_metrics": metrics,
            "selection_reason": "unresolved required coverage ranked by observed route utility",
        }
        candidate["_sort"] = (
            -candidate["coverage_debt"],
            -int(candidate["required_source_class"]),
            -float(metrics["utility"]),
            -priority,
            target_id,
        )
        candidates.append(candidate)

    candidates.sort(key=lambda row: row["_sort"])
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def add(candidate: dict[str, Any], reason: str) -> None:
        if len(selected) >= args.limit or candidate["target_id"] in selected_ids:
            return
        output = {key: value for key, value in candidate.items() if key != "_sort"}
        output["selection_reason"] = reason
        selected.append(output)
        selected_ids.add(candidate["target_id"])

    for candidate in candidates:
        if len(selected) >= exploration_slots:
            break
        if candidate["route_metrics"]["executions"] == 0:
            add(candidate, "reserved exploration slot for an unvalidated current-run route")

    represented_source_classes = {row["source_class"] for row in selected}
    for candidate in candidates:
        if len(selected) >= args.limit:
            break
        if candidate["source_class"] not in represented_source_classes:
            add(candidate, "coverage-fair slot for an unresolved source class")
            represented_source_classes.add(candidate["source_class"])

    for candidate in candidates:
        if len(selected) >= args.limit:
            break
        add(candidate, candidate["selection_reason"])

    latest_frontiers = latest_rows(frontiers, "frontier_id", "event_at")
    required_frontier_ids = {
        str(value) for value in coverage_plan.get("required_frontier_ids", []) if isinstance(value, str) and value
    }
    discovery_mode = control.get("discovery_mode")
    if discovery_mode == "frontier_ledger":
        frontier_scope = required_frontier_ids or set(latest_frontiers)
        discovery_complete = bool(frontier_scope) and all(
            latest_frontiers.get(frontier_id, {}).get("state") in TERMINAL_FRONTIER_STATES
            for frontier_id in frontier_scope
        )
    else:
        discovery_complete = bool(control.get("discovery_assessed")) and discovery_mode in {
            "bounded_plan",
            "not_applicable",
        }
    open_frontiers = sorted(
        frontier_id
        for frontier_id, row in latest_frontiers.items()
        if row.get("state") not in TERMINAL_FRONTIER_STATES
    )

    if selected:
        stop_decision = "continue"
    elif actionable_required_total == 0 and discovery_complete:
        stop_decision = "coverage_complete"
    elif open_frontiers or not discovery_complete:
        stop_decision = "discovery_incomplete"
    elif blocked_unrunnable:
        stop_decision = "blocked_only"
    else:
        stop_decision = "no_eligible_targets"

    ledger_files = (
        "target_queue.jsonl",
        "collection_attempts.jsonl",
        "coverage.jsonl",
        "tasks.jsonl",
        "discovery_frontier.jsonl",
    )
    ledger_snapshot = {name: file_snapshot(root / name) for name in ledger_files}
    policy = {
        "name": "coverage_first_yield_adaptive",
        "limit": args.limit,
        "exploration_slots": exploration_slots,
        "max_attempts_per_target_route": max_attempts,
    }
    decision_basis = {
        "run_id": manifest.get("run_id"),
        "input_snapshot": manifest.get("input_snapshot"),
        "selector_version": SELECTOR_VERSION,
        "policy": policy,
        "ledger_snapshot": ledger_snapshot,
        "selected": [
            {"target_id": row["target_id"], "selected_route_id": row["selected_route_id"]}
            for row in selected
        ],
        "stop_decision": stop_decision,
    }
    decision = {
        "decision_id": stable_id("BDEC", decision_basis),
        "run_id": manifest.get("run_id"),
        "goal_id": manifest.get("goal_id"),
        "input_snapshot": manifest.get("input_snapshot"),
        "decided_at": args.decided_at or utc_now(),
        "selector_version": SELECTOR_VERSION,
        "policy": policy,
        "ledger_snapshot": ledger_snapshot,
        "selected": selected,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "unresolved_required_cells": unresolved_required_total,
        "actionable_required_cells": actionable_required_total,
        "open_frontier_ids": open_frontiers,
        "discovery_complete": discovery_complete,
        "exclusion_counts": dict(sorted(exclusion_counts.items())),
        "stop_decision": stop_decision,
    }

    path = root / "batch_decisions.jsonl"
    existing = [{key: value for key, value in row.items() if key != "_line"} for row in load_jsonl(path)]
    prior = next((row for row in existing if row.get("decision_id") == decision["decision_id"]), None)
    appended = False
    if prior is None and not args.dry_run:
        atomic_write_jsonl(path, existing + [decision])
        appended = True
    elif prior is not None:
        decision = prior

    print(json.dumps({**decision, "ledger_appended": appended}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
