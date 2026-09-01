#!/usr/bin/env python3
"""Summarize collection throughput, stage success, and retry recovery."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


STAGES = {"discover", "fetch", "render", "parse", "extract"}
STATUSES = {
    "success",
    "partial",
    "empty",
    "blocked",
    "rate_limited",
    "timeout",
    "access_denied",
    "challenge_blocked",
    "transport_failed",
    "parse_failed",
    "invalid_target",
    "skipped_duplicate",
    "interrupted",
}
SUCCESS_STATUSES = {"success", "partial"}
NON_FAILURE_STATUSES = SUCCESS_STATUSES | {"skipped_duplicate"}
COUNT_FIELDS = ("valid_record_count", "new_record_count")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("--output", help="Optional JSON output path")
    return p


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


def load_jsonl(path: Path, errors: list[str], required: bool = True) -> list[dict[str, Any]]:
    if not path.is_file():
        if required:
            errors.append(f"missing required file: {path.name}")
        return []
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
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


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def ratio(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def metric_sum(rows: list[dict[str, Any]], field: str) -> float | int | None:
    values = [row[field] for row in rows if isinstance(row.get(field), (int, float)) and not isinstance(row.get(field), bool)]
    if not values:
        return None
    total = sum(values)
    return round(total, 6) if any(isinstance(value, float) for value in values) else total


def efficiency(rows: list[dict[str, Any]]) -> dict[str, int | float | None]:
    new_records = sum(int(row.get("new_record_count", 0)) for row in rows if row.get("status") in SUCCESS_STATUSES)
    valid_records = sum(int(row.get("valid_record_count", 0)) for row in rows if row.get("status") in SUCCESS_STATUSES)
    cost = metric_sum(rows, "cost")
    input_tokens = metric_sum(rows, "input_tokens")
    output_tokens = metric_sum(rows, "output_tokens")
    elapsed_ms = metric_sum(rows, "elapsed_ms")
    bytes_received = metric_sum(rows, "bytes_received")
    return {
        "attempts": len(rows),
        "unique_targets": len({str(row.get("target_id")) for row in rows}),
        "usable_targets": len({str(row.get("target_id")) for row in rows if row.get("status") in SUCCESS_STATUSES}),
        "reported_valid_records": valid_records,
        "reported_new_records": new_records,
        "new_records_per_100_attempts": ratio(new_records * 100, len(rows)),
        "cost": cost,
        "cost_per_new_record": ratio(float(cost), new_records) if cost is not None else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tokens_per_new_record": ratio(float((input_tokens or 0) + (output_tokens or 0)), new_records)
        if input_tokens is not None or output_tokens is not None
        else None,
        "summed_attempt_elapsed_ms": elapsed_ms,
        "elapsed_ms_per_new_record": ratio(float(elapsed_ms), new_records) if elapsed_ms is not None else None,
        "bytes_received": bytes_received,
    }


def row_order(row: dict[str, Any]) -> tuple[str, int, str]:
    attempt_no = row.get("attempt_no")
    return (
        str(row.get("finished_at") or ""),
        attempt_no if isinstance(attempt_no, int) else 0,
        str(row.get("attempt_id") or ""),
    )


def main() -> int:
    args = parser().parse_args()
    root = Path(args.run_directory).expanduser().resolve()
    errors: list[str] = []

    manifest = load_json(root / "run_manifest.json", errors)
    field_contract = load_json(root / "field_contract.json", errors) if (root / "field_contract.json").is_file() else {}
    attempts = load_jsonl(root / "collection_attempts.jsonl", errors)
    observations = load_jsonl(root / "observations.jsonl", errors, required=False)
    target_queue = load_jsonl(root / "target_queue.jsonl", errors, required=False)
    coverage = load_jsonl(root / "coverage.jsonl", errors, required=False)
    raw_artifacts = load_jsonl(root / "raw_artifacts.jsonl", errors, required=False)
    tasks = load_jsonl(root / "tasks.jsonl", errors, required=False)
    frontiers = load_jsonl(root / "discovery_frontier.jsonl", errors, required=False)
    batch_decisions = load_jsonl(root / "batch_decisions.jsonl", errors, required=False)

    required = {
        "attempt_id",
        "run_id",
        "batch_id",
        "target_id",
        "stage",
        "adapter",
        "route_version",
        "attempt_no",
        "status",
        "started_at",
        "finished_at",
    }
    attempt_ids: set[str] = set()
    retry_links: list[tuple[str, str, int]] = []

    for row in attempts:
        label = f"collection_attempts.jsonl:{row['_line']}"
        missing = sorted(field for field in required if field not in row)
        if missing:
            errors.append(f"{label}: missing {missing}")
        attempt_id = row.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            errors.append(f"{label}: attempt_id must be a non-empty string")
        elif attempt_id in attempt_ids:
            errors.append(f"{label}: duplicate attempt_id {attempt_id!r}")
        else:
            attempt_ids.add(attempt_id)
        if row.get("run_id") != manifest.get("run_id"):
            errors.append(f"{label}: run_id mismatch")
        if row.get("stage") not in STAGES:
            errors.append(f"{label}: invalid stage {row.get('stage')!r}")
        status = row.get("status")
        if status not in STATUSES:
            errors.append(f"{label}: invalid status {status!r}")
        if status in STATUSES - NON_FAILURE_STATUSES and not row.get("error_category"):
            errors.append(f"{label}: failure status requires error_category")
        attempt_no = row.get("attempt_no")
        if not isinstance(attempt_no, int) or isinstance(attempt_no, bool) or attempt_no < 1:
            errors.append(f"{label}: attempt_no must be a positive integer")
        for field in COUNT_FIELDS:
            value = row.get(field, 0)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"{label}: {field} must be a non-negative integer")
        for field in ("elapsed_ms", "input_tokens", "output_tokens", "bytes_received"):
            if field in row and (
                not isinstance(row.get(field), int)
                or isinstance(row.get(field), bool)
                or row.get(field) < 0
            ):
                errors.append(f"{label}: {field} must be a non-negative integer")
        if "cost" in row and (
            not isinstance(row.get("cost"), (int, float))
            or isinstance(row.get("cost"), bool)
            or row.get("cost") < 0
        ):
            errors.append(f"{label}: cost must be a non-negative number")
        retry_of = row.get("retry_of_attempt_id")
        if retry_of is not None:
            retry_links.append((str(attempt_id), str(retry_of), row["_line"]))

    for attempt_id, retry_of, line_no in retry_links:
        if retry_of not in attempt_ids:
            errors.append(
                f"collection_attempts.jsonl:{line_no}: retry_of_attempt_id {retry_of!r} does not exist"
            )
        if attempt_id == retry_of:
            errors.append(f"collection_attempts.jsonl:{line_no}: attempt cannot retry itself")

    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1

    by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_target_stage: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_adapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_route: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_executor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_batch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failure_attempts: Counter[str] = Counter()

    for row in attempts:
        target_id = str(row["target_id"])
        stage = str(row["stage"])
        adapter = str(row["adapter"])
        by_target[target_id].append(row)
        by_target_stage[(target_id, stage)].append(row)
        by_stage[stage].append(row)
        by_adapter[adapter].append(row)
        by_route[str(row.get("route_id") or row.get("route_version") or "unknown")].append(row)
        by_executor[str(row.get("executor_class") or "unspecified")].append(row)
        by_batch[str(row.get("batch_id"))].append(row)
        if row["status"] not in NON_FAILURE_STATUSES:
            failure_attempts[str(row["status"])] += 1

    stage_summary: dict[str, dict[str, int | float | None]] = {}
    for stage in sorted(STAGES):
        rows = by_stage.get(stage, [])
        targets = {str(row["target_id"]) for row in rows}
        fully_successful_targets = {
            str(row["target_id"]) for row in rows if row["status"] == "success"
        }
        usable_targets = {
            str(row["target_id"]) for row in rows if row["status"] in SUCCESS_STATUSES
        }
        stage_summary[stage] = {
            "attempts": len(rows),
            "unique_targets_attempted": len(targets),
            "fully_successful_targets": len(fully_successful_targets),
            "usable_targets": len(usable_targets),
            "target_success_rate": rate(len(fully_successful_targets), len(targets)),
            "target_usable_rate": rate(len(usable_targets), len(targets)),
        }

    successful_by_stage = {
        stage: {
            str(row["target_id"])
            for row in rows
            if row["status"] in SUCCESS_STATUSES
        }
        for stage, rows in by_stage.items()
    }
    all_targets = set(by_target)
    discovered = successful_by_stage.get("discover", set()) | {
        str(row["target_id"])
        for stage in ("fetch", "render", "parse", "extract")
        for row in by_stage.get(stage, [])
    }
    fetch_attempted = {
        str(row["target_id"])
        for stage in ("fetch", "render")
        for row in by_stage.get(stage, [])
    }
    fetched = successful_by_stage.get("fetch", set()) | successful_by_stage.get("render", set())
    parsed = successful_by_stage.get("parse", set()) | successful_by_stage.get("extract", set())
    extracted = successful_by_stage.get("extract", set())
    valid_targets = {
        str(row["target_id"])
        for row in by_stage.get("extract", [])
        if row["status"] in SUCCESS_STATUSES and row.get("valid_record_count", 0) > 0
    }
    duplicate_targets = {
        str(row["target_id"]) for row in attempts if row["status"] == "skipped_duplicate"
    }

    final_statuses: Counter[str] = Counter()
    unresolved_targets: set[str] = set()
    for target_id, rows in by_target.items():
        final_status = sorted(rows, key=row_order)[-1]["status"]
        final_statuses[str(final_status)] += 1
        if final_status not in NON_FAILURE_STATUSES:
            unresolved_targets.add(target_id)

    retried_target_stages = 0
    recovered_target_stages = 0
    for rows in by_target_stage.values():
        ordered = sorted(rows, key=row_order)
        if len(ordered) <= 1:
            continue
        retried_target_stages += 1
        if ordered[0]["status"] not in SUCCESS_STATUSES and any(
            row["status"] in SUCCESS_STATUSES for row in ordered[1:]
        ):
            recovered_target_stages += 1

    adapter_summary: dict[str, dict[str, int | float | None]] = {}
    for adapter, rows in sorted(by_adapter.items()):
        targets = {str(row["target_id"]) for row in rows}
        fully_successful_targets = {
            str(row["target_id"]) for row in rows if row["status"] == "success"
        }
        usable_targets = {
            str(row["target_id"]) for row in rows if row["status"] in SUCCESS_STATUSES
        }
        adapter_summary[adapter] = {
            "attempts": len(rows),
            "unique_targets_attempted": len(targets),
            "fully_successful_targets": len(fully_successful_targets),
            "usable_targets": len(usable_targets),
            "target_success_rate": rate(len(fully_successful_targets), len(targets)),
            "target_usable_rate": rate(len(usable_targets), len(targets)),
            "reported_valid_records": sum(
                int(row.get("valid_record_count", 0))
                for row in rows
                if row["status"] in SUCCESS_STATUSES
            ),
            "reported_new_records": sum(
                int(row.get("new_record_count", 0))
                for row in rows
                if row["status"] in SUCCESS_STATUSES
            ),
            "efficiency": efficiency(rows),
        }

    route_summary = {route: efficiency(rows) for route, rows in sorted(by_route.items())}
    executor_summary = {executor: efficiency(rows) for executor, rows in sorted(by_executor.items())}
    batch_rows = sorted(by_batch.items(), key=lambda item: min(str(row.get("started_at") or "") for row in item[1]))
    cumulative_new_records = 0
    batch_summary: list[dict[str, Any]] = []
    for batch_id, rows in batch_rows:
        metrics = efficiency(rows)
        cumulative_new_records += int(metrics["reported_new_records"] or 0)
        batch_summary.append({"batch_id": batch_id, **metrics, "cumulative_new_records": cumulative_new_records})

    observations_by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        if row.get("field"):
            observations_by_field[str(row["field"])].append(row)
    latest_coverage: dict[tuple[str, str], dict[str, Any]] = {}
    for row in coverage:
        target_id = str(row.get("target_id") or "")
        field = str(row.get("field_scope") or "")
        if not target_id or not field:
            continue
        key = (target_id, field)
        order = (str(row.get("retrieved_at") or ""), str(row.get("attempt_id") or ""), int(row.get("_line", 0)))
        previous = latest_coverage.get(key)
        previous_order = (
            str(previous.get("retrieved_at") or ""),
            str(previous.get("attempt_id") or ""),
            int(previous.get("_line", 0)),
        ) if previous else None
        if previous_order is None or order > previous_order:
            latest_coverage[key] = row
    field_names = sorted(
        set(field_contract.get("required_fields", []))
        | set(field_contract.get("optional_fields", []))
        | set(observations_by_field)
        | {field for _, field in latest_coverage}
    )
    field_summary: dict[str, dict[str, Any]] = {}
    for field in field_names:
        field_rows = observations_by_field.get(field, [])
        states = Counter(
            str(row.get("state") or "unknown")
            for (target_id, cell_field), row in latest_coverage.items()
            if cell_field == field
        )
        planned_cells = sum(states.values())
        terminal_cells = sum(states[state] for state in ("checked_hit", "checked_no_confirmation", "blocked"))
        field_summary[field] = {
            "required": field in set(field_contract.get("required_fields", [])),
            "optional": field in set(field_contract.get("optional_fields", [])),
            "observations": len(field_rows),
            "unique_targets_observed": len({str(row.get("target_id")) for row in field_rows if row.get("target_id")}),
            "unique_observation_keys": len({str(row.get("observation_key")) for row in field_rows if row.get("observation_key")}),
            "planned_target_field_cells": planned_cells,
            "terminal_target_field_cells": terminal_cells,
            "terminalization_rate": rate(terminal_cells, planned_cells),
            "states": dict(sorted(states.items())),
        }

    planned_target_ids = {str(row.get("target_id")) for row in target_queue if row.get("target_id")}
    terminal_cells_total = sum(
        str(row.get("state")) in {"checked_hit", "checked_no_confirmation", "blocked"}
        for row in latest_coverage.values()
    )
    tasks_by_runner_class = Counter(str(row.get("runner_class") or "unspecified") for row in tasks)
    latest_frontiers: dict[str, dict[str, Any]] = {}
    for row in frontiers:
        frontier_id = str(row.get("frontier_id") or "")
        if not frontier_id:
            continue
        order = (str(row.get("event_at") or ""), int(row.get("_line", 0)))
        previous = latest_frontiers.get(frontier_id)
        previous_order = (
            str(previous.get("event_at") or ""),
            int(previous.get("_line", 0)),
        ) if previous else None
        if previous_order is None or order > previous_order:
            latest_frontiers[frontier_id] = row
    frontier_states = Counter(str(row.get("state") or "unknown") for row in latest_frontiers.values())
    latest_batch_decision = max(
        batch_decisions,
        key=lambda row: (str(row.get("decided_at") or ""), int(row.get("_line", 0))),
        default=None,
    )

    summary = {
        "schema_version": "1.2.0",
        "run_id": manifest.get("run_id"),
        "batches": len({str(row["batch_id"]) for row in attempts}),
        "total_attempts": len(attempts),
        "unique_targets": len(all_targets),
        "planned_targets": len(planned_target_ids),
        "pipeline": {
            "discovered_targets": len(discovered),
            "fetch_attempted_targets": len(fetch_attempted),
            "fetched_targets": len(fetched),
            "parsed_targets": len(parsed),
            "extracted_targets": len(extracted),
            "valid_targets": len(valid_targets),
            "duplicate_targets": len(duplicate_targets),
            "unresolved_targets": len(unresolved_targets),
            "fetch_success_rate": rate(len(fetched), len(fetch_attempted)),
            "parse_success_rate": rate(len(parsed & fetched), len(fetched)),
            "valid_target_rate": rate(len(valid_targets), len(extracted)),
            "end_to_end_valid_rate": rate(len(valid_targets), len(discovered)),
        },
        "recovery": {
            "retried_target_stages": retried_target_stages,
            "recovered_target_stages": recovered_target_stages,
            "retry_recovery_rate": rate(recovered_target_stages, retried_target_stages),
        },
        "failures": {
            "attempts_by_status": dict(sorted(failure_attempts.items())),
            "final_targets_by_status": dict(sorted(final_statuses.items())),
        },
        "observations": {
            "rows": len(observations),
            "unique_observation_ids": len(
                {str(row["observation_id"]) for row in observations if row.get("observation_id")}
            ),
            "unique_observation_keys": len(
                {str(row["observation_key"]) for row in observations if row.get("observation_key")}
            ),
        },
        "field_coverage": {
            "planned_target_field_cells": len(latest_coverage),
            "terminal_target_field_cells": terminal_cells_total,
            "terminalization_rate": rate(terminal_cells_total, len(latest_coverage)),
            "by_field": field_summary,
        },
        "efficiency": {
            **efficiency(attempts),
            "cost_unit": manifest.get("cost_unit"),
            "raw_artifacts": len(raw_artifacts),
            "unique_raw_payload_hashes": len({str(row.get("sha256")) for row in raw_artifacts if row.get("sha256")}),
        },
        "coordination": {
            "decision": manifest.get("coordination"),
            "tasks": len(tasks),
            "tasks_by_runner_class": dict(sorted(tasks_by_runner_class.items())),
        },
        "control_loop": {
            "policy": manifest.get("collection_control"),
            "frontier_events": len(frontiers),
            "frontiers": len(latest_frontiers),
            "frontier_states": dict(sorted(frontier_states.items())),
            "frontier_new_targets": sum(
                int(row.get("new_target_count", 0))
                for row in frontiers
                if isinstance(row.get("new_target_count", 0), int)
            ),
            "frontier_duplicate_targets": sum(
                int(row.get("duplicate_target_count", 0))
                for row in frontiers
                if isinstance(row.get("duplicate_target_count", 0), int)
            ),
            "batch_decisions": len(batch_decisions),
            "latest_stop_decision": latest_batch_decision.get("stop_decision") if latest_batch_decision else None,
            "latest_selected_count": latest_batch_decision.get("selected_count") if latest_batch_decision else None,
        },
        "batches_marginal_yield": batch_summary,
        "stages": stage_summary,
        "adapters": adapter_summary,
        "routes": route_summary,
        "executors": executor_summary,
    }

    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
