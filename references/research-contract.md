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

## Completion and stopping

Completion is relative to the declared source universe. A run may be complete even with blocked or unresolved cells if those states are explicit and the agreed stopping conditions are met.

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
