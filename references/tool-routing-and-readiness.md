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

For large collection runs, keep one lead adapter per source partition and one explicit fallback. Choose adapters by capability rather than popularity:

| Route capability | Required behavior |
|---|---|
| search, sitemap, feed, or site map | return discoverable locators with pagination or cursor boundaries |
| lightweight fetch | expose status, headers, final URL, raw payload, and retry guidance |
| rendered or browser retrieval | preserve session and locale intentionally; detect challenge and empty-shell pages |
| structured endpoint, API, or export | expose stable identifiers, pagination, limits, and schema version when available |
| batch crawler | durable queue, per-host concurrency, deduplication, checkpoints, partial-result recovery, and dead-letter handling |
| parser or extractor | versioned schema, raw-payload preservation, record-level validation, and reparse without refetch |

Do not install several overlapping crawlers merely to increase theoretical coverage. Pilot the available routes, assign the best observed route to each partition, and retain another route only when it handles a distinct failure class.

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

## Dispatch gate for external executors

Do not enumerate every executable on the machine. Build a small candidate roster from tools or CLIs named by the user, project instructions, selected Skill integrations, or a material capability gap in the current route. For each candidate, record one `external_executor_decisions` entry in the run manifest:

| Decision | Use when |
|---|---|
| `selected` | its distinctive capability passed a real read-only target pilot and it has a bounded task |
| `duplicate_capability` | a validated current route already provides the same capability at equal or better yield and cost |
| `unavailable` | the executable, endpoint, compatible version, or dependency is absent |
| `auth_blocked` | required authorized credentials or permissions are unavailable |
| `cost_blocked` | the needed paid run is not authorized or exceeds the declared ceiling |
| `failed_pilot` | a real target attempt failed its content, identity, field, recovery, or economics gate |
| `not_needed` | the capability does not close a material coverage or quality gap in this run |

For a `selected` or `failed_pilot` candidate, link the decision to its append-only pilot attempt. A selected executor must also own an `external_cli` task with an explicit output schema, acceptance metric, escalation condition, and runtime readiness state. Do not mark a candidate selected after only reading documentation, printing help, checking a version, or confirming login.

After a pilot passes, give the executor a mutually exclusive bounded lane. Keep the lead controller responsible for the goal, evidence contract, merge, and final conclusion. If the CLI is a semantic model rather than a deterministic retriever, treat its output as a worker package that must pass the same evidence and field gates as a child agent. If it is only a deterministic runtime, do not pretend its parallel processes are independent agents.

This gate prevents two opposite failures: never invoking a distinctive available capability, and invoking many overlapping CLIs merely because they are installed. Strict validation checks that selected executors have both a pilot attempt and a task assignment.

## Evaluate managed and black-box collectors

A publicly listed or callable collector is not necessarily open source, locally reproducible, or licensed for copying. Before treating a managed crawler, hosted extraction service, or opaque API as reusable technology, separate five layers:

| Layer | What may be learned from a bounded run | What must not be assumed |
|---|---|---|
| interface | accepted inputs, output schema, pagination controls, limits, and error contract | undocumented inputs remain stable |
| observable behavior | runtime signatures, request ordering, retries, fallbacks, queue behavior, timing, and itemized charges when exposed | logs reveal every request header, selector, cookie, or decision |
| implementation | exposed source files, dependency metadata, parser behavior, and version identifiers | a public service exposes its private source, selectors, or fingerprint logic |
| execution environment | geographic route, session behavior, durable storage, queueing, or managed network capability when evidenced | copying wrapper code reproduces the provider's network, proxy pool, or reputation |
| reuse rights | license, repository terms, or an explicit permission | the right to run a service grants the right to copy its implementation |

Locate the earliest failing stage before adding tools or rewriting code. The following are diagnostic inferences, not automatic proof:

| Observed boundary | Likely capability gap to test next |
|---|---|
| a known-good target yields no relevant payload before parsing | reachability, egress, geography, session, or managed runtime |
| a relevant payload arrives but contracted fields present in the payload are not emitted | parser, selector, normalization, or schema contract |
| exact targets work but page two, cursors, or deep listings do not progress | discovery or pagination control |
| records appear but restart loses work or repeats accepted targets | queue durability, checkpointing, identity, or merge logic |
| output is valid but cost or latency rises sharply with depth | route economics, concurrency, optional expansion, or source limits |

Use one diagnostic cohort instead of an unbounded trial. Include known-good exact targets, a listing or search entry, a second-page or cursor case, and a hard or negative case under the same declared market and field contract. Set explicit record, time, and cost ceilings; disable expensive optional expansions unless they are themselves under evaluation. Preserve the provider run identifier, version, input, output, logs, queue or cursor evidence, route class when exposed, and itemized cost without recording credentials.

Accept the route only after checking identity precision, required-field yield, pagination progress, duplicate or loss behavior, resume semantics, and actual cost per accepted record. Then choose deliberately:

- exposed source with compatible license: adapt it with provenance and tests
- observable interface without reusable source rights: implement against the interface or perform a clean-room rewrite; do not copy private behavior
- stable black-box output with acceptable economics: keep it as a versioned upstream adapter while retaining local validation, merge, and QA ownership
- provider-only environment advantage: record that the missing capability is environmental rather than claiming that wrapper code will reproduce it locally
- failed identity, pagination, recovery, or cost gate: do not scale

Launching a paid run, creating an account, or consuming external credits requires the corresponding user authorization. Keep tokens in a credential store or environment variable, never in the prompt, run ledger, fixture, or Skill.

## Project-local route knowledge

A project may maintain a source- or platform-specific playbook. It is a long-lived operational prior, not a second copy of this Skill and not evidence that a route is ready now.

When a project playbook is named by project instructions or run configuration:

1. Load only the section for the current source or platform, market, and page type; do not load an entire catalog when one adapter is in scope.
2. Keep the playbook path outside this portable Skill. Record the consulted `route_id`, `route_version`, and playbook revision in the run manifest or collection attempts.
3. Re-run the smallest relevant readiness pilot before scaling. A historical success, route pattern, field coverage table, or past blocker is not current acceptance.
4. Preserve the old record when a route changes. Add a new route version and explicitly relate it to the route it supersedes or diagnoses.

Keep long-lived knowledge state separate from current runtime state:

| Knowledge state | Meaning |
|---|---|
| `candidate` | plausible route or optimization not yet supported by a diverse pilot |
| `historical_prior` | executed or observed previously, but not accepted in the current environment |
| `validated` | passed the project's current evidence gate for the stated market, page type, and fields |
| `superseded` | retained for provenance or fallback analysis after a better route replaced it |
| `retired` | known to be invalid, unsafe, or outside the maintained scope |

Each maintained route should identify: `route_id`, route version, source or platform, market and locale, delivery or session boundary when material, page type and stage, adapter and material configuration, knowledge state, `last_verified_at`, pilot scope, target-field yield and precision, blocker fingerprints, provenance run/attempt IDs, and any superseded route.

Route changes must preserve business semantics. Changing country, locale, currency, delivery location, account, session, or login state creates a different evidence context and must be recorded as a separate route event. A route with different semantics may diagnose transport or blocking behavior, but its values must not populate the original current view.

Use an isolated browser context by default. Attach an existing browser profile, CDP session, or user login only when it is necessary for the agreed source, the access is authorized, and the resulting session boundary is recorded.

## Learning disposition and promotion

Do not turn every failed page or successful workaround into permanent guidance. At a stable checkpoint or run close, classify material learning by its correct owner:

| Finding | Correct destination |
|---|---|
| transient outage, one-off page anomaly, or unconfirmed hypothesis | append-only run attempts only |
| repeatable source/platform route, blocker signature, field semantic, or stopping rule | project-local playbook with route version and provenance |
| deterministic parsing, normalization, merge, or validation defect | code plus a regression test; the playbook may record the operational effect |
| cross-source decision rule or safety/correctness invariant | Skill-maintenance candidate |
| changed objective, market, scope, or deliverable | goal contract or explicit user decision |

An ordinary research run may update a project-local playbook when project instructions authorize maintenance and the finding passed the stated evidence gate. It must not edit the installed Skill. Promote a Skill candidate only in an explicit Skill-maintenance task, using [research-contract.md](research-contract.md) to confirm that the failure recurs, changes a decision, is expensive if repeated, and cannot be enforced more reliably by data or code. Supersede the old rule and add a meaningful regression test when deterministic behavior changes.

## Installation boundary

This Skill owns readiness checks and routing, not unsolicited installation or environment repair. If a required capability is absent, report the gap and use an available fallback. Install, authenticate, or modify system configuration only when the user explicitly requests it or when a selected dedicated setup Skill is authorized to do so.

After installation or repair, repeat the real end-to-end acceptance request. Do not mark the route ready from installation output alone.

## Retry and switching

Retry only when the failure is plausibly transient or the next attempt changes a relevant parameter. Cap identical retries. After repeated failure, switch route, reduce scope, or return `blocked` with the exact boundary. Do not allow one blocked source to monopolize the run queue.

Record route events with target field, source class, page type, adapter, route version, evidence context, attempt, result, blocker, yield, precision, cost, and elapsed time. Use the disposition rules above to improve project routing without adding page-specific rules to the main Skill.

When collection volume or failure recovery is material, use the attempt schema and adaptive queue protocol in [collection-throughput-and-recovery.md](collection-throughput-and-recovery.md).

## Security and access

Keep credentials in environment variables, credential stores, or user-controlled sessions. Never place tokens, cookies, authorization codes, or private keys in prompts, logs, reports, fixtures, Skill files, or project playbooks. Use the minimum read permission needed and do not convert read-only research into external writes without separate authorization.

For optional installed Skill routing, read [skill-integrations.md](skill-integrations.md).
