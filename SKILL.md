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

## Run the research

1. Create a compact goal contract, data dictionary, source universe, and initial coverage matrix.
2. Normalize aliases and define the unit of analysis and stable keys before collecting at scale.
3. Run a small, diverse pilot across the hardest source and page types. Measure target-field yield, precision, time, cost, and blockers.
4. Route by target field and source capability. Expand, switch, or stop a route from observed net yield, not advertised features or request counts.
5. Store sources, observations, coverage states, conflicts, and task results separately. Use the scripts in `scripts/` when multiple batches or agents are involved.
6. Apply quality gates before synthesis: coverage visibility, claim-to-source traceability, key stability, conflict retention, currentness, and output navigation.
7. Deliver the answer using [output-contract.md](references/output-contract.md). Do not return a process diary or an unstructured bullet dump.

## Load details only when needed

- For source classes, evidence strength, coverage states, object separation, and completeness tests, read [evidence-and-coverage.md](references/evidence-and-coverage.md).
- For retrieval routes, readiness checks, fallbacks, access limits, and secret handling, read [tool-routing-and-readiness.md](references/tool-routing-and-readiness.md).
- For canonical JSONL records, stable keys, deterministic merge rules, and batch invariance, read [data-contract-and-merge.md](references/data-contract-and-merge.md).
- For independent work lanes, ownership leases, result packages, single-writer rules, and recovery from blocked tasks, read [parallel-research-protocol.md](references/parallel-research-protocol.md) only when parallel work is justified.
- For optional routing to other installed skills, read [skill-integrations.md](references/skill-integrations.md) and load only the selected skill's full instructions.
- For long or stakeholder-facing results, read [output-contract.md](references/output-contract.md).

## Deterministic helpers

- `scripts/init_research_run.py` creates a versioned run package after scope and depth are resolved.
- `scripts/merge_observations.py` builds a deterministic current view while retaining conflicts.
- `scripts/validate_research_run.py` checks contracts, IDs, states, references, task ownership, and merge outputs.

Run helpers with `--help` before first use. A passing structural validator is necessary but does not prove that the research conclusion is correct.
