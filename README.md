# Adaptive Commercial Research

A Codex Skill for multi-source commercial research with explicit scope, evidence coverage, tool readiness, deterministic batch merging, and navigable conclusions.

It is designed for research about businesses, companies, brands, channels, products, platforms, and commercial operating relationships. It does not try to replace specialist scientific, investment, or data-quality workflows; it routes to them when they are the better lead.

## What it adds

- A stable goal contract so retrieval failures cannot silently change the objective.
- Quick, standard, and exhaustive research depths; unclear depth is resolved before broad execution.
- Separate coverage, evidence type, source strength, confidence, completeness, and currentness states.
- A declared source universe with checked, no-confirmation, blocked, and unchecked boundaries.
- Runtime acceptance tests for tools instead of treating installation as readiness.
- Append-only JSONL observations with deterministic current views and retained conflicts.
- A single-lead parallel research protocol that prevents agents from competing for the master result.
- A conclusion-first output contract with stable claim, source, gap, blocker, conflict, and action IDs.

## Install

Clone the repository into the Codex skills directory:

```powershell
git clone https://github.com/yugao-tum/adaptive-commercial-research.git "$env:USERPROFILE\.codex\skills\adaptive-commercial-research"
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
│   ├── data-contract-and-merge.md
│   ├── parallel-research-protocol.md
│   ├── skill-integrations.md
│   └── output-contract.md
├── scripts/
│   ├── init_research_run.py
│   ├── merge_observations.py
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
  --depth standard
```

Materialize observations while preventing silent backfill of current dynamic fields:

```powershell
python scripts/merge_observations.py `
  .\run-example\observations.jsonl `
  --output .\run-example\current_view.jsonl `
  --conflicts .\run-example\conflicts.jsonl `
  --current-run-id RUN_ID
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
- batch-order invariance and idempotence
- conflict retention and deterministic selection
- prevention of stale dynamic-field backfill
- strict cross-file run validation

Run it with:

```powershell
python -m unittest discover -s tests -v
```

## Security

Do not place tokens, cookies, authorization codes, private keys, or private source content in Skill files, fixtures, prompts, logs, or public reports. Keep credentials in environment variables, credential stores, or user-controlled sessions.

## License

MIT. See [LICENSE](LICENSE).
