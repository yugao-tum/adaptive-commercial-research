# Adaptive Commercial Research

A Codex Skill for multi-source commercial research with explicit scope, evidence coverage, tool readiness, deterministic batch merging, and navigable conclusions.

It is designed for research about businesses, companies, brands, channels, products, platforms, and commercial operating relationships. It does not try to replace specialist scientific, investment, or data-quality workflows; it routes to them when they are the better lead.

## What it adds

- A stable goal contract so retrieval failures cannot silently change the objective.
- A cross-layer field contract that prevents required fields from disappearing between scope, extraction, merging, and acceptance.
- Quick, standard, and exhaustive research depths; unclear depth is resolved before broad execution.
- Separate coverage, evidence type, source strength, confidence, completeness, and currentness states.
- A declared source universe with checked, no-confirmation, blocked, and unchecked boundaries.
- Runtime acceptance tests for tools instead of treating installation as readiness.
- A bounded black-box collector protocol that separates observable service behavior, private implementation, managed environment advantages, reuse rights, and local capability gaps.
- Optional project-local source and platform playbooks that remain historical priors until a current pilot validates them.
- A two-pass discovery and extraction pipeline that increases unique valid records without sending every target through the most expensive route.
- Adaptive per-host batches, classified failures, route-changing retries, durable checkpoints, and retained recovery history.
- A reproducible collection funnel covering discovery, fetch, parse, extraction, valid-record yield, duplicates, unresolved targets, and retry recovery.
- Deterministic target-universe expansion, canonical target-field cells, explicit exclusions, and stable shards.
- Append-only discovery-frontier events that make pagination, cursor, saturation, and blocker boundaries auditable.
- Deterministic next-batch selection from required-field debt, source-family fairness, observed route yield, retry caps, and active leases.
- Content-addressed raw-evidence registration for reparse-before-refetch recovery.
- Pilot output gates that test actual emitted fields rather than trusting extractor declarations.
- Field-, batch-, route-, executor-, cost-, token-, latency-, and byte-level efficiency summaries.
- One-pass extraction of independently evidenced in-scope fields from expensive payloads, with reparse-before-refetch recovery.
- Append-only JSONL observations with deterministic current views and retained conflicts.
- A single-lead parallel research protocol that prevents agents from competing for the master result.
- A mandatory dispatch assessment that distinguishes child agents, external CLIs, native tools, deterministic code, and request concurrency, with explicit non-dispatch reasons.
- Role-based agent, model, quota, and concurrency tiering driven by accepted yield rather than model prestige.
- Versioned child-agent prompts and traceable prompt, reasoning, model, or executor escalation with run-level caps.
- A conclusion-first output contract with stable claim, source, gap, blocker, conflict, and action IDs.
- A learning-disposition gate that keeps one-off failures in run evidence, platform knowledge in project playbooks, deterministic defects in code/tests, and only cross-source invariants in the Skill.

## Install

Clone the repository into the Codex skills directory:

```powershell
Set-Location "$env:USERPROFILE\.codex\skills"
gh repo clone yugao-tum/adaptive-commercial-research
```

Restart or refresh Codex so the Skill is rediscovered. Invoke it explicitly with `$adaptive-commercial-research`, or let Codex select it for substantive multi-source commercial research.

## Example requests

```text
Use $adaptive-commercial-research to map the operating entities, sales roles,
channel presence, and unresolved evidence gaps for this business across several markets.
Ask me to choose the research depth before broad execution.
```

```text
Use $adaptive-commercial-research to collect the same product fields across multiple
sites and batches. Preserve source lineage, distinguish zero from missing, and produce
an order-invariant merged dataset plus a concise conclusion report.
```

## Structure

```text
adaptive-commercial-research/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── research-contract.md
│   ├── evidence-and-coverage.md
│   ├── tool-routing-and-readiness.md
│   ├── collection-throughput-and-recovery.md
│   ├── collection-plan-schema.md
│   ├── data-contract-and-merge.md
│   ├── parallel-research-protocol.md
│   ├── skill-integrations.md
│   └── output-contract.md
├── scripts/
│   ├── init_research_run.py
│   ├── plan_collection.py
│   ├── record_discovery_frontier.py
│   ├── select_next_batch.py
│   ├── register_raw_artifact.py
│   ├── validate_pilot_output.py
│   ├── merge_observations.py
│   ├── summarize_collection_run.py
│   └── validate_research_run.py
└── tests/test_runtime.py
```

`SKILL.md` contains the activation boundary, operating modes, invariants, and routing. Detailed rules are loaded from `references/` only when relevant. The scripts implement deterministic behavior that should not depend on prompt wording.

## Runtime helpers

Create a new run package after the goal, lead mode, and depth are resolved:

```powershell
python scripts/init_research_run.py `
  --output .\run-example `
  --goal "Map the requested commercial evidence" `
  --decision-use "Support a channel decision" `
  --mode coverage-sweep `
  --depth standard `
  --cost-unit credits `
  --required-field price `
  --optional-field seller `
  --excluded-field orderable
```

For schema 1.2 and later runs, complete `field_contract.json` with the extractor output fields and acceptance fields before broad execution. Strict validation rejects a required field that was silently omitted by either layer.

Schema 1.3 adds `target_queue.jsonl` and `raw_artifacts.jsonl`. Use a project-local JSON plan to expand bounded axes and templates without embedding source-specific locators in the Skill:

```powershell
python scripts/plan_collection.py .\run-example --spec .\collection-plan.json
```

Schema 1.4 adds an execution-routing contract. Before broad `standard` or `exhaustive` work, complete `run_manifest.json.coordination`; selected child agents and external CLIs must resolve to real `tasks.jsonl` assignments, while non-selection retains a concrete reason.

Schema 1.5 adds an adaptive collection loop. Complete `run_manifest.json.collection_control`, record cursor or pagination progress when the universe is not a deterministic matrix, and link project plan templates to their candidate routes and frontier IDs:

```powershell
python scripts/record_discovery_frontier.py .\run-example `
  --source-class channel-native `
  --method cursor `
  --entrypoint "https://example.test/api/items" `
  --state active `
  --cursor PAGE_TOKEN

python scripts/select_next_batch.py .\run-example --limit 20
```

The selector appends an idempotent decision package to `batch_decisions.jsonl`; it does not bypass task ownership or mutate the immutable target queue.

Validate a completed pilot partition before scale-up:

```powershell
python scripts/validate_pilot_output.py .\run-example --shard-id 0 --strict
```

Materialize observations while preventing silent backfill of current dynamic fields:

```powershell
python scripts/merge_observations.py `
  .\run-example\observations.jsonl `
  --output .\run-example\current_view.jsonl `
  --conflicts .\run-example\conflicts.jsonl `
  --current-run-id RUN_ID
```

Summarize collection quantity, stage success, route yield, unresolved targets, and retry recovery:

```powershell
python scripts/summarize_collection_run.py `
  .\run-example `
  --output .\run-example\collection_metrics.json
```

Validate the complete run package:

```powershell
python scripts/validate_research_run.py .\run-example --strict
```

## Optional Skill routing

When installed and relevant, the Skill can route bounded work to internet retrieval, internal business-context gathering, structured data-quality analysis, public-equity research, life-science research, or Skill maintenance. Only one Skill remains the lead for scope, conflict resolution, and the final answer. See `references/skill-integrations.md`.

## Validation

The repository test suite checks:

- required Skill files and local reference links
- safe run initialization
- goal-contract drift rejection
- cross-layer required, optional, and excluded field parity
- batch-order invariance and idempotence
- conflict retention and deterministic selection
- prevention of stale dynamic-field backfill
- strict cross-file run validation
- collection-attempt schema and retry-link validation
- deterministic collection funnel and retry-recovery metrics
- deterministic target planning and stable shard assignment
- content-addressed raw-payload deduplication and provenance
- actual target-field pilot acceptance
- field-level completion and marginal batch efficiency metrics
- discovery-frontier identity, terminal-state, and source-family checks
- deterministic, idempotent next-batch decisions with route-yield feedback
- prompt/model/reasoning escalation lineage and caps

Run it with:

```powershell
python -m unittest discover -s tests -v
```

## Security

Do not place tokens, cookies, authorization codes, private keys, or private source content in Skill files, fixtures, prompts, logs, or public reports. Keep credentials in environment variables, credential stores, or user-controlled sessions.

## License

MIT. See [LICENSE](LICENSE).
