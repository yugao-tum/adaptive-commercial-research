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
RUNNER_CLASSES = {"lead", "child_agent", "external_cli", "native_tool", "deterministic_code"}
MODEL_TIERS = {"strong_reasoning", "balanced", "low_cost"}
REASONING_TIERS = {"low", "medium", "high"}
CHILD_AGENT_DECISIONS = {
    "unassessed",
    "delegated",
    "single_lane",
    "coordination_cost",
    "unavailable",
    "unauthorized",
    "unsafe_shared_state",
}
EXTERNAL_EXECUTOR_DECISIONS = {
    "selected",
    "duplicate_capability",
    "unavailable",
    "auth_blocked",
    "cost_blocked",
    "failed_pilot",
    "not_needed",
}
FIELD_KINDS = {"static", "slowly_changing", "dynamic"}
SOURCE_STRENGTHS = {"direct_primary", "official_secondary", "independent_secondary", "weak_signal", "unknown"}
SOURCE_STATES = {"ready", "degraded", "blocked", "unknown"}
ACCESS_CLASSES = {"public", "internal", "private", "restricted"}
RAW_STORAGE_STATES = {"stored", "external", "not_retained"}
COLLECTION_STAGES = {"discover", "fetch", "render", "parse", "extract"}
COLLECTION_STATUSES = {
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
COLLECTION_NON_FAILURE_STATES = {"success", "partial", "skipped_duplicate"}


def stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: object) -> str:
    return f"{prefix}-{stable_hash(value)[:24]}"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version_at_least(value: object, minimum: tuple[int, int, int]) -> bool:
    try:
        parts = tuple(int(part) for part in str(value).split("."))
    except ValueError:
        return False
    return len(parts) == 3 and parts >= minimum


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


def as_string_set(value: Any, label: str, errors: list[str]) -> set[str]:
    items = as_list(value, label, errors)
    strings: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}[{index}]: expected a non-empty string")
            continue
        strings.append(item)
    for duplicate in duplicates(strings):
        errors.append(f"{label}: duplicate field {duplicate!r}")
    return set(strings)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    p.add_argument("--verify-raw-files", action="store_true", help="Recompute hashes for stored raw artifacts")
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
    field_contract_path = root / "field_contract.json"
    requires_field_contract = version_at_least(manifest.get("schema_version"), (1, 2, 0))
    if requires_field_contract and not field_contract_path.is_file():
        errors.append("missing required file for schema >= 1.2.0: field_contract.json")
    field_contract = load_json(field_contract_path, errors) if field_contract_path.is_file() else {}
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
    if requires_field_contract:
        require(
            goal,
            {"required_fields", "optional_fields", "excluded_fields"},
            "goal_contract.json",
            errors,
        )
    attempts_path = root / "collection_attempts.jsonl"
    if version_at_least(manifest.get("schema_version"), (1, 1, 0)) and not attempts_path.is_file():
        errors.append("missing required file for schema >= 1.1.0: collection_attempts.jsonl")
    requires_control_plane = version_at_least(manifest.get("schema_version"), (1, 3, 0))
    requires_execution_routing = version_at_least(manifest.get("schema_version"), (1, 4, 0))
    for name in ("target_queue.jsonl", "raw_artifacts.jsonl"):
        if requires_control_plane and not (root / name).is_file():
            errors.append(f"missing required file for schema >= 1.3.0: {name}")
    for field in ("schema_version", "goal_id", "mode", "depth", "as_of"):
        if goal.get(field) != manifest.get(field):
            errors.append(f"goal_contract.json and run_manifest.json disagree on {field}")
    if goal.get("depth") not in {"quick", "standard", "exhaustive"}:
        errors.append(f"invalid depth: {goal.get('depth')!r}")
    if manifest.get("input_snapshot") and stable_hash(goal) != manifest.get("input_snapshot"):
        errors.append("goal_contract.json no longer matches run_manifest.json input_snapshot")

    coordination: dict[str, Any] = {}
    selected_external_attempts: list[tuple[str, str]] = []
    selected_external_ids: set[str] = set()
    if requires_execution_routing:
        if not isinstance(manifest.get("coordination"), dict):
            errors.append("run_manifest.json.coordination must be an object for schema >= 1.4.0")
        else:
            coordination = manifest["coordination"]
            require(
                coordination,
                {
                    "assessed",
                    "independent_lane_count",
                    "child_agent_decision",
                    "child_agent_reason",
                    "external_executor_decisions",
                },
                "run_manifest.json.coordination",
                errors,
            )
            assessed = coordination.get("assessed")
            if not isinstance(assessed, bool):
                errors.append("run_manifest.json.coordination.assessed must be a boolean")
            elif not assessed:
                warnings.append("coordination and executor routing have not been assessed")
            lane_count = coordination.get("independent_lane_count")
            if not isinstance(lane_count, int) or isinstance(lane_count, bool) or lane_count < 0:
                errors.append("run_manifest.json.coordination.independent_lane_count must be a non-negative integer")
            child_decision = coordination.get("child_agent_decision")
            if child_decision not in CHILD_AGENT_DECISIONS:
                errors.append(f"run_manifest.json.coordination has invalid child_agent_decision {child_decision!r}")
            child_reason = coordination.get("child_agent_reason")
            if (
                child_decision != "delegated"
                and assessed
                and isinstance(lane_count, int)
                and not isinstance(lane_count, bool)
                and lane_count >= 2
            ):
                if child_decision == "single_lane":
                    errors.append("coordination declares at least two independent lanes but child_agent_decision is single_lane")
                if not isinstance(child_reason, str) or not child_reason.strip():
                    errors.append("non-delegation with multiple independent lanes requires child_agent_reason")
            decisions = as_list(
                coordination.get("external_executor_decisions"),
                "run_manifest.json.coordination.external_executor_decisions",
                errors,
            )
            for index, decision in enumerate(decisions):
                label = f"run_manifest.json.coordination.external_executor_decisions[{index}]"
                if not isinstance(decision, dict):
                    errors.append(f"{label}: expected an object")
                    continue
                require(decision, {"executor_id", "capability_gap", "decision", "reason"}, label, errors)
                for field in ("executor_id", "capability_gap", "reason"):
                    if not isinstance(decision.get(field), str) or not decision.get(field):
                        errors.append(f"{label}.{field} must be a non-empty string")
                state = decision.get("decision")
                if state not in EXTERNAL_EXECUTOR_DECISIONS:
                    errors.append(f"{label}: invalid decision {state!r}")
                if state in {"selected", "failed_pilot"}:
                    attempt_id = decision.get("pilot_attempt_id")
                    if not isinstance(attempt_id, str) or not attempt_id:
                        errors.append(f"{label}: {state} requires pilot_attempt_id")
                    else:
                        selected_external_attempts.append((str(decision.get("executor_id")), attempt_id))
                if state == "selected" and isinstance(decision.get("executor_id"), str):
                    selected_external_ids.add(decision["executor_id"])

    require(data_dictionary, {"schema_version", "goal_id", "unit_of_analysis", "key_fields", "fields"}, "data_dictionary.json", errors)
    coverage_required = {"schema_version", "goal_id", "dimensions", "required_source_classes", "required_cells", "completion_rule"}
    if requires_field_contract:
        coverage_required.add("required_fields")
    require(coverage_plan, coverage_required, "coverage_plan.json", errors)
    for name, value in (("data_dictionary.json", data_dictionary), ("coverage_plan.json", coverage_plan)):
        if value.get("schema_version") != manifest.get("schema_version"):
            errors.append(f"{name}: schema_version mismatch")
        if value.get("goal_id") != manifest.get("goal_id"):
            errors.append(f"{name}: goal_id mismatch")

    required_fields: set[str] = set()
    optional_fields: set[str] = set()
    excluded_fields: set[str] = set()
    if requires_field_contract and field_contract:
        require(
            field_contract,
            {
                "schema_version",
                "goal_id",
                "required_fields",
                "optional_fields",
                "excluded_fields",
                "extractor_output_fields",
                "acceptance_fields",
            },
            "field_contract.json",
            errors,
        )
        if field_contract.get("schema_version") != manifest.get("schema_version"):
            errors.append("field_contract.json: schema_version mismatch")
        if field_contract.get("goal_id") != manifest.get("goal_id"):
            errors.append("field_contract.json: goal_id mismatch")

        goal_required = as_string_set(goal.get("required_fields"), "goal_contract.json.required_fields", errors)
        goal_optional = as_string_set(goal.get("optional_fields"), "goal_contract.json.optional_fields", errors)
        goal_excluded = as_string_set(goal.get("excluded_fields"), "goal_contract.json.excluded_fields", errors)
        required_fields = as_string_set(field_contract.get("required_fields"), "field_contract.json.required_fields", errors)
        optional_fields = as_string_set(field_contract.get("optional_fields"), "field_contract.json.optional_fields", errors)
        excluded_fields = as_string_set(field_contract.get("excluded_fields"), "field_contract.json.excluded_fields", errors)
        extractor_fields = as_string_set(field_contract.get("extractor_output_fields"), "field_contract.json.extractor_output_fields", errors)
        acceptance_fields = as_string_set(field_contract.get("acceptance_fields"), "field_contract.json.acceptance_fields", errors)
        coverage_fields = as_string_set(coverage_plan.get("required_fields"), "coverage_plan.json.required_fields", errors)

        for left_name, left, right_name, right in (
            ("required", required_fields, "optional", optional_fields),
            ("required", required_fields, "excluded", excluded_fields),
            ("optional", optional_fields, "excluded", excluded_fields),
        ):
            overlap = sorted(left & right)
            if overlap:
                errors.append(f"field_contract.json: {left_name} and {right_name} fields overlap: {overlap}")

        for label, goal_fields, contract_fields in (
            ("required", goal_required, required_fields),
            ("optional", goal_optional, optional_fields),
            ("excluded", goal_excluded, excluded_fields),
        ):
            if goal_fields != contract_fields:
                errors.append(f"goal_contract.json and field_contract.json disagree on {label}_fields")

        if coverage_fields != required_fields:
            errors.append("coverage_plan.json.required_fields does not match field_contract.json.required_fields")

        dictionary_fields_value = data_dictionary.get("fields")
        if not isinstance(dictionary_fields_value, dict):
            errors.append("data_dictionary.json.fields: expected an object")
            dictionary_fields: set[str] = set()
        else:
            dictionary_fields = set(dictionary_fields_value)
        missing_dictionary = sorted((required_fields | optional_fields) - dictionary_fields)
        if missing_dictionary:
            errors.append(f"data_dictionary.json.fields missing contracted fields: {missing_dictionary}")
        excluded_dictionary = sorted(excluded_fields & dictionary_fields)
        if excluded_dictionary:
            errors.append(f"data_dictionary.json.fields contains excluded fields: {excluded_dictionary}")

        allowed_fields = required_fields | optional_fields
        for label, declared in (("extractor_output_fields", extractor_fields), ("acceptance_fields", acceptance_fields)):
            missing_required = sorted(required_fields - declared)
            if missing_required:
                errors.append(f"field_contract.json.{label} missing required fields: {missing_required}")
            outside_contract = sorted(declared - allowed_fields)
            if outside_contract:
                errors.append(f"field_contract.json.{label} contains fields outside the contract: {outside_contract}")

    sources = load_jsonl(root / "sources.jsonl", errors)
    targets = load_jsonl(root / "target_queue.jsonl", errors) if (root / "target_queue.jsonl").is_file() else []
    collection_attempts = load_jsonl(attempts_path, errors) if attempts_path.is_file() else []
    coverage = load_jsonl(root / "coverage.jsonl", errors)
    observations = load_jsonl(root / "observations.jsonl", errors)
    raw_artifacts = load_jsonl(root / "raw_artifacts.jsonl", errors) if (root / "raw_artifacts.jsonl").is_file() else []
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

    target_ids: set[str] = set()
    target_fields: dict[str, set[str]] = {}
    planned_cell_ids: set[str] = set()
    for row in targets:
        label = f"target_queue.jsonl:{row['_line']}"
        require(
            row,
            {
                "target_id",
                "run_id",
                "goal_id",
                "template_id",
                "target_type",
                "page_type",
                "source_class",
                "route_id",
                "locator",
                "dimensions",
                "coverage_fields",
                "priority",
                "shard_id",
                "partition_key",
                "batch_id",
                "planned_at",
                "planner_version",
            },
            label,
            errors,
        )
        target_id = row.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            errors.append(f"{label}: target_id must be a non-empty string")
            continue
        if target_id in target_ids:
            errors.append(f"{label}: duplicate target_id {target_id!r}")
        target_ids.add(target_id)
        if row.get("run_id") != manifest.get("run_id"):
            errors.append(f"{label}: run_id mismatch")
        if row.get("goal_id") != manifest.get("goal_id"):
            errors.append(f"{label}: goal_id mismatch")
        if not isinstance(row.get("dimensions"), dict):
            errors.append(f"{label}: dimensions must be an object")
        fields = as_string_set(row.get("coverage_fields"), f"{label}.coverage_fields", errors)
        target_fields[target_id] = fields
        outside_contract = sorted(fields - (required_fields | optional_fields))
        if outside_contract:
            errors.append(f"{label}: coverage_fields outside field contract: {outside_contract}")
        if not isinstance(row.get("priority"), int) or isinstance(row.get("priority"), bool):
            errors.append(f"{label}: priority must be an integer")
        if not isinstance(row.get("shard_id"), int) or isinstance(row.get("shard_id"), bool) or row.get("shard_id") < 0:
            errors.append(f"{label}: shard_id must be a non-negative integer")
        for field in fields:
            planned_cell_ids.add(stable_id("CELL", {"target_id": target_id, "field": field}))

    if requires_control_plane:
        declared_cells = as_string_set(coverage_plan.get("required_cells"), "coverage_plan.json.required_cells", errors)
        missing_cells = sorted(planned_cell_ids - declared_cells)
        if missing_cells:
            errors.append(f"coverage_plan.json.required_cells missing planned target-field cells: {missing_cells[:10]}")

    collection_attempt_ids: set[str] = set()
    attempt_cost_seen = False
    retry_links: list[tuple[str, str, int]] = []
    for row in collection_attempts:
        label = f"collection_attempts.jsonl:{row['_line']}"
        require(
            row,
            {
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
            },
            label,
            errors,
        )
        attempt_id = row.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            errors.append(f"{label}: attempt_id must be a non-empty string")
        elif attempt_id in collection_attempt_ids:
            errors.append(f"{label}: duplicate attempt_id {attempt_id!r}")
        else:
            collection_attempt_ids.add(attempt_id)
        if row.get("run_id") != manifest.get("run_id"):
            errors.append(f"{label}: run_id mismatch")
        if requires_control_plane and row.get("target_id") not in target_ids:
            errors.append(f"{label}: unknown target_id {row.get('target_id')!r}")
        if row.get("stage") not in COLLECTION_STAGES:
            errors.append(f"{label}: invalid stage {row.get('stage')!r}")
        status = row.get("status")
        if status not in COLLECTION_STATUSES:
            errors.append(f"{label}: invalid status {status!r}")
        if status in COLLECTION_STATUSES - COLLECTION_NON_FAILURE_STATES and not row.get("error_category"):
            errors.append(f"{label}: failure status requires error_category")
        attempt_no = row.get("attempt_no")
        if not isinstance(attempt_no, int) or isinstance(attempt_no, bool) or attempt_no < 1:
            errors.append(f"{label}: attempt_no must be a positive integer")
        for field in ("valid_record_count", "new_record_count"):
            value = row.get(field, 0)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"{label}: {field} must be a non-negative integer")
        for field in ("elapsed_ms", "input_tokens", "output_tokens", "bytes_received"):
            if field not in row:
                continue
            value = row.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"{label}: {field} must be a non-negative integer")
        if "cost" in row:
            attempt_cost_seen = True
            value = row.get("cost")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                errors.append(f"{label}: cost must be a non-negative number")
        if "executor_class" in row and (not isinstance(row.get("executor_class"), str) or not row.get("executor_class")):
            errors.append(f"{label}: executor_class must be a non-empty string")
        for field in ("provider_run_id", "provider_version", "billing_model"):
            if field in row and (not isinstance(row.get(field), str) or not row.get(field)):
                errors.append(f"{label}: {field} must be a non-empty string")
        retry_of = row.get("retry_of_attempt_id")
        if retry_of is not None:
            retry_links.append((str(attempt_id), str(retry_of), row["_line"]))

    for attempt_id, retry_of, line_no in retry_links:
        if retry_of not in collection_attempt_ids:
            errors.append(
                f"collection_attempts.jsonl:{line_no}: retry_of_attempt_id {retry_of!r} does not exist"
            )
        if attempt_id == retry_of:
            errors.append(f"collection_attempts.jsonl:{line_no}: attempt cannot retry itself")

    for executor_id, pilot_attempt_id in selected_external_attempts:
        if pilot_attempt_id not in collection_attempt_ids:
            errors.append(
                "run_manifest.json.coordination: external executor "
                f"{executor_id!r} references unknown pilot_attempt_id {pilot_attempt_id!r}"
            )

    if attempt_cost_seen and (not isinstance(manifest.get("cost_unit"), str) or not manifest.get("cost_unit")):
        warnings.append("collection attempts contain cost but run_manifest.json has no cost_unit")

    cell_attempt_ids: list[str] = []
    for row in coverage:
        label = f"coverage.jsonl:{row['_line']}"
        coverage_required_fields = {"attempt_id", "cell_id", "run_id", "source_class", "object_scope", "field_scope", "market", "state", "retrieved_at"}
        if requires_control_plane:
            coverage_required_fields.add("target_id")
        require(row, coverage_required_fields, label, errors)
        if row.get("state") not in COVERAGE_STATES:
            errors.append(f"{label}: invalid state {row.get('state')!r}")
        if row.get("state") == "blocked" and not row.get("blocker_reason"):
            errors.append(f"{label}: blocked state requires blocker_reason")
        for source_id in as_list(row.get("source_ids", []), f"{label}.source_ids", errors):
            if source_id not in source_ids:
                errors.append(f"{label}: unknown source_id {source_id!r}")
        if requires_control_plane:
            target_id = row.get("target_id")
            if target_id not in target_ids:
                errors.append(f"{label}: unknown target_id {target_id!r}")
            field = row.get("field_scope")
            if isinstance(target_id, str) and field not in target_fields.get(target_id, set()):
                errors.append(f"{label}: field_scope {field!r} is not planned for target {target_id!r}")
            expected_cell = stable_id("CELL", {"target_id": target_id, "field": field})
            if row.get("cell_id") != expected_cell:
                errors.append(f"{label}: cell_id does not match target_id and field_scope")
        cell_attempt_ids.append(row.get("attempt_id"))
    for value in duplicates([v for v in cell_attempt_ids if isinstance(v, str)]):
        errors.append(f"duplicate coverage attempt_id {value!r}")

    raw_artifact_ids: set[str] = set()
    raw_hashes: set[str] = set()
    for row in raw_artifacts:
        label = f"raw_artifacts.jsonl:{row['_line']}"
        require(
            row,
            {
                "raw_artifact_id",
                "run_id",
                "target_id",
                "attempt_id",
                "sha256",
                "bytes",
                "media_type",
                "locator",
                "retrieved_at",
                "route_version",
                "access_class",
                "storage_state",
            },
            label,
            errors,
        )
        artifact_id = row.get("raw_artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            errors.append(f"{label}: raw_artifact_id must be a non-empty string")
        if artifact_id in raw_artifact_ids:
            errors.append(f"{label}: duplicate raw_artifact_id {artifact_id!r}")
        raw_artifact_ids.add(artifact_id)
        if row.get("run_id") != manifest.get("run_id"):
            errors.append(f"{label}: run_id mismatch")
        if row.get("target_id") not in target_ids:
            errors.append(f"{label}: unknown target_id {row.get('target_id')!r}")
        if row.get("attempt_id") not in collection_attempt_ids:
            errors.append(f"{label}: unknown attempt_id {row.get('attempt_id')!r}")
        source_id = row.get("source_id")
        if source_id is not None and source_id not in source_ids:
            errors.append(f"{label}: unknown source_id {source_id!r}")
        content_hash = row.get("sha256")
        if not isinstance(content_hash, str) or len(content_hash) != 64:
            errors.append(f"{label}: sha256 must be a 64-character hex digest")
        else:
            try:
                int(content_hash, 16)
            except ValueError:
                errors.append(f"{label}: sha256 must be hexadecimal")
            raw_hashes.add(content_hash)
        if not isinstance(row.get("bytes"), int) or isinstance(row.get("bytes"), bool) or row.get("bytes") < 0:
            errors.append(f"{label}: bytes must be a non-negative integer")
        if row.get("access_class") not in ACCESS_CLASSES:
            errors.append(f"{label}: invalid access_class {row.get('access_class')!r}")
        storage_state = row.get("storage_state")
        if storage_state not in RAW_STORAGE_STATES:
            errors.append(f"{label}: invalid storage_state {storage_state!r}")
        if storage_state == "stored":
            relative_path = row.get("relative_path")
            if not isinstance(relative_path, str) or not relative_path:
                errors.append(f"{label}: stored artifact requires relative_path")
            else:
                artifact_path = (root / relative_path).resolve()
                if root not in artifact_path.parents:
                    errors.append(f"{label}: relative_path escapes the run directory")
                elif not artifact_path.is_file():
                    errors.append(f"{label}: stored artifact file is missing")
                else:
                    if artifact_path.stat().st_size != row.get("bytes"):
                        errors.append(f"{label}: stored artifact byte count mismatch")
                    if args.verify_raw_files and file_hash(artifact_path) != content_hash:
                        errors.append(f"{label}: stored artifact hash mismatch")
        elif not row.get("retention_reason"):
            errors.append(f"{label}: non-stored artifact requires retention_reason")

    observation_ids: set[str] = set()
    observation_keys: set[str] = set()
    for row in observations:
        label = f"observations.jsonl:{row['_line']}"
        require(
            row,
            {"observation_id", "run_id", "observation_key", "object_type", "object_id", "field", "field_kind", "value", "source_id", "evidence_type", "source_strength", "observed_at", "retrieved_at", "route_version", "parser_version", "raw_hash"} | ({"target_id"} if requires_control_plane else set()),
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
        if requires_control_plane:
            target_id = row.get("target_id")
            if target_id not in target_ids:
                errors.append(f"{label}: unknown target_id {target_id!r}")
            if row.get("field") not in target_fields.get(str(target_id), set()):
                errors.append(f"{label}: field is not planned for target {target_id!r}")
            if row.get("raw_hash") not in raw_hashes:
                errors.append(f"{label}: raw_hash is not registered in raw_artifacts.jsonl")

    task_ids: set[str] = set()
    active_partitions: list[str] = []
    active_resource_leases: list[str] = []
    child_agent_task_count = 0
    external_task_ids: set[str] = set()
    task_runner_counts: Counter[str] = Counter()
    for row in tasks:
        label = f"tasks.jsonl:{row['_line']}"
        task_required = {"task_id", "goal_id", "input_snapshot", "partition_key", "owner", "status", "attempt"}
        if requires_execution_routing:
            task_required.update(
                {
                    "runner_class",
                    "executor_id",
                    "dispatch_reason",
                    "expected_output_schema",
                    "acceptance_metric",
                    "escalation_condition",
                    "allowed_side_effects",
                    "resource_lease_keys",
                }
            )
        require(row, task_required, label, errors)
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
        if requires_execution_routing:
            runner_class = row.get("runner_class")
            if runner_class not in RUNNER_CLASSES:
                errors.append(f"{label}: invalid runner_class {runner_class!r}")
            else:
                task_runner_counts[runner_class] += 1
            for field in (
                "executor_id",
                "dispatch_reason",
                "expected_output_schema",
                "acceptance_metric",
                "escalation_condition",
            ):
                if not isinstance(row.get(field), str) or not row.get(field):
                    errors.append(f"{label}: {field} must be a non-empty string")
            as_string_set(row.get("allowed_side_effects"), f"{label}.allowed_side_effects", errors)
            resource_keys = as_string_set(row.get("resource_lease_keys"), f"{label}.resource_lease_keys", errors)
            if row.get("status") in ACTIVE_TASK_STATES:
                active_resource_leases.extend(resource_keys)
            if runner_class == "child_agent":
                child_agent_task_count += 1
                if row.get("model_tier") not in MODEL_TIERS:
                    errors.append(f"{label}: child_agent requires a valid model_tier")
                if row.get("reasoning_tier") not in REASONING_TIERS:
                    errors.append(f"{label}: child_agent requires a valid reasoning_tier")
            if runner_class == "external_cli":
                executor_id = row.get("executor_id")
                if isinstance(executor_id, str):
                    external_task_ids.add(executor_id)
                if row.get("readiness_state") not in SOURCE_STATES:
                    errors.append(f"{label}: external_cli requires a valid readiness_state")
                if row.get("status") in ACTIVE_TASK_STATES and row.get("readiness_state") not in {"ready", "degraded"}:
                    errors.append(f"{label}: active external_cli task is not runtime-ready")
    for value in duplicates(active_partitions):
        errors.append(f"multiple active task leases for partition_key {value!r}")
    for value in duplicates(active_resource_leases):
        errors.append(f"multiple active task leases for resource_lease_key {value!r}")
    if requires_execution_routing:
        child_decision = coordination.get("child_agent_decision")
        if child_decision == "delegated" and child_agent_task_count == 0:
            errors.append("coordination declares delegated child agents but tasks.jsonl has no child_agent task")
        if child_decision != "delegated" and child_agent_task_count > 0:
            errors.append("tasks.jsonl contains child_agent work but coordination does not declare delegation")
        missing_external_tasks = sorted(selected_external_ids - external_task_ids)
        if missing_external_tasks:
            errors.append(
                "selected external executors have no external_cli task: "
                f"{missing_external_tasks}"
            )

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
    if observations and not collection_attempts:
        warnings.append("observations exist but collection_attempts.jsonl is empty")
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
        "targets": len(targets),
        "collection_attempts": len(collection_attempts),
        "coverage_attempts": len(coverage),
        "observations": len(observations),
        "raw_artifacts": len(raw_artifacts),
        "tasks": len(tasks),
        "tasks_by_runner_class": dict(sorted(task_runner_counts.items())),
        "coordination_assessed": coordination.get("assessed") if coordination else None,
        "child_agent_decision": coordination.get("child_agent_decision") if coordination else None,
        "external_executors_considered": len(
            coordination.get("external_executor_decisions", [])
            if isinstance(coordination.get("external_executor_decisions"), list)
            else []
        ),
        "claims": len(claims),
        "current_rows": len(current),
        "conflicts": len(conflicts),
        "required_fields": len(required_fields),
        "optional_fields": len(optional_fields),
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
