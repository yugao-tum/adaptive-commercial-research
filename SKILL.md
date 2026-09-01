---
name: adaptive-commercial-research
description: Plan and execute multi-source research about businesses, companies, brands, channels, products, platforms, and commercial operating relationships. Use when the work needs broad source discovery, explicit coverage boundaries, evidence grading, structured extraction, cross-batch merging, or coordinated research lanes. Do not use for a trivial one-fact lookup, purely academic or scientific literature research, software-only technical research, or writing that requires no new evidence gathering.
---

# Adaptive Commercial Research

Collect broader information without confusing more pages with better coverage. Define the research universe, route each field to the lightest reliable source path, preserve evidence and access boundaries, and produce a result that is traceable, mergeable, and easy to navigate.

## Establish the run

Before broad execution, identify the decision use, research objects, markets or jurisdictions, time boundary, requested deliverables, and anything that must be preserved. Only the user or a later explicit instruction may change these items; tool failures and partial findings may change the route, not the goal.

Determine research depth from the request. If depth is not already clear and it materially changes scope, time, or cost, ask once whether the user wants `quick`, `standard`, or `exhaustive`. If the user delegates the choice or asks to proceed without questions, use `standard` and state that assumption. Read [research-contract.md](references/research-contract.md) when the task is substantive, multi-stage, or ambiguous.

Select the narrowest useful mode:

- `operating-architecture`: entities, roles, ownership clues, contracting, logistics, compliance, and relationships.
- `coverage-sweep`: object x market x channel or site x alias coverage.
- `structured-extraction`: repeatable fields across products, listings, stores, or records.
- `enrichment-audit`: add or validate metrics, sources, fields, or evidence in an existing artifact.
- `mixed`: use only when the requested deliverable genuinely spans modes; retain one lead mode.

## Non-negotiable invariants

1. Define completeness against a declared source universe. Never claim that the internet itself was exhaustively searched.
2. Keep parent organization, legal entity, seller, store, brand, rightsholder, responsible party, logistics node, platform, site, product, listing, and variant separate until evidence closes the relationship.
3. Keep coverage state, evidence type, source strength, identity confidence, field completeness, and currentness as separate dimensions.
4. `blocked`, `unchecked`, empty content, login walls, rate limits, and timeouts are not business absence or numeric zero.
5. Preserve raw observations append-only. Only one deterministic merge step may write a current view; conflicts remain visible.
6. Never silently backfill a dynamic field from an older run. Preserve lineage for static fields and state staleness explicitly.
7. Treat installed or configured tools as `unknown` until a minimal real read succeeds in the current run. Installation is not runtime acceptance.
8. Research agents and helper skills may gather or assess evidence; the lead controller owns scope, schema, conflict resolution, merge approval, and final conclusions.
9. When repeated additions make the deliverable hard to navigate, preserve the source artifact and produce a clean integrated result instead of appending another patch.
10. Separate cheap discovery from expensive extraction. Canonicalize and deduplicate targets before rendering, browser interaction, OCR, or paid retrieval.
11. Log every target-stage attempt append-only. Retry only after classifying the failure and changing a relevant condition; retain failed attempts when recovery succeeds.
12. Preserve evidence semantics across route changes. Market, locale, currency, delivery context, identity scope, and session or login state must not change silently; diagnostic fallbacks with different semantics cannot populate the current evidence layer.
13. Before scaling, reconcile required, optional, and excluded fields across the goal contract, data dictionary, extractor output, merge layer, and acceptance metrics. A terminal target is not evidence that every required field is complete.
14. When an expensive retrieval already exposes several in-scope fields, extract every explicit field supported by that payload in the same pass, but create independent observations and never infer one field from another. Reparse preserved evidence before refetching.
15. Use the least expensive currently validated capability that can meet the task's evidence and reasoning requirements. Reserve stronger agents for scope, ambiguous semantics, route recovery, conflicts, and QA; use deterministic code for deterministic transformations.
16. Distinguish child-agent delegation, external CLI or helper-Skill dispatch, native tool calls, deterministic code, and request concurrency. For `standard` or `exhaustive` work, assess these runner classes before broad execution: when at least two independent lanes are ready, delegate a child lane when available and authorized, or record the concrete exception. Threads and concurrent requests do not count as agent delegation; merely listing an installed CLI does not count as dispatch.
17. Keep completeness and throughput in one feedback loop. Audit discovery boundaries separately from target-field coverage, then choose each next batch from unresolved required cells, source-family fairness, current-run route yield, retry state, and active leases. Do not let a high-yield route starve a required low-yield source family, and do not keep blocked or exhausted work in the runnable queue.

## Run the research

1. Create a compact goal contract, field contract, data dictionary, and declared source universe. For matrix-scale collection, use the planner to materialize stable targets, target-field cells, route candidates, discovery lineage, and partitions before retrieval. For `standard` or `exhaustive` work, also complete the coordination, discovery-control, and external-executor decisions in the run manifest before broad retrieval.
2. Normalize aliases and define the unit of analysis and stable keys before collecting at scale. Reconcile the field contract with the extractor and acceptance layer before the pilot.
3. If project instructions name a local source or platform playbook, load only the relevant target, market, and page-type section. Record the referenced route version and treat every historical route as a prior, not current readiness.
4. Run a small, diverse pilot across the hardest source and page types. Measure unique valid-record yield, required-field yield, stage success rates, precision, time, cost, duplicates, and blockers. Validate real target-field outcomes before expanding the queue.
5. Route by target field, source capability, and task complexity. During high-volume runs, select bounded next batches from the append-only control ledgers; expand, switch, escalate, or stop from observed net yield and coverage debt, not advertised features, model prestige, successful HTTP responses, or request counts.
6. Store discovery-frontier events, targets, batch decisions, sources, collection attempts, raw artifacts, observations, coverage states, conflicts, and task results separately. Persist each completed page, cursor, or bounded batch before continuing. Register reusable raw evidence before parsing so extractor fixes can reprocess it without refetching.
7. Classify material operational learning as run-only evidence, a project-playbook update, a deterministic code/test fix, or a Skill-maintenance candidate. Update an authorized project-local playbook before closeout when the evidence gate is met; do not self-modify an installed Skill during an ordinary research run.
8. Apply quality gates before synthesis: coverage visibility, claim-to-source traceability, key stability, conflict retention, currentness, and output navigation.
9. Deliver the answer using [output-contract.md](references/output-contract.md). Do not return a process diary or an unstructured bullet dump.

## Load details only when needed

- For source classes, evidence strength, coverage states, object separation, and completeness tests, read [evidence-and-coverage.md](references/evidence-and-coverage.md).
- For retrieval routes, readiness checks, managed or black-box collector evaluation, project-local playbooks, route lifecycle, learning promotion, fallbacks, access limits, and secret handling, read [tool-routing-and-readiness.md](references/tool-routing-and-readiness.md).
- For high-volume collection, auditable discovery frontiers, dynamic next-batch selection, failure recovery, and success metrics, read [collection-throughput-and-recovery.md](references/collection-throughput-and-recovery.md).
- For canonical JSONL records, stable keys, deterministic merge rules, and batch invariance, read [data-contract-and-merge.md](references/data-contract-and-merge.md).
- For child-agent triggers, runner-class separation, model capability tiers, ownership leases, result packages, single-writer rules, and recovery from blocked tasks, read [parallel-research-protocol.md](references/parallel-research-protocol.md) when multiple lanes, external executors, independent QA, or shared resources are in scope.
- For optional routing to other installed skills, read [skill-integrations.md](references/skill-integrations.md) and load only the selected skill's full instructions.
- For long or stakeholder-facing results, read [output-contract.md](references/output-contract.md).

## Deterministic helpers

- `scripts/init_research_run.py` creates a versioned run package after scope and depth are resolved.
- `scripts/record_discovery_frontier.py` appends auditable enumeration, pagination, cursor, saturation, and blocker events for the declared source universe.
- `scripts/plan_collection.py` expands bounded dimension templates into canonical targets, target-field coverage cells, and stable shards.
- `scripts/select_next_batch.py` chooses and records the next bounded batch from required-field debt, source-family fairness, current route yield, retry caps, and active leases.
- `scripts/register_raw_artifact.py` stores authorized raw payloads by content hash while retaining target and attempt provenance.
- `scripts/validate_pilot_output.py` verifies that real pilot targets have consistent field observations and terminal coverage states.
- `scripts/merge_observations.py` builds a deterministic current view while retaining conflicts.
- `scripts/summarize_collection_run.py` derives stage success, field completion, marginal batch yield, recovery, cost, and route or executor efficiency from append-only ledgers.
- `scripts/validate_research_run.py` checks contracts, IDs, states, references, task ownership, and merge outputs.

Run helpers with `--help` before first use. A passing structural validator is necessary but does not prove that the research conclusion is correct.
