# Data Contract and Merge

Use this contract when research spans multiple batches, tools, agents, or repeated refreshes.

## Canonical run package

The canonical machine layer is append-only JSONL plus versioned JSON contracts:

| File | Purpose |
|---|---|
| `goal_contract.json` | Immutable decision use, scope, depth, deliverables, and stopping rules |
| `field_contract.json` | Required, optional, and excluded fields plus extractor and acceptance coverage |
| `run_manifest.json` | Run ID, schema version, mode, timestamps, input snapshot, route and parser versions |
| `data_dictionary.json` | Unit of analysis, stable keys, field semantics, types, units, and currentness classes |
| `coverage_plan.json` | Declared source universe, matrix dimensions, required cells, and completion rule |
| `sources.jsonl` | One source record per stable source ID |
| `target_queue.jsonl` | Immutable canonical target definitions, planned fields, priorities, and stable partitions |
| `collection_attempts.jsonl` | Append-only target-stage attempts, retries, checkpoints, failure classes, and route yield |
| `coverage.jsonl` | Append-only attempts and states for coverage cells |
| `observations.jsonl` | Append-only target-field observations |
| `raw_artifacts.jsonl` | Raw-payload hashes, storage state, access class, and target-attempt provenance |
| `tasks.jsonl` | Task ownership, attempts, checkpoints, and terminal states |
| `claims.jsonl` | Material conclusions and source links |
| `current_view.jsonl` | Deterministically materialized field values |
| `conflicts.jsonl` | Competing values and selected resolution |

CSV, spreadsheet, database, and narrative reports are derived views. They do not replace the canonical observations and provenance.

## Field-contract parity

For schema `1.2.0` and later, `goal_contract.json` and `field_contract.json` declare the same required, optional, and excluded field sets. Every required and optional field must exist in `data_dictionary.json`; excluded fields must not appear in extractor output or acceptance fields. Every required field must appear in both `extractor_output_fields` and `acceptance_fields` before broad execution.

The parity check verifies declared interfaces, not the truthfulness of an implementation. Bind extractor declarations to a parser version and verify the pilot's actual observations and acceptance report before scaling. When a collector already retrieves evidence for an in-scope optional field, add a separate field observation rather than hiding it inside another field's excerpt.

Target status and field status have different grains. Keep target-stage attempts in `collection_attempts.jsonl` and target-field outcomes in observations or field-scoped coverage cells. A target can be terminal while one or more required fields remain blocked or unobserved.

For schema `1.3.0` and later, target, raw-evidence, field, and attempt links are explicit. Every collection attempt and observation refers to a planned `target_id`; every planned target-field pair has a deterministic coverage cell; and every observation's `raw_hash` resolves to `raw_artifacts.jsonl`. This closes the gap between declared interfaces and executed evidence.

For schema `1.4.0` and later, executor selection is also explicit. `run_manifest.json.coordination` records whether independent lanes were assessed, the child-agent delegation decision, its exception reason when applicable, and every considered external executor. A selected external executor resolves to both a real pilot attempt and an `external_cli` task; a declared child-agent delegation resolves to at least one `child_agent` task.

## Target and raw-artifact grain

A target is an immutable retrieval or discovery unit, not its latest execution status. `target_queue.jsonl` records its canonical locator, route, page and source class, semantic dimensions, planned fields, priority, shard, partition, and planner version. Attempts and tasks carry changing execution state.

Use a content-addressed raw store when retention is authorized. One raw-artifact row represents one target-attempt provenance link; multiple rows may reference the same stored hash. A stored row includes a relative path and byte count. An external or deliberately unretained artifact records its storage state and retention reason instead of pretending the payload was preserved.

## Stable grain and keys

Define the grain before collection. A field observation key should be composed from explicit business dimensions, for example:

`object_type | object_id | field | market | period`

Never use row order, batch number, page position, display label, or file name as identity. Normalize whitespace, case, Unicode, URLs, currencies, units, dates, timezones, locale, and known aliases before computing keys, while retaining the original raw value.

Each observation must include at least:

- `observation_id`, `run_id`, and `observation_key`
- `object_type`, `object_id`, `field`, `field_kind`
- `market`, `period`, `value`, `unit`, and `currency` when applicable
- `source_id`, `evidence_type`, and `source_strength`
- `observed_at`, `retrieved_at`, `route_version`, and `parser_version`
- `raw_hash` and optional raw locator

`field_kind` is `static`, `slowly_changing`, or `dynamic`. Missing, explicit zero, unavailable, not applicable, and withheld are distinct representations.

## Collection attempt grain

Use one `collection_attempts.jsonl` row per target, stage, adapter call, and attempt number. This ledger measures collection quantity and recovery without conflating HTTP success with useful data.

Each row must include:

- `attempt_id`, `run_id`, `batch_id`, `target_id`, and optional canonical locator
- `stage`: `discover`, `fetch`, `render`, `parse`, or `extract`
- `adapter`, `route_version`, and positive integer `attempt_no`
- `status`: `success`, `partial`, `empty`, `blocked`, `rate_limited`, `timeout`, `access_denied`, `challenge_blocked`, `transport_failed`, `parse_failed`, `invalid_target`, `skipped_duplicate`, or `interrupted`
- `started_at` and `finished_at`
- optional `retry_of_attempt_id`, cursor or checkpoint, and next route
- optional non-negative `valid_record_count` and `new_record_count`
- optional non-negative `elapsed_ms`, `cost`, `input_tokens`, `output_tokens`, and `bytes_received`
- optional `route_id` and `executor_class` for comparable resource allocation
- optional `provider_run_id`, `provider_version`, and `billing_model` when a managed or black-box route exposes them
- `error_category` and optional stable error fingerprint whenever the result is a failure

Keep the same `target_id` across retries and route changes. `attempt_id` is globally unique. A later success does not replace a failed row. `batch_id` groups a bounded, resumable unit but is never an identity key for the target or observation.

Canonicalize targets before assigning `target_id`: normalize scheme and host case, remove fragments and known tracking parameters, normalize locale rules deliberately, and prefer stable platform or listing identifiers when available. Preserve the original locator separately. Do not collapse URLs whose market, seller, variant, or language dimension is meaningful to the goal.

## Task and executor grain

Use one `tasks.jsonl` row per owned work lane. For schema `1.4.0` and later, every task also includes:

- `runner_class`: `lead`, `child_agent`, `external_cli`, `native_tool`, or `deterministic_code`
- exact `executor_id` and a concrete `dispatch_reason`
- `expected_output_schema`, `acceptance_metric`, and `escalation_condition`
- `allowed_side_effects` and `resource_lease_keys`
- for child agents, portable `model_tier` and `reasoning_tier`
- for external CLIs, current `readiness_state`

The partition lease prevents duplicate ownership of data; resource leases prevent two active tasks from racing on the same session, profile, port, credential context, output artifact, or other exclusive runtime. An empty resource list is valid when the lane has no exclusive runtime dependency. Thread count and request concurrency remain attempt telemetry, not runner classes.

## Deterministic materialization

The merger must produce the same current view regardless of input file order or batch order.

1. Validate schema and reject duplicate `observation_id` values with different payloads.
2. Deduplicate exact observations without changing provenance.
3. Group by `observation_key`.
4. For `dynamic` fields, prefer the latest valid `observed_at`, then stronger evidence, later retrieval, and stable ID as tie-breakers.
5. For `static` and `slowly_changing` fields, prefer stronger evidence, then later observation and retrieval times, while retaining alternate values.
6. Write one selected current row per key and one conflict record whenever distinct non-null values remain.
7. Never select `checked_no_confirmation`, `blocked`, or `unchecked` as a value. Those states belong in the coverage ledger.

Do not silently carry forward an older dynamic value when the current run has no valid observation. Surface it as stale historical context only when the deliverable explicitly allows that posture.

## Required regression properties

- idempotence: merging the same inputs twice produces the same output
- batch-order invariance: reordered input files produce the same output
- stable-key invariance: formatting normalization does not create duplicate identities
- conflict retention: competing values remain visible after materialization
- zero/missing separation: numeric zero never becomes blank or absent
- rebuildability: current views can be recreated from append-only records
- lineage: every selected value resolves to an observation and source
- recoverability: completed target-stage attempts and checkpoints are not replayed after restart
- retry traceability: every recovered target retains the failed attempt and changed route or condition
- metric reproducibility: collection funnel and route metrics rebuild from append-only attempts and observations
- field-contract parity: required fields cannot disappear between goal, dictionary, extractor, and acceptance layers
- terminalization separation: completing every target does not synthesize missing target-field observations
- target-plan reproducibility: reordered axis inputs produce the same targets, cells, and shard assignments
- raw-evidence linkage: every current-run observation resolves to a registered raw artifact or an explicit non-retention record
- telemetry honesty: missing cost or usage stays unknown and is never converted to zero
- dispatch visibility: selected child agents and external executors resolve to real tasks and pilots; non-selection has an explicit reason
- resource-lease exclusivity: active tasks cannot share a partition or exclusive runtime lease key

Use `../scripts/merge_observations.py`, `../scripts/summarize_collection_run.py`, and `../scripts/validate_research_run.py` for the base implementation. Extend the schema only when a recurring field requires it; version the schema and add a regression case.
