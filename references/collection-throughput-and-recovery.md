# Collection Throughput and Recovery

Use this protocol when the result depends on collecting many records, pages, listings, documents, or source traces, or when access failures would materially reduce coverage. Optimize for unique valid records per unit of time, not raw requests or downloaded pages.

## Separate discovery from extraction

Use a two-pass pipeline:

1. **Wide, cheap discovery:** expand aliases, languages, markets, source families, sitemaps, feeds, indexes, site search, listing pages, and known identifiers. Produce canonical target IDs before expensive retrieval.
2. **Narrow, expensive extraction:** prioritize targets by expected target-field yield, source strength, freshness, and coverage gap. Use rendering, browser interaction, OCR, or costly APIs only for candidates that need them.

Do not send every discovered URL directly to the most expensive route. Canonicalize URLs, strip tracking parameters, resolve known aliases, and deduplicate stable platform or listing IDs first. Use content hashes after retrieval to suppress mirrors and repeated templates while retaining provenance.

## Extract once, decide per field

Before a costly route is scaled, map which required and optional fields the same response, rendered region, export row, or authorized session can expose. If one successful retrieval contains several in-scope fields, parse them in the same pass when doing so is reliable and materially cheaper than revisiting the target.

Each field still needs its own observation, evidence rule, missing state, and acceptance test. A price does not establish stock, a purchase control does not establish every variant's availability, and a seller label does not establish the contracting entity. Do not convert nearby text into a field merely because it was cheap to collect.

Preserve the raw payload, relevant excerpt or selector, and parser version so a missing parser branch can be repaired by reprocessing stored evidence before any refetch. If the original evidence did not contain the field or did not preserve enough context to interpret it safely, classify that field as unobserved rather than inferring it.

## Build a coverage-expanding queue

Partition the queue by source family, domain, page type, market or locale, and retrieval route. Give every target a stable `target_id`; give every bounded unit of work a `batch_id`.

Prioritize in this order unless the goal contract says otherwise:

1. uncovered required cells and high-value aliases
2. likely primary or channel-native sources
3. targets with high pilot yield and low marginal cost
4. recovery work that changes route or failure condition
5. weaker discovery sources and low-yield long-tail pages

Use pagination, sitemaps, site maps, category pages, feeds, structured endpoints, exports, and identifier enumeration to increase breadth. Search-result pages are discovery surfaces, not proof that all underlying records were captured.

Track marginal yield by route and source family. Expand queries from missing coverage cells and from retrieved-but-unused aliases, identifiers, entities, and page types. Stop expanding a route when repeated batches add few unique valid records and another route has higher expected yield.

## Pilot and adaptive batch sizing

Pilot each materially different domain and page type with a small, diverse batch. Measure:

- unique targets discovered
- fetch and parse success by stage
- valid and new records
- duplicate and empty-content rates
- latency, cost, rate limits, challenges, and blocker classes

Set concurrency per host and adapter, not globally. Increase batch size or concurrency gradually while success and latency remain stable. On rate limits, rising timeouts, challenge pages, or partial-result loss, honor server guidance, reduce concurrency, shrink batches, and resume from the last durable checkpoint. Do not use a fixed concurrency value as a universal rule.

Persist each completed page, cursor, or bounded batch before requesting the next one. A restarted run must be able to identify completed targets, pending targets, the last cursor, and retry history without replaying successful work.

## Failure taxonomy and route changes

Classify failure before retrying. An identical retry without a changed condition is usually waste.

| Failure | First response | Useful escalation |
|---|---|---|
| transient network or server error | bounded retry with jittered backoff | alternate endpoint or later batch |
| rate limit | honor retry guidance; reduce host concurrency | slower queue, authenticated API, export, or later window |
| login, permission, or access denial | verify authorized access | user-controlled session, official API/export, or `blocked` |
| challenge or bot defense | stop blind retries | authorized browser route, alternate primary source, or `blocked` |
| empty or incomplete dynamic content | verify response and page type | rendered/browser retrieval or structured endpoint |
| parser or schema failure | preserve raw payload | reparse locally with a revised parser; do not refetch first |
| invalid or moved locator | canonicalize and rediscover | replacement locator, sitemap, archive, or terminal invalid target |
| geography or locale mismatch | record the boundary | permitted locale route or explicit coverage gap |

Cap retries by failure class. Route switches must preserve the same `target_id`, link to the prior attempt, and record what changed. Put terminal failures in a dead-letter or blocked queue with their exact reason so one source cannot monopolize workers.

Keep adapter or wrapper status separate from content classification. If an outer tool reports an error while preserving parseable target evidence, retain both facts and apply an explicit, versioned precedence rule. Repair classification in deterministic parser code with a regression case; append the corrected attempt or observation rather than deleting the earlier record.

## Durable attempt ledger

Write one append-only `collection_attempts.jsonl` row for every target-stage attempt. The grain is one target, one stage, one adapter call, and one attempt number. Required fields are defined in [data-contract-and-merge.md](data-contract-and-merge.md).

Log attempts before synthesizing success metrics. Never reconstruct failures only from prose or tool output. Do not overwrite a failed attempt when a later route succeeds; recovery rate depends on retaining both.

## Throughput and success gates

Use a funnel instead of a single success number:

`unique discovered targets -> fetched targets -> parsed targets -> extracted targets -> targets with valid records -> unique merged observations`

Report at least:

- stage-level target success rates
- end-to-end valid-target rate
- unique observation keys and new-record yield
- retry recovery rate
- final unresolved targets by failure class
- duplicate, empty, blocked, and rate-limited shares
- route-level yield and success rate
- required-field observations and completion by field
- target terminalization separately from required-field completion

Raw request count, total downloaded pages, terminal target count, and successful HTTP status alone do not demonstrate useful collection. Use `../scripts/summarize_collection_run.py` to derive comparable metrics from the attempt and observation ledgers.

## Stop and switch rules

Continue a route while it adds unique valid records or closes required coverage cells at an acceptable marginal cost. Switch when another ready route has better observed yield or when the present failure class requires a different capability. Stop when the declared coverage rule is met, marginal unique yield stays below the run's threshold across repeated batches, or an explicit resource or access boundary is reached.

Never reinterpret a blocked route as absence. Preserve pending and blocked targets so a later authorized run can resume them.
