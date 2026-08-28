# Parallel Research Protocol

Load this reference only when the work has at least two independent evidence lanes or comparison units and the retrieval benefit exceeds coordination cost.

## When not to parallelize

Keep the work single-threaded when scope or identifiers are unresolved, later steps depend tightly on earlier results, one focused Skill can answer the request, the task is a narrow follow-up, or agents would need to edit the same artifact.

## Ownership model

| Role | Owns | Must not do |
|---|---|---|
| lead controller | goal, depth, schema, partitions, conflict decisions, merge approval, final answer | silently change user scope |
| evidence-lane worker | bounded source family, jurisdiction, market, object set, or field set | write the master view or final conclusion |
| structured extractor | repeatable extraction after a route and schema pass the pilot | redefine grain or field semantics |
| merger | deterministic normalization and materialization | invent missing evidence or smooth conflicts |
| independent QA | coverage, provenance, merge invariants, overclaiming, and navigation | begin with the expected conclusion when independence matters |

For standard work, the controller may also merge and QA. For exhaustive or high-impact work, separate QA when agents are available and authorized.

## Partition rules

Partitions must be mutually exclusive and collectively traceable. Split by one or more stable dimensions:

- source family
- jurisdiction or market
- channel or page archetype
- object or alias set
- target field group
- workflow stage after prerequisites are complete

Do not partition by vague instructions such as “research broadly.” Each task gets a unique `task_id`, `goal_id`, immutable input snapshot, partition key, owner lease, expected output schema, stopping condition, and allowed side effects.

Only one active lease may exist for a partition key. Expired or blocked work returns to the queue with its checkpoint; it is not silently duplicated.

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
