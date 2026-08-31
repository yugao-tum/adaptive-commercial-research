# Data Contract and Merge

Use this contract when research spans multiple batches, tools, agents, or repeated refreshes.

## Canonical run package

The canonical machine layer is append-only JSONL plus versioned JSON contracts:

| File | Purpose |
|---|---|
| `goal_contract.json` | Immutable decision use, scope, depth, deliverables, and stopping rules |
| `run_manifest.json` | Run ID, schema version, mode, timestamps, input snapshot, route and parser versions |
| `data_dictionary.json` | Unit of analysis, stable keys, field semantics, types, units, and currentness classes |
| `coverage_plan.json` | Declared source universe, matrix dimensions, required cells, and completion rule |
| `sources.jsonl` | One source record per stable source ID |
| `collection_attempts.jsonl` | Append-only target-stage attempts, retries, checkpoints, failure classes, and route yield |
| `coverage.jsonl` | Append-only attempts and states for coverage cells |
| `observations.jsonl` | Append-only target-field observations |
| `tasks.jsonl` | Task ownership, attempts, checkpoints, and terminal states |
| `claims.jsonl` | Material conclusions and source links |
| `current_view.jsonl` | Deterministically materialized field values |
| `conflicts.jsonl` | Competing values and selected resolution |

CSV, spreadsheet, database, and narrative reports are derived views. They do not replace the canonical observations and provenance.

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
- `error_category` and optional stable error fingerprint whenever the result is a failure

Keep the same `target_id` across retries and route changes. `attempt_id` is globally unique. A later success does not replace a failed row. `batch_id` groups a bounded, resumable unit but is never an identity key for the target or observation.

Canonicalize targets before assigning `target_id`: normalize scheme and host case, remove fragments and known tracking parameters, normalize locale rules deliberately, and prefer stable platform or listing identifiers when available. Preserve the original locator separately. Do not collapse URLs whose market, seller, variant, or language dimension is meaningful to the goal.

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

Use `../scripts/merge_observations.py`, `../scripts/summarize_collection_run.py`, and `../scripts/validate_research_run.py` for the base implementation. Extend the schema only when a recurring field requires it; version the schema and add a regression case.
