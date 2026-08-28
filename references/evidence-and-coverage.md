# Evidence and Coverage

## Declare the source universe

Use source families rather than a fixed website list. Include only families relevant to the target fields:

1. user-provided internal records, historical reports, and connected workspaces
2. official company, contractual, legal-notice, policy, and owned-domain material
3. filings, regulators, registries, tax, trademark, domain, court, and recall material
4. channel-native search, store, seller, brand, listing, and transaction-path evidence
5. product documents, manuals, compliance labels, responsible-party, logistics, import, and warehouse clues
6. reputable industry databases, measurement providers, trade media, and structured datasets
7. community, social, forum, review, and other weak-signal discovery sources
8. search indexes, archives, sitemaps, and aggregators used as locators rather than final proof

Internal and public sources may be used together, but label access class and never expose private evidence in a public-facing deliverable without authorization.

## Keep state dimensions separate

### Coverage state

- `checked_hit`: the cell was checked and produced target-relevant evidence
- `checked_no_confirmation`: checked, but no target-relevant confirmation was found
- `blocked`: access or technical conditions prevented a reliable check
- `unchecked`: not yet attempted

### Evidence type

Use the most specific applicable type, such as discovery trace, content or product hit, brand page, official store, seller identity, contractual or legal record, compliance or responsible-party record, registry or filing, internal record, or metric observation.

### Source strength

- `direct_primary`: direct legal, regulatory, contractual, registry, filing, platform-native identity, or user-authorized primary record
- `official_secondary`: official narrative or owned material that is relevant but not the controlling record
- `independent_secondary`: reputable independent reporting or structured data with a clear method
- `weak_signal`: community, snippet, aggregator, recommendation card, or otherwise indirect clue
- `unknown`: provenance or method is insufficiently clear

Source strength is not completeness, confidence, or currentness. Store those separately.

## Coverage matrix

Choose dimensions that match the mode. A common matrix is:

`object or alias x market or jurisdiction x source family or channel type x target field x period`

Each required cell must have exactly one current coverage state, while historical attempts remain append-only. Record the query or route, retrieval time, source references, result type, blocker when applicable, and next useful route.

Do not list only successful sources. A coverage claim is trustworthy only when checked, no-confirmation, blocked, and unchecked boundaries are visible.

## Conservative identity and relationship mapping

Do not collapse adjacent labels. Keep organization, legal entity, seller, store display name, brand, trademark owner, importer, responsible party, logistics node, platform, site, product, listing, and variant as separate objects.

A relationship becomes confirmed only when at least one strong direct source closes it or when multiple independent sources jointly support the same precise relationship without material contradiction. Product adjacency, shared design, search ranking, recommendation cards, traffic overlap, or similar names are clues, not ownership proof.

## Claim-to-source mapping

Every material conclusion should have a stable claim ID and link to:

- supporting source IDs
- counterevidence source IDs
- inference type, if the conclusion is not directly stated
- confidence and currentness
- associated gap or blocker IDs

Preserve conflicting values. Explain which value is used for the current decision and why; do not erase alternatives from the ledger.

## Important semantic boundaries

- Technical failure or empty content is not absence.
- Numeric zero is a value; missing, unavailable, not applicable, and not checked are different states.
- Traffic estimates are not revenue, orders, profit, or deduplicated users.
- Ratings, rating counts, written-review counts, seller-review counts, and shared variant pools are different measures.
- A country domain or localized page does not alone prove local contracting, inventory, or sales.
- A search hit, product listing, brand page, official store, seller identity, and legal or responsible-party record are different evidence types.

## Completeness test

Do not say `complete` merely because many pages were collected. State:

- the declared source universe and excluded families
- coverage counts by state
- which aliases, languages, markets, and periods were used
- whether critical claims meet the evidence threshold
- remaining blockers and conflicts
- why further high-value searches are unlikely to change the decision, or which resource boundary ended the run
