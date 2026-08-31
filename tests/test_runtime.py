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
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


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


class SkillStructureTests(unittest.TestCase):
    def test_required_files_and_local_links(self) -> None:
        required = [
            ROOT / "SKILL.md",
            ROOT / "agents" / "openai.yaml",
            ROOT / "references" / "research-contract.md",
            ROOT / "references" / "evidence-and-coverage.md",
            ROOT / "references" / "tool-routing-and-readiness.md",
            ROOT / "references" / "collection-throughput-and-recovery.md",
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
            "--stop",
            "Tests pass",
        )
        return run_dir, json.loads(result.stdout)

    def complete_contract_files(self, run_dir: Path) -> None:
        write_json(
            run_dir / "data_dictionary.json",
            {
                "schema_version": "1.1.0",
                "goal_id": "goal-test",
                "unit_of_analysis": "object x field x market x period",
                "key_fields": ["object_type", "object_id", "field", "market", "period"],
                "fields": {},
            },
        )
        write_json(
            run_dir / "coverage_plan.json",
            {
                "schema_version": "1.1.0",
                "goal_id": "goal-test",
                "dimensions": ["object", "field", "market", "source_class"],
                "required_source_classes": ["official", "independent"],
                "required_cells": ["CELL-001"],
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

            first = run_dir / "collection-metrics-a.json"
            second = run_dir / "collection-metrics-b.json"
            run_script("summarize_collection_run.py", run_dir, "--output", first)
            run_script("summarize_collection_run.py", run_dir, "--output", second)
            self.assertEqual(digest(first), digest(second))


if __name__ == "__main__":
    unittest.main()
