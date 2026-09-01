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

Start with a representative sample for each proposed tier. Promote routine lanes only when their accepted field yield and precision are adequate; escalate exceptions rather than the whole queue. Downgrade or stop a tier when retry recovery or net-new yield is poor.

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

Set concurrency per host, route, and worker capability. Raise it gradually while accepted yield and latency remain stable; reduce it when blocker share, timeout rate, or duplicate work rises. A large blocked queue with low sampled recovery is a signal to change route or stop, not to add more premium agents.
