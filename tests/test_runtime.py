from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_script(name: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and result.returncode:
        raise AssertionError(
            f"{name} failed with exit {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observation(
    observation_id: str,
    run_id: str,
    key: str,
    field: str,
    field_kind: str,
    value: object,
    source_id: str,
    strength: str,
    observed_at: str,
    retrieved_at: str,
) -> dict[str, object]:
    return {
        "observation_id": observation_id,
        "run_id": run_id,
        "observation_key": key,
        "object_type": "synthetic_object",
        "object_id": "object-1",
        "field": field,
        "field_kind": field_kind,
        "market": "test",
        "period": "test-period",
        "value": value,
        "unit": None,
        "currency": None,
        "source_id": source_id,
        "evidence_type": "synthetic_evidence",
        "source_strength": strength,
        "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "route_version": "1",
        "parser_version": "1",
        "raw_hash": f"hash-{observation_id}",
    }


def target(
    target_id: str,
    run_id: str,
    goal_id: str,
    planned_at: str,
    coverage_fields: list[str] | None = None,
) -> dict[str, object]:
    return {
        "target_id": target_id,
        "run_id": run_id,
        "goal_id": goal_id,
        "template_id": "synthetic-template",
        "target_type": "synthetic-target",
        "page_type": "synthetic-page",
        "source_class": "official",
        "route_id": "synthetic-route",
        "locator": f"https://example.test/item/{target_id}",
        "original_locator": f"https://example.test/item/{target_id}",
        "dimensions": {"object_id": target_id, "market": "test"},
        "coverage_fields": coverage_fields or [],
        "priority": 100,
        "shard_id": 0,
        "partition_key": "synthetic-template:shard-000",
        "batch_id": "batch-synthetic-template-shard-000",
        "planned_at": planned_at,
        "planner_version": "1.0.0",
    }


class SkillStructureTests(unittest.TestCase):
    def test_required_files_and_local_links(self) -> None:
        required = [
            ROOT / "SKILL.md",
            ROOT / "agents" / "openai.yaml",
            ROOT / "references" / "research-contract.md",
            ROOT / "references" / "evidence-and-coverage.md",
            ROOT / "references" / "tool-routing-and-readiness.md",
            ROOT / "references" / "collection-throughput-and-recovery.md",
            ROOT / "references" / "collection-plan-schema.md",
            ROOT / "references" / "data-contract-and-merge.md",
            ROOT / "references" / "parallel-research-protocol.md",
            ROOT / "references" / "skill-integrations.md",
            ROOT / "references" / "output-contract.md",
        ]
        for path in required:
            self.assertTrue(path.is_file(), path)

        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\n"))
        self.assertIn("name: adaptive-commercial-research", skill_text)

        import re

        for markdown in [ROOT / "SKILL.md", *(ROOT / "references").glob("*.md")]:
            text = markdown.read_text(encoding="utf-8")
            for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
                target = match.group(1)
                if "://" in target or target.startswith("#"):
                    continue
                self.assertTrue((markdown.parent / target).resolve().exists(), f"{markdown}: {target}")


class RuntimeTests(unittest.TestCase):
    def initialize(self, root: Path) -> tuple[Path, dict[str, object]]:
        run_dir = root / "run"
        result = run_script(
            "init_research_run.py",
            "--output",
            run_dir,
            "--goal",
            "Test stable research execution",
            "--decision-use",
            "Verify runtime invariants",
            "--mode",
            "structured-extraction",
            "--depth",
            "standard",
            "--goal-id",
            "goal-test",
            "--run-id",
            "run-current",
            "--cost-unit",
            "credits",
            "--stop",
            "Tests pass",
        )
        return run_dir, json.loads(result.stdout)

    def complete_contract_files(self, run_dir: Path) -> None:
        write_json(
            run_dir / "data_dictionary.json",
            {
                "schema_version": "1.3.0",
                "goal_id": "goal-test",
                "unit_of_analysis": "object x field x market x period",
                "key_fields": ["object_type", "object_id", "field", "market", "period"],
                "fields": {},
            },
        )
        write_json(
            run_dir / "coverage_plan.json",
            {
                "schema_version": "1.3.0",
                "goal_id": "goal-test",
                "dimensions": ["object", "field", "market", "source_class"],
                "required_source_classes": ["official", "independent"],
                "required_cells": ["CELL-001"],
                "required_fields": [],
                "completion_rule": "Every required cell has a terminal state",
            },
        )

    def test_initialization_and_goal_drift_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, initialized = self.initialize(Path(temp))
            self.assertEqual("standard", initialized["depth"])
            self.assertTrue((run_dir / "data_dictionary.json").is_file())
            self.assertTrue((run_dir / "coverage_plan.json").is_file())
            self.assertTrue((run_dir / "collection_attempts.jsonl").is_file())

            self.complete_contract_files(run_dir)
            valid = run_script("validate_research_run.py", run_dir, "--strict")
            self.assertEqual(0, json.loads(valid.stdout)["errors"])

            goal_path = run_dir / "goal_contract.json"
            goal = json.loads(goal_path.read_text(encoding="utf-8"))
            goal["goal"] = "Changed without updating the immutable snapshot"
            write_json(goal_path, goal)
            invalid = run_script("validate_research_run.py", run_dir, check=False)
            self.assertNotEqual(0, invalid.returncode)
            self.assertIn("input_snapshot", invalid.stdout)

    def test_field_contract_rejects_silent_scope_narrowing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run"
            run_script(
                "init_research_run.py",
                "--output",
                run_dir,
                "--goal",
                "Collect contracted listing fields",
                "--decision-use",
                "Verify field parity",
                "--mode",
                "structured-extraction",
                "--depth",
                "standard",
                "--goal-id",
                "goal-fields",
                "--run-id",
                "run-fields",
                "--required-field",
                "price",
                "--optional-field",
                "seller",
                "--excluded-field",
                "orderable",
            )
            write_json(
                run_dir / "data_dictionary.json",
                {
                    "schema_version": "1.3.0",
                    "goal_id": "goal-fields",
                    "unit_of_analysis": "listing x field x market x observation time",
                    "key_fields": ["listing_id", "field", "market", "observed_at"],
                    "fields": {"price": {}, "seller": {}},
                },
            )
            write_json(
                run_dir / "coverage_plan.json",
                {
                    "schema_version": "1.3.0",
                    "goal_id": "goal-fields",
                    "dimensions": ["listing", "field", "market"],
                    "required_source_classes": ["official"],
                    "required_cells": ["CELL-PRICE"],
                    "required_fields": ["price"],
                    "completion_rule": "Every required target-field cell has a terminal state",
                },
            )

            narrowed = run_script("validate_research_run.py", run_dir, check=False)
            self.assertNotEqual(0, narrowed.returncode)
            self.assertIn("extractor_output_fields missing required fields", narrowed.stdout)
            self.assertIn("acceptance_fields missing required fields", narrowed.stdout)

            contract_path = run_dir / "field_contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["extractor_output_fields"] = ["price", "seller"]
            contract["acceptance_fields"] = ["price"]
            write_json(contract_path, contract)
            valid = run_script("validate_research_run.py", run_dir, "--strict")
            self.assertEqual(0, json.loads(valid.stdout)["errors"])

            contract["extractor_output_fields"].append("orderable")
            write_json(contract_path, contract)
            excluded = run_script("validate_research_run.py", run_dir, check=False)
            self.assertNotEqual(0, excluded.returncode)
            self.assertIn("outside the contract", excluded.stdout)

    def test_merge_is_order_invariant_idempotent_and_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batch_a = root / "batch-a.jsonl"
            batch_b = root / "batch-b.jsonl"
            key_dynamic = "object|1|dynamic_metric|test|test-period"
            key_static = "object|1|identity_name|test|all"
            key_stale = "object|1|stale_metric|test|test-period"

            write_jsonl(
                batch_a,
                [
                    observation("OBS-OLD-1", "run-old", key_dynamic, "dynamic_metric", "dynamic", 10, "S-001", "direct_primary", "2026-08-01T00:00:00Z", "2026-08-01T00:00:00Z"),
                    observation("OBS-CUR-3", "run-current", key_dynamic, "dynamic_metric", "dynamic", 13, "S-001", "direct_primary", "2026-08-20T00:00:00Z", "2026-08-20T00:00:00Z"),
                    observation("OBS-CUR-5", "run-current", key_static, "identity_name", "static", "Name B", "S-002", "independent_secondary", "2026-08-25T00:00:00Z", "2026-08-25T00:00:00Z"),
                ],
            )
            write_jsonl(
                batch_b,
                [
                    observation("OBS-CUR-2", "run-current", key_dynamic, "dynamic_metric", "dynamic", 12, "S-002", "independent_secondary", "2026-08-20T00:00:00Z", "2026-08-21T00:00:00Z"),
                    observation("OBS-CUR-4", "run-current", key_static, "identity_name", "static", "Name A", "S-001", "direct_primary", "2026-08-10T00:00:00Z", "2026-08-10T00:00:00Z"),
                    observation("OBS-OLD-6", "run-old", key_stale, "stale_metric", "dynamic", 99, "S-001", "direct_primary", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z"),
                ],
            )

            view_ab, conflicts_ab = root / "view-ab.jsonl", root / "conflicts-ab.jsonl"
            view_ba, conflicts_ba = root / "view-ba.jsonl", root / "conflicts-ba.jsonl"
            common = ("--current-run-id", "run-current")
            run_script("merge_observations.py", batch_a, batch_b, "--output", view_ab, "--conflicts", conflicts_ab, *common)
            run_script("merge_observations.py", batch_b, batch_a, "--output", view_ba, "--conflicts", conflicts_ba, *common)

            self.assertEqual(digest(view_ab), digest(view_ba))
            self.assertEqual(digest(conflicts_ab), digest(conflicts_ba))
            before = (digest(view_ab), digest(conflicts_ab))
            run_script("merge_observations.py", batch_a, batch_b, "--output", view_ab, "--conflicts", conflicts_ab, *common)
            self.assertEqual(before, (digest(view_ab), digest(conflicts_ab)))

            view = [json.loads(line) for line in view_ab.read_text(encoding="utf-8").splitlines()]
            selected = {row["field"]: (row["value"], row["selected_from_observation_id"]) for row in view}
            self.assertEqual((13, "OBS-CUR-3"), selected["dynamic_metric"])
            self.assertEqual(("Name A", "OBS-CUR-4"), selected["identity_name"])
            self.assertNotIn("stale_metric", selected)

            conflicts = [json.loads(line) for line in conflicts_ab.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(2, sum(row["conflict_type"] == "competing_values" for row in conflicts))
            self.assertEqual(1, sum(row["conflict_type"] == "stale_only" for row in conflicts))

    def test_collection_summary_tracks_funnel_and_retry_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, _ = self.initialize(Path(temp))

            def attempt(
                attempt_id: str,
                target_id: str,
                stage: str,
                status: str,
                attempt_no: int = 1,
                retry_of: str | None = None,
                valid: int = 0,
            ) -> dict[str, object]:
                row: dict[str, object] = {
                    "attempt_id": attempt_id,
                    "run_id": "run-current",
                    "batch_id": "batch-1",
                    "target_id": target_id,
                    "stage": stage,
                    "adapter": "synthetic-adapter",
                    "route_version": "1",
                    "attempt_no": attempt_no,
                    "status": status,
                    "started_at": f"2026-08-01T00:00:{attempt_no:02d}Z",
                    "finished_at": f"2026-08-01T00:01:{attempt_no:02d}Z",
                    "valid_record_count": valid,
                    "new_record_count": valid,
                    "elapsed_ms": 100,
                    "cost": 0.01,
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "bytes_received": 100,
                    "executor_class": "local-test",
                    "route_id": "synthetic-route",
                }
                if status not in {"success", "partial", "skipped_duplicate"}:
                    row["error_category"] = status
                if retry_of:
                    row["retry_of_attempt_id"] = retry_of
                return row

            attempts = [
                attempt("A-01", "T-1", "discover", "success"),
                attempt("A-02", "T-1", "fetch", "timeout"),
                attempt("A-03", "T-1", "fetch", "success", 2, "A-02"),
                attempt("A-04", "T-1", "parse", "success"),
                attempt("A-05", "T-1", "extract", "success", valid=2),
                attempt("A-06", "T-2", "discover", "success"),
                attempt("A-07", "T-2", "fetch", "rate_limited"),
                attempt("A-08", "T-3", "discover", "success"),
                attempt("A-09", "T-3", "fetch", "success"),
                attempt("A-10", "T-3", "parse", "success"),
                attempt("A-11", "T-3", "extract", "success"),
                attempt("A-12", "T-4", "discover", "success"),
                attempt("A-13", "T-4", "fetch", "skipped_duplicate"),
            ]
            manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
            write_jsonl(
                run_dir / "target_queue.jsonl",
                [target(f"T-{number}", "run-current", "goal-test", manifest["created_at"]) for number in range(1, 5)],
            )
            write_jsonl(run_dir / "collection_attempts.jsonl", attempts)
            self.complete_contract_files(run_dir)
            validated = run_script("validate_research_run.py", run_dir, "--strict")
            self.assertEqual(13, json.loads(validated.stdout)["collection_attempts"])
            write_jsonl(
                run_dir / "observations.jsonl",
                [
                    {"observation_id": "O-1", "observation_key": "K-1"},
                    {"observation_id": "O-2", "observation_key": "K-2"},
                ],
            )

            result = run_script("summarize_collection_run.py", run_dir)
            summary = json.loads(result.stdout)
            self.assertEqual(13, summary["total_attempts"])
            self.assertEqual(4, summary["unique_targets"])
            self.assertEqual(0.5, summary["pipeline"]["fetch_success_rate"])
            self.assertEqual(0.5, summary["pipeline"]["valid_target_rate"])
            self.assertEqual(0.25, summary["pipeline"]["end_to_end_valid_rate"])
            self.assertEqual(1, summary["pipeline"]["duplicate_targets"])
            self.assertEqual(1, summary["pipeline"]["unresolved_targets"])
            self.assertEqual(1.0, summary["recovery"]["retry_recovery_rate"])
            self.assertEqual(2, summary["observations"]["unique_observation_keys"])
            self.assertAlmostEqual(0.13, summary["efficiency"]["cost"])
            self.assertAlmostEqual(0.065, summary["efficiency"]["cost_per_new_record"])
            self.assertEqual(1, len(summary["batches_marginal_yield"]))
            self.assertIn("synthetic-route", summary["routes"])
            self.assertIn("local-test", summary["executors"])

            first = run_dir / "collection-metrics-a.json"
            second = run_dir / "collection-metrics-b.json"
            run_script("summarize_collection_run.py", run_dir, "--output", first)
            run_script("summarize_collection_run.py", run_dir, "--output", second)
            self.assertEqual(digest(first), digest(second))

    def test_planner_raw_cache_and_pilot_gate_form_a_closed_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            run_script(
                "init_research_run.py",
                "--output",
                run_dir,
                "--goal",
                "Collect planned target fields",
                "--decision-use",
                "Verify collection control plane",
                "--mode",
                "structured-extraction",
                "--depth",
                "standard",
                "--goal-id",
                "goal-plan",
                "--run-id",
                "run-plan",
                "--cost-unit",
                "credits",
                "--required-field",
                "price",
                "--optional-field",
                "seller",
                "--stop",
                "Every planned target-field cell is terminal",
            )
            write_json(
                run_dir / "data_dictionary.json",
                {
                    "schema_version": "1.3.0",
                    "goal_id": "goal-plan",
                    "unit_of_analysis": "listing x field x market x observation time",
                    "key_fields": ["listing_id", "field", "market", "observed_at"],
                    "fields": {"price": {}, "seller": {}},
                },
            )
            write_json(
                run_dir / "coverage_plan.json",
                {
                    "schema_version": "1.3.0",
                    "goal_id": "goal-plan",
                    "dimensions": ["target", "field", "market"],
                    "required_source_classes": ["official"],
                    "required_cells": [],
                    "required_fields": ["price"],
                    "completion_rule": "Every planned target-field cell has a terminal state",
                },
            )
            field_contract_path = run_dir / "field_contract.json"
            field_contract = json.loads(field_contract_path.read_text(encoding="utf-8"))
            field_contract["extractor_output_fields"] = ["price", "seller"]
            field_contract["acceptance_fields"] = ["price"]
            write_json(field_contract_path, field_contract)
            spec_path = root / "plan.json"
            write_json(
                spec_path,
                {
                    "planned_at": "2026-09-01T00:00:00Z",
                    "shard_count": 3,
                    "axes": {
                        "object_id": ["object-b", "object-a"],
                        "market": ["BE", "NL"],
                        "alias": ["desk chair", "chair"],
                    },
                    "templates": [
                        {
                            "template_id": "site-search",
                            "vary_by": ["object_id", "market", "alias"],
                            "identity_axes": ["object_id", "market", "alias"],
                            "url_encode_axes": ["alias"],
                            "target_type": "search-results",
                            "page_type": "search",
                            "source_class": "official",
                            "route_id": "public-search-v1",
                            "locator_template": "https://example.test/{market}/search?q={alias}&utm_source=test",
                            "coverage_fields": ["price", "seller"],
                        }
                    ],
                    "exclude": [
                        {
                            "template_id": "site-search",
                            "object_id": "object-b",
                            "market": "BE",
                            "alias": "desk chair",
                        }
                    ],
                },
            )
            planned = run_script("plan_collection.py", run_dir, "--spec", spec_path)
            planned_summary = json.loads(planned.stdout)
            self.assertEqual(7, planned_summary["generated_targets"])
            self.assertEqual(14, planned_summary["generated_coverage_cells"])
            queue_hash = digest(run_dir / "target_queue.jsonl")
            coverage_hash = digest(run_dir / "coverage.jsonl")
            planned_again = run_script("plan_collection.py", run_dir, "--spec", spec_path)
            self.assertEqual(0, json.loads(planned_again.stdout)["new_targets"])
            self.assertEqual(queue_hash, digest(run_dir / "target_queue.jsonl"))
            self.assertEqual(coverage_hash, digest(run_dir / "coverage.jsonl"))

            targets = [json.loads(line) for line in (run_dir / "target_queue.jsonl").read_text(encoding="utf-8").splitlines()]
            pilot_target = targets[0]
            source = {
                "source_id": "S-001",
                "source_type": "official_page",
                "strength_grade": "direct_primary",
                "access_class": "public",
                "locator": pilot_target["locator"],
                "retrieved_at": "2026-09-01T00:01:00Z",
                "state": "ready",
            }
            write_jsonl(run_dir / "sources.jsonl", [source])
            attempt_row = {
                "attempt_id": "A-PILOT-1",
                "run_id": "run-plan",
                "batch_id": pilot_target["batch_id"],
                "target_id": pilot_target["target_id"],
                "stage": "extract",
                "adapter": "synthetic-adapter",
                "route_id": "public-search-v1",
                "route_version": "1",
                "attempt_no": 1,
                "status": "success",
                "started_at": "2026-09-01T00:00:30Z",
                "finished_at": "2026-09-01T00:01:00Z",
                "valid_record_count": 1,
                "new_record_count": 1,
                "elapsed_ms": 30000,
                "cost": 0.02,
            }
            write_jsonl(run_dir / "collection_attempts.jsonl", [attempt_row])
            payload = root / "payload.html"
            payload.write_text("<html><body>price evidence</body></html>", encoding="utf-8")
            registered = run_script(
                "register_raw_artifact.py",
                run_dir,
                payload,
                "--target-id",
                pilot_target["target_id"],
                "--attempt-id",
                "A-PILOT-1",
                "--source-id",
                "S-001",
                "--locator",
                pilot_target["locator"],
                "--retrieved-at",
                "2026-09-01T00:01:00Z",
                "--route-version",
                "1",
            )
            raw = json.loads(registered.stdout)
            registered_again = run_script(
                "register_raw_artifact.py",
                run_dir,
                payload,
                "--target-id",
                pilot_target["target_id"],
                "--attempt-id",
                "A-PILOT-1",
                "--source-id",
                "S-001",
                "--locator",
                pilot_target["locator"],
                "--retrieved-at",
                "2026-09-01T00:01:00Z",
                "--route-version",
                "1",
            )
            self.assertFalse(json.loads(registered_again.stdout)["registry_appended"])
            self.assertEqual(1, len((run_dir / "raw_artifacts.jsonl").read_text(encoding="utf-8").splitlines()))

            coverage_rows = [json.loads(line) for line in (run_dir / "coverage.jsonl").read_text(encoding="utf-8").splitlines()]
            for field, state in (("price", "checked_hit"), ("seller", "checked_no_confirmation")):
                initial = next(
                    row for row in coverage_rows
                    if row["target_id"] == pilot_target["target_id"] and row["field_scope"] == field
                )
                coverage_rows.append(
                    {
                        **initial,
                        "attempt_id": f"COV-{field}",
                        "state": state,
                        "retrieved_at": "2026-09-01T00:01:00Z",
                        "source_ids": ["S-001"],
                    }
                )
            write_jsonl(run_dir / "coverage.jsonl", coverage_rows)
            price_observation = observation(
                "OBS-PRICE-1",
                "run-plan",
                f"listing|{pilot_target['target_id']}|price|test|2026-09-01",
                "price",
                "dynamic",
                19.99,
                "S-001",
                "direct_primary",
                "2026-09-01T00:01:00Z",
                "2026-09-01T00:01:00Z",
            )
            price_observation["target_id"] = pilot_target["target_id"]
            price_observation["raw_hash"] = raw["sha256"]
            write_jsonl(run_dir / "observations.jsonl", [price_observation])

            pilot = run_script(
                "validate_pilot_output.py",
                run_dir,
                "--target-id",
                pilot_target["target_id"],
                "--strict",
            )
            pilot_summary = json.loads(pilot.stdout)
            self.assertTrue(pilot_summary["passed"])
            self.assertEqual(1.0, pilot_summary["target_field_terminalization_rate"])
            validated = run_script("validate_research_run.py", run_dir, "--strict", "--verify-raw-files")
            self.assertEqual(0, json.loads(validated.stdout)["errors"])


if __name__ == "__main__":
    unittest.main()
