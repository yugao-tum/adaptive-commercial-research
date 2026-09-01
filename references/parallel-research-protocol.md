# Parallel Research Protocol

Load this reference only when the work has at least two independent evidence lanes or comparison units and the retrieval benefit exceeds coordination cost.

## When not to parallelize

Keep the work single-threaded when scope or identifiers are unresolved, later steps depend tightly on earlier results, one focused Skill can answer the request, the task is a narrow follow-up, or agents would need to edit the same artifact.

## Separate runner classes before dispatch

Parallel requests are not the same as parallel reasoning. Assign every planned lane one runner class before broad execution:

| Runner class | Appropriate work | Does not count as |
|---|---|---|
| `lead` | goal, schema, routing, conflicts, merge approval, and final conclusion | independent review |
| `child_agent` | a mutually independent evidence lane, semantic exception set, route diagnosis, or independent QA | bulk request concurrency |
| `external_cli` | a distinctive retrieval, analysis, or runtime capability that passed a real pilot | readiness merely because it is installed |
| `native_tool` | bounded search, browser, connector, or application calls controlled by the lead or worker | a separate agent unless it has independent ownership and a result package |
| `deterministic_code` | queue execution, normalization, parsing, deduplication, merge, counting, and invariant checks | semantic judgment |

Do not describe multiple browser tabs, server threads, shell processes, asynchronous requests, or model calls owned by the same controller as child-agent delegation. They may improve throughput, but they share one reasoning owner.

## Mandatory dispatch assessment

For every `standard` or `exhaustive` run, complete `run_manifest.json.coordination` before broad execution. Count only lanes whose scope, partition key, input snapshot, output schema, acceptance metric, and resource needs are already stable.

When at least two mutually independent lanes are ready and delegation is available and authorized, delegate at least one lane to a child agent and assign distinct owners to other ready lanes up to safe concurrency. Explicit user permission removes the authorization barrier; once the independence and benefit gates also pass, do not leave delegation as a merely optional suggestion.

If delegation does not occur, record one concrete decision: `single_lane`, `coordination_cost`, `unavailable`, `unauthorized`, or `unsafe_shared_state`, plus the reason. A lead-only run with two or more declared independent lanes must not pass strict validation without that exception. For exhaustive or high-impact work, use a separate independent QA lane when available and authorized; otherwise record the same exception rather than treating self-review as independent.

External executors use a parallel decision gate in [tool-routing-and-readiness.md](tool-routing-and-readiness.md). A selected CLI or helper Skill must receive a real task and pilot attempt; reading its documentation, checking its version, or mentioning it in the plan is not dispatch.

## Ownership model

| Role | Owns | Must not do |
|---|---|---|
| lead controller | goal, depth, schema, partitions, conflict decisions, merge approval, final answer | silently change user scope |
| evidence-lane worker | bounded source family, jurisdiction, market, object set, or field set | write the master view or final conclusion |
| structured extractor | repeatable extraction after a route and schema pass the pilot | redefine grain or field semantics |
| merger | deterministic normalization and materialization | invent missing evidence or smooth conflicts |
| independent QA | coverage, provenance, merge invariants, overclaiming, and navigation | begin with the expected conclusion when independence matters |

For standard work, the controller may also merge and QA. For exhaustive or high-impact work, separate QA when agents are available and authorized.

## Capability and resource tiering

Do not assign every lane the strongest model, highest reasoning level, or maximum concurrency. Match resources to the work:

| Work type | Default execution |
|---|---|
| goal, schema, field semantics, route design, conflict resolution, final synthesis | strong reasoning under the lead controller |
| repeatable extraction after a validated pilot | lowest-cost agent or model that passes the same field and evidence checks |
| normalization, deduplication, merge, counting, export, and invariant checks | deterministic local code |
| ambiguous identity, variant semantics, parser exceptions, or route recovery | escalate only the affected cases |
| independent QA | strong reviewer on a risk-based sample plus all exceptions |

Alternative quotas or external agents may handle routine work only after a current-run real-target pilot proves the required tools, output schema, privacy boundary, and accuracy. Available credit or speed is not evidence of capability. Record the executor class, material model or route version, cost, latency, and accepted yield so later allocation is evidence-based.

Map the models available in the current environment to portable capability tiers instead of hard-coding provider-specific names:

| Model tier | Default work | Reasoning tier |
|---|---|---|
| `strong_reasoning` | lead control, ambiguous semantics, route recovery, conflict resolution, and independent QA | `high`, reduced only when the pilot supports it |
| `balanced` | bounded evidence lanes, parser review, and routine semantic extraction | `medium` |
| `low_cost` | pilot-validated repetitive discovery, classification, or formatting | `low` |

Record the selected `model_tier`, reasoning tier, and exact executor ID in each child-agent task. Do not let every child silently inherit the lead's model. If a tier is unavailable, use the closest available tier, record the substitution in `dispatch_reason`, and preserve the same acceptance gate.

Start with a representative sample for each proposed tier. Promote routine lanes only when their accepted field yield and precision are adequate; escalate exceptions rather than the whole queue. Downgrade or stop a tier when retry recovery or net-new yield is poor.

## Prompt, model, and reasoning escalation

For schema `1.5.0` and later, version every child-agent task contract and classify acceptance before escalation. Diagnose in this order:

1. missing evidence, unavailable tool, blocked route, or runtime failure;
2. ambiguous partition, output schema, acceptance metric, or stopping condition;
3. skipped reasoning steps despite sufficient evidence;
4. repeated semantic, identity, or conflict errors after the contract is clear; and
5. coordination or resource-lease conflict.

Fix evidence, route, runtime, partition, or prompt-contract defects at their own layer. Increase reasoning one tier only for omitted multi-step analysis or premature conclusions. Increase model capability only when sufficient inputs and a clear contract still produce repeated semantic errors on representative samples. Change one capability variable per pilot when attribution matters; otherwise the controller cannot tell why performance changed.

Record `prompt_version`, `acceptance_result`, `failure_class`, `escalated_from_task_id`, `escalation_step`, and `max_escalations`. A partial or failed parent may create one exception task on the same goal snapshot and partition, but the child must change its prompt version, model tier, reasoning tier, or executor. Do not describe an unchanged retry as escalation. Stop or return the exception after the run-level cap; do not promote the whole queue because one case failed.

Keep the child prompt as a compact task contract: task and goal IDs, immutable snapshot, one partition, permitted evidence and tools, expected output schema, acceptance metric, stop condition, escalation condition, side-effect boundary, and resource leases. Replace superseded rules and increment `prompt_version`; do not append full conversation history or every prior exception to the prompt.

## Partition rules

Partitions must be mutually exclusive and collectively traceable. Split by one or more stable dimensions:

- source family
- jurisdiction or market
- channel or page archetype
- object or alias set
- target field group
- workflow stage after prerequisites are complete

Do not partition by vague instructions such as “research broadly.” Each task gets a unique `task_id`, `goal_id`, immutable input snapshot, partition key, owner lease, runner class, exact executor ID, dispatch reason, expected output schema, acceptance metric, escalation condition, allowed side effects, and resource lease keys.

Only one active lease may exist for a partition key. Expired or blocked work returns to the queue with its checkpoint; it is not silently duplicated.

For matrix-scale collection, prefer the stable `shard_id` and `partition_key` produced by `plan_collection.py` over handwritten row ranges. The same target plan and shard count must reproduce the same ownership boundaries. Changing shard count creates a new plan revision and requires the controller to reconcile completed targets before issuing new leases.

## Worker result package

Workers return append-only packages containing:

- task and goal IDs plus input snapshot hash
- attempted coverage cells
- source records and observations
- checked-no-confirmation and blocked states
- conflicts and unresolved identifiers
- route metrics and checkpoints
- artifacts produced and exact limitations

Workers do not edit the master report or current view. The controller rejects results with a mismatched goal ID, schema version, partition, or snapshot.

## Avoiding deadlock and distortion

Use durable checkpoints after each completed partition or batch. Limit identical retries; route-switch or return `blocked` after the cap. Do not make downstream tasks wait for a source that is optional to the decision. Escalate only prerequisites whose absence changes the agreed deliverable or evidence posture.

The controller periodically reconciles coverage, not prose length. Progress is net new high-priority coverage, target-field yield, resolved conflicts, and reduced uncertainty. Pages, requests, tokens, and raw record counts are not sufficient progress measures.

Set concurrency per host, route, and worker capability. Raise it gradually while accepted yield and latency remain stable; reduce it when blocker share, timeout rate, or duplicate work rises. A large blocked queue with low sampled recovery is a signal to change route or stop, not to add more premium agents.
