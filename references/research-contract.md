# Research Contract

Use this reference when the task has multiple objects, markets, sources, batches, agents, or deliverables.

## Goal contract

Keep the contract compact and machine-readable:

| Field | Meaning |
|---|---|
| `goal_id` | Stable identifier for this research decision |
| `decision_use` | What decision the research will support |
| `in_scope` | Objects, markets, periods, fields, and relationships included |
| `out_of_scope` | Explicit exclusions |
| `required_fields` | Fields whose completion affects acceptance |
| `optional_fields` | In-scope fields worth collecting when the same evidence exposes them |
| `excluded_fields` | Fields that must not drive retrieval, extraction, or acceptance |
| `deliverables` | Human and machine outputs required |
| `must_preserve` | Existing structure, source artifacts, definitions, or user constraints |
| `success_conditions` | Observable completion conditions |
| `stop_conditions` | Cost, time, risk, saturation, or authorization boundaries |
| `assumptions` | Assumptions that could affect interpretation |
| `change_log` | User-authorized changes to goal or scope |

The goal contract is immutable during ordinary execution. Strategies, routes, retries, and task partitions are mutable. Record a goal change only when the user or a later explicit instruction changes the decision use, scope, priority, or deliverable.

## Depth selection

Depth materially affects scope and cost. Infer it from explicit wording; otherwise ask once before broad execution.

| Depth | Appropriate use | Minimum posture |
|---|---|---|
| `quick` | Orientation or a narrow fact pattern | A few strong sources, visible caveats, no completeness claim |
| `standard` | Default commercial research | Multiple relevant source families, key claims cross-checked, coverage summary, material gaps visible |
| `exhaustive` | User asks for complete, comprehensive, audit-ready, or batch-scale work | Declared source universe, full matrix states, durable run package, saturation test, deterministic merge, independent QA when useful |

If the user delegates the depth choice or asks not to be questioned, select `standard`. Never silently downgrade an explicit exhaustive request because a route is blocked; report the incomplete cells.

## Lead mode and unit of analysis

Choose one lead mode even when supporting modes are needed. Lock the unit before collection, for example:

- organization x legal role x jurisdiction
- brand or store alias x market x channel
- product x listing x variant x observation time
- root domain x market x metric x period

Define which fields are static identity, slowly changing, or dynamic. Record timezone, currency, unit, market, period, and language assumptions when they affect comparability.

## Cross-layer field contract

For structured extraction or enrichment, maintain one explicit field contract with `required_fields`, `optional_fields`, and `excluded_fields`. For each required or optional field, define its grain, semantics, admissible evidence, missing states, currentness class, destination, and completion test.

Before scaling, reconcile the same field names across:

1. goal and field contracts
2. data dictionary and observation schema
3. extractor or parser output
4. merge and destination mappings
5. acceptance metrics and final coverage report

A required field missing from any layer is a contract defect, not permission to narrow the task silently. An excluded field must not consume requests or appear in acceptance metrics. Optional fields may be collected from already-retrieved evidence, but must not expand retrieval cost unless the user or goal contract authorizes that expansion.

When the user adds or removes a field, record one authorized contract change and propagate it through every downstream layer before further collection. Do not leave an obsolete field in queues, validators, or success statistics.

## Completion and stopping

Completion is relative to the declared source universe. A run may be complete even with blocked or unresolved cells if those states are explicit and the agreed stopping conditions are met.

Track two independent completion axes:

- **target terminalization:** every target has a final success, no-confirmation, blocked, invalid, or other agreed terminal state
- **field completion:** every required target-field cell is populated or has an explicit allowed terminal state

Do not report “all fields complete” merely because every target was attempted or terminalized. Acceptance should show required-field coverage separately from route completion, with optional-field yield reported as useful enrichment rather than a hidden success criterion.

For standard work, stop broadening when key claims have adequate evidence, all high-priority source families have a state, material contradictions are exposed, and another route is unlikely to change the decision.

For exhaustive work, stop only when every required coverage cell is `checked_hit`, `checked_no_confirmation`, or `blocked`; aliases and local-language variants were expanded; critical relationships meet the evidence threshold; and marginal high-value yield has plateaued or a stated resource boundary was reached.

## Repair without prompt accretion

Classify failures before changing the Skill or run:

| Layer | Examples | Correct repair location |
|---|---|---|
| target | Wrong objective, scope, or deliverable | Goal contract or explicit user decision |
| schema | Mixed objects, ambiguous field, unstable key | Data dictionary or schema reference |
| route | Page type or source path does not yield the field | Route registry or tool reference |
| merge | Order-dependent or stale materialization | Deterministic merge script and regression test |
| coordination | Duplicate ownership, blocking dependency | Task protocol |
| presentation | Correct evidence is hard to locate | Output contract |
| one-off | Temporary outage or isolated page anomaly | Run log; do not create a universal rule |

Admit a new permanent rule only when the failure recurs, changes a decision, is expensive if repeated, and cannot be enforced more reliably by data or code. Add a regression test, then replace or supersede the old rule instead of appending a second version.
