# Collection Plan Schema

Use this reference when `plan_collection.py` should expand a bounded matrix into canonical targets. Keep source-specific values in the project plan file, not in the portable Skill.

## Plan object

```json
{
  "planned_at": "2026-09-01T00:00:00Z",
  "shard_count": 4,
  "axes": {
    "object_id": ["object-a", "object-b"],
    "market": ["market-1", "market-2"],
    "alias": ["local term", "alternate term"]
  },
  "templates": [
    {
      "template_id": "site-search",
      "vary_by": ["object_id", "market", "alias"],
      "identity_axes": ["object_id", "market", "alias"],
      "url_encode_axes": ["alias"],
      "target_type": "search-results",
      "page_type": "search",
      "source_class": "channel-native",
      "route_id": "public-search-v1",
      "route_candidates": ["public-search-v1", "rendered-search-v1"],
      "frontier_ids": ["FRONTIER-example"],
      "locator_template": "https://example.test/{market}/search?q={alias}",
      "coverage_fields": ["title", "canonical_url"],
      "priority": 100
    }
  ],
  "exclude": [
    {"template_id": "site-search", "object_id": "object-b", "market": "market-2"}
  ]
}
```

## Semantics

`axes` values must be scalar and non-empty. The planner sorts values deterministically before taking the Cartesian product. Each template chooses axes with `vary_by`; `fixed_dimensions` may add constants.

`locator_template` uses Python-style named placeholders. Put dimensions that need query-string escaping in `url_encode_axes`. The planner lowercases URL scheme and host, removes fragments and known tracking parameters, sorts query parameters, and rejects embedded credentials. It does not erase locale, seller, variant, language, or other dimensions unless the plan explicitly removes them from the locator and identity.

`identity_axes` controls which dimensions participate in the stable target ID. Default to every `vary_by` axis. Remove an axis only when it is demonstrably non-semantic for target identity; otherwise unrelated observations may collapse.

`coverage_fields` must be required or optional fields from `field_contract.json`. Excluded or undeclared fields are rejected before output. An exclusion is a partial exact match against `template_id` and dimensions.

`route_id` is the initial route. `route_candidates` lists distinct current-run routes that may retrieve the same immutable target; the initial route must be included. For schema `1.5.0` and later, route choice is deliberately excluded from `target_id`, so retries and switches keep the same target lineage. `frontier_ids` links the target to the discovery entrypoints that exposed or bounded it; every referenced frontier must exist in `discovery_frontier.jsonl`.

`priority` is a static business priority, not a complete scheduling score. The adaptive selector combines it with unresolved required fields, source-family fairness, current-run route performance, retry state, and active leases. `shard_count` must remain fixed while active leases exist. Stable target hashing reproduces the same shard for the same target and shard count.

## Outputs and reruns

The planner writes new immutable rows to `target_queue.jsonl`, adds initial `unchecked` rows to `coverage.jsonl`, and updates the deterministic required-cell set in `coverage_plan.json`. Re-running the same plan is idempotent. A conflicting definition for an existing target is rejected rather than overwritten.

Use a new plan revision when routes, semantic dimensions, or shard count change. Reconcile completed targets and active leases before issuing work from that revision.
