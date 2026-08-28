# Tool Routing and Readiness

Route from the target field and page type to a capability. Concrete tools are replaceable adapters, not the research architecture.

## Capability ladder

| Need | Start with | Escalate when |
|---|---|---|
| discover candidate sources | ordinary search, enabled search skill, sitemap, archive, or index | aliases, local language, or source-family gaps remain |
| read a known static page or document | native fetch or lightweight reader | content is incomplete, rendered dynamically, or blocked |
| interact with dynamic or protected content | browser-capable or JavaScript-capable retrieval | scale, geography, session, or repeatability requires another route |
| extract known URLs at scale | batch extraction with durable polling and resume | target fields are inconsistent or precision falls |
| discover a site | sitemap and robots first, then bounded map | site structure remains unknown; crawl only the required boundary |
| verify identity or legal relationships | official records, contractual pages, registries, filings, compliance documents | use weaker sources only as discovery clues |
| normalize, deduplicate, merge, or validate | deterministic local scripts | do not delegate deterministic merge logic to prose prompts |

Run a small, diverse pilot before scaling. Compare routes by target-field yield, precision, elapsed time, cost, blocker rate, and reproducibility. Request count and page count are not progress metrics.

## Runtime readiness

Use four states: `ready`, `degraded`, `blocked`, `unknown`.

Before declaring a route ready in the current run, verify the smallest relevant end-to-end path:

1. exact executable, endpoint, or skill is present
2. required version, flags, browser or runtime dependencies are available
3. authentication and permissions work for a read-only request
4. network and geography are appropriate for the target
5. one real target request returns non-empty, parseable, relevant content
6. batch routes can submit, poll, resume, and recover durable results when those features are required
7. a fallback route is known for a material source class

A version command, successful installer, visible GUI, configured connector, or historical success is not runtime acceptance. Store `last_verified_at`, target type, and actual result state.

## Installation boundary

This Skill owns readiness checks and routing, not unsolicited installation or environment repair. If a required capability is absent, report the gap and use an available fallback. Install, authenticate, or modify system configuration only when the user explicitly requests it or when a selected dedicated setup Skill is authorized to do so.

After installation or repair, repeat the real end-to-end acceptance request. Do not mark the route ready from installation output alone.

## Retry and switching

Retry only when the failure is plausibly transient or the next attempt changes a relevant parameter. Cap identical retries. After repeated failure, switch route, reduce scope, or return `blocked` with the exact boundary. Do not allow one blocked source to monopolize the run queue.

Record route events with target field, source class, page type, adapter, attempt, result, blocker, yield, precision, cost, and elapsed time. Use this ledger to improve future routing rather than adding page-specific rules to the main prompt.

## Security and access

Keep credentials in environment variables, credential stores, or user-controlled sessions. Never place tokens, cookies, authorization codes, or private keys in prompts, logs, reports, fixtures, or Skill files. Use the minimum read permission needed and do not convert read-only research into external writes without separate authorization.

For optional installed Skill routing, read [skill-integrations.md](skill-integrations.md).
