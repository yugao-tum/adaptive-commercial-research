# Output Contract

Substantive answers must be navigable. Organize around the user's decision, not around tools, agents, or search chronology.

## Extended structure

Start with a one-line research status strip:

`RUN | mode | depth | scope | as-of | completion posture`

Then use these stable sections:

### 0. Core conclusions

Give the direct answer first. Assign stable IDs only to material conclusions: `C-01`, `C-02`, and so on. State status and confidence in plain language.

### 1. Conclusion map

Use a table for repeated fields:

| Claim | Working conclusion | Support | Counterevidence | Confidence | Currentness |
|---|---|---|---|---|---|

Evidence references use `S-001` style IDs. A conclusion inferred from multiple sources must say that it is an inference.

### 2. Coverage and evidence boundary

Summarize the declared source universe and coverage counts by `checked_hit`, `checked_no_confirmation`, `blocked`, and `unchecked`. Show the detailed matrix only when its repeated dimensions help the user; otherwise place it in an appendix or machine artifact.

### 3. Conflicts, gaps, and blockers

Use stable IDs:

- `X-01` for material conflicting evidence
- `G-01` for an unresolved evidence or field gap
- `B-01` for a technical or authorization blocker

Explain whether resolving the item could change the decision. Do not mix these states with business absence.

### 4. Recommended actions

Use `A-01` identifiers and prioritize only actions that could materially improve coverage, confidence, currentness, or the user's decision. Do not recommend more searching by default.

### Appendix

Put long source lists, queries, route events, tool diagnostics, extraction details, schemas, and raw coverage ledgers here. Preserve source IDs so the main answer can be traced without repeating URLs.

## Compact structure

For a narrow result, use only:

1. direct conclusion
2. essential evidence
3. boundary, uncertainty, or next decision

Do not force IDs or a full report when there are fewer than several material claims and no complex coverage boundary.

## Formatting rules

1. Use headings for layers, tables for repeated mappings, and short paragraphs for reasoning.
2. Bullets are local lists inside a named section, not the architecture of the whole answer.
3. Every material detail must belong to a conclusion, coverage cell, conflict, gap, blocker, or action. Remove or append orphan details.
4. Keep process narration, tool names, request counts, and retry logs out of the main body unless they change evidence reliability.
5. Put conclusions before caveats, but keep the caveats adjacent to the conclusion they qualify.
6. Keep evidence state, confidence, and currentness separate. Do not compress them into one badge.
7. Preserve the user's existing artifact structure unless they requested redesign; when integration is needed, keep the original and create one clean consolidated artifact.

## Navigation gate

Before delivery, verify that a reader can locate within roughly 30 seconds:

- the direct answer
- the exact research boundary
- the strongest evidence for each major conclusion
- the largest unresolved issue or blocker
- the next action that could change the decision

Also verify that every claim resolves to sources, every gap resolves to a coverage cell or missing field, and no section is merely a dump of disconnected bullets.
