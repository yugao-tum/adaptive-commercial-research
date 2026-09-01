# Optional Skill Integrations

These are conditional routes, not permanent co-owners. Before invoking another Skill, confirm it is available in the current environment and read its complete `SKILL.md`. If unavailable, continue with the closest safe capability and state the limitation. Do not copy another Skill's instructions into this Skill.

Apply the external-executor dispatch gate in [tool-routing-and-readiness.md](tool-routing-and-readiness.md). Once a support Skill is selected for a material capability gap, invoke it on a bounded real task and record its result; merely reading its instructions or listing it as an option does not count as use. When it is not selected, retain the explicit reason instead of repeatedly proposing the same unused integration.

## Routing and precedence

| Skill | Invoke when | Relationship to this Skill |
|---|---|---|
| `$agent-reach` | The task requires internet discovery or supported social, video, community, career, developer, web, or finance retrieval | Retrieval support. This Skill retains goal, evidence, coverage, merge, and output ownership. Run the required readiness check and record unavailable channels. |
| `$scrapling-official` | Known web targets require repeatable extraction, JavaScript rendering, adaptive parsing, anti-bot-aware retrieval, or a resumable multi-page spider | Web collection support. Start with the lightest route, escalate only for a classified failure, respect access rules, and return attempt, checkpoint, and record-yield data to this Skill's ledgers. Installation or environment repair still requires the authorization defined in the tool-readiness policy. |
| `$data-analytics:gather-business-context` | Internal workspaces, reports, definitions, decisions, or connected business sources are needed to frame the research | Context support. Return compact attributable context; do not let internal narrative override stronger controlling records. |
| `$data-analytics:analyze-data-quality` | Structured datasets, extracts, dashboards, joins, metrics, or conflicting definitions must be assessed for trustworthiness | Quality support. Preserve the declared grain and feed findings into this Skill's claim and gap structure. |
| `$public-equity-investing:public-equity-investing` | The real decision concerns a listed security, earnings, valuation, portfolio, catalyst, or investor thesis | Domain handoff. The investment Skill becomes lead; this Skill may support source coverage or structured collection. |
| `$life-science-research:research-router-skill` | The real task is scientific, biomedical, clinical, chemical, genetic, or translational research | Domain handoff. Do not force a scientific task into the commercial object model. |
| `$skill-creator` | The user asks to create, revise, package, or validate this or another Skill | Maintenance only. Never invoke it during an ordinary research run. |

The historical evidence-gated platform sweep is absorbed here as evidence and coverage behavior rather than treated as a runtime dependency.

## Single-lead rule

At most one Skill owns the final decision workflow. Support Skills receive bounded inputs and return evidence, context, data-quality findings, or artifacts. The lead Skill owns clarifying questions, depth, scope changes, conflict resolution, and the final deliverable.

Do not invoke a support Skill merely because it exists. Invoke it only when its specialized behavior changes reliability, coverage, or efficiency enough to justify the additional coordination.
