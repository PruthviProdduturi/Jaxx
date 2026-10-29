"""Deterministic replay, validation, provenance and no-adoption regression coverage."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "improve.py"
SPEC = importlib.util.spec_from_file_location("improve", SCRIPT)
improve = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(improve)
FIXTURES = ROOT / "tests" / "improvement"


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            name: json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
            for name in improve.INPUTS
        }

    def evaluate(self):
        return improve.evaluate(*(self.data[name] for name in improve.INPUTS))

    def test_synthetic_comparison_is_review_only(self):
        report = self.evaluate()
        self.assertEqual(report["status"], "review-required")
        self.assertFalse(report["adopted"])
        self.assertEqual(report["scores"], {"baseline": 3, "candidate": 5, "total": 5})
        self.assertEqual(report["toolCalls"], {"baseline": 10, "candidate": 8})
        self.assertTrue(all(report["gates"].values()))

    def test_only_improvement_supported_lessons_are_composed(self):
        report = self.evaluate()
        report["inputSha256"] = {}
        packet = improve.compose(report, self.data["proposal"])
        self.assertEqual(len(packet["lessonDrafts"]), 2)
        self.assertEqual(packet["unsupportedLessonCount"], 1)
        self.assertFalse(packet["adopted"])
        self.assertTrue(all(row["status"] == "draft" for row in packet["lessonDrafts"]))

    def test_multi_case_lesson_requires_every_case_to_improve(self):
        self.data["proposal"]["lessons"][0]["caseIds"].append("quiet-cycle")
        report = self.evaluate()
        report["inputSha256"] = {}
        packet = improve.compose(report, self.data["proposal"])
        self.assertEqual(len(packet["lessonDrafts"]), 1)

    def test_safety_regression_cannot_hide_behind_net_gain(self):
        self.data["candidate"]["results"][2]["decision"] = "post"
        report = self.evaluate()
        self.assertEqual(report["scores"]["candidate"], 4)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["gates"]["allSafetyCasesPass"])
        self.assertFalse(report["gates"]["noCaseRegressions"])
        with self.assertRaises(ValueError):
            improve.compose(report, self.data["proposal"])

    def test_task_regression_also_blocks(self):
        self.data["candidate"]["results"][-1]["decision"] = "post"
        self.assertEqual(self.evaluate()["status"], "blocked")

    def test_missing_evidence_and_extra_claims_fail(self):
        for field, value in (("evidence", ["receipt"]),
                             ("claims", ["persisted", "accepted"])):
            with self.subTest(field=field):
                original = self.data["candidate"]["results"][0][field]
                self.data["candidate"]["results"][0][field] = value
                self.assertEqual(self.evaluate()["status"], "blocked")
                self.data["candidate"]["results"][0][field] = original

    def test_marker_order_does_not_change_score(self):
        self.data["candidate"]["results"][0]["evidence"].reverse()
        self.assertEqual(self.evaluate()["status"], "review-required")

    def test_budgets_are_total_and_inclusive(self):
        limits = self.data["cases"]["limits"]
        limits.update(maxToolCalls=8, maxDurationMs=5000)
        self.assertEqual(self.evaluate()["status"], "review-required")
        for field, value in (("maxToolCalls", 7), ("maxDurationMs", 4999)):
            with self.subTest(field=field):
                previous = limits[field]
                limits[field] = value
                self.assertEqual(self.evaluate()["status"], "blocked")
                limits[field] = previous

    def test_correctness_gain_cannot_buy_extra_tool_calls(self):
        self.data["candidate"]["results"][0]["toolCalls"] = 6
        self.assertEqual(self.evaluate()["status"], "blocked")

    def test_no_gain_blocks_even_when_everything_passes(self):
        self.data["baseline"]["results"] = copy.deepcopy(self.data["candidate"]["results"])
        self.assertEqual(self.evaluate()["status"], "blocked")
        self.data["candidate"]["results"][0]["durationMs"] = 1
        self.assertEqual(self.evaluate()["status"], "blocked")

    def test_fewer_calls_on_passing_cases_is_a_gain(self):
        self.data["baseline"]["results"] = copy.deepcopy(self.data["candidate"]["results"])
        self.data["baseline"]["results"][0]["toolCalls"] += 1
        self.assertEqual(self.evaluate()["status"], "review-required")

    def test_uneditable_surfaces_are_rejected(self):
        for surface in ("guardrails", "system-prompt", "config", "hooks",
                        "plugins", "../config", "authority", []):
            with self.subTest(surface=surface):
                self.data["proposal"]["changes"][0]["surface"] = surface
                with self.assertRaises(ValueError):
                    self.evaluate()

    def test_unknown_and_empty_lesson_references_are_rejected(self):
        for references in ([], ["missing"], ["quiet-cycle", "quiet-cycle"]):
            self.data["proposal"]["lessons"][0]["caseIds"] = references
            with self.assertRaises(ValueError):
                self.evaluate()

    def test_unchanged_or_empty_proposals_are_rejected(self):
        self.data["proposal"]["changes"][0]["after"] = self.data["proposal"]["changes"][0]["before"]
        with self.assertRaises(ValueError):
            self.evaluate()
        self.data["proposal"]["changes"] = []
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_duplicate_missing_and_extra_results_are_rejected(self):
        original = copy.deepcopy(self.data["candidate"]["results"])
        for rows in (original + [original[0]], original[:-1],
                     original + [dict(original[0], id="extra")], []):
            self.data["candidate"]["results"] = rows
            with self.assertRaises(ValueError):
                self.evaluate()

    def test_suite_and_proposal_ids_must_match(self):
        for name in ("suiteId", "proposalId"):
            previous = self.data["candidate"][name]
            self.data["candidate"][name] = "wrong"
            with self.assertRaises(ValueError):
                self.evaluate()
            self.data["candidate"][name] = previous

    def test_baseline_requires_baseline_id(self):
        self.data["baseline"]["proposalId"] = "receipt-first"
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_both_task_and_safety_cases_are_required(self):
        for kind in ("task", "safety"):
            for case in self.data["cases"]["cases"]:
                case["kind"] = kind
            with self.assertRaises(ValueError):
                self.evaluate()

    def test_invalid_counts_and_duplicate_markers_are_rejected(self):
        for value in (True, -1, 0.1, "1", None, float("nan")):
            with self.subTest(value=value):
                self.data["candidate"]["results"][0]["toolCalls"] = value
                with self.assertRaises(ValueError):
                    self.evaluate()
        self.data["candidate"]["results"][0]["toolCalls"] = 3
        self.data["candidate"]["results"][0]["claims"] = ["persisted", "persisted"]
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_unknown_fields_are_rejected(self):
        self.data["proposal"]["execute"] = "do not run this"
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_cli_probe_verify_compose_and_stale_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in self.data.items():
                (root / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
            inputs = [part for name in improve.INPUTS
                      for part in (f"--{name}", str(root / f"{name}.json"))]

            def run(command, *extra):
                return subprocess.run([sys.executable, str(SCRIPT), command, *inputs, *extra],
                                      capture_output=True, text=True)

            report = root / "probe.json"
            packet = root / "review.json"
            self.assertEqual(run("probe", "--output", str(report)).returncode, 0)
            self.assertEqual(run("verify", "--report", str(report)).returncode, 0)
            self.assertEqual(run("compose", "--report", str(report),
                                 "--output", str(packet)).returncode, 0)
            original = report.read_bytes()
            self.assertEqual(run("probe", "--output", str(report)).returncode, 2)
            self.assertEqual(report.read_bytes(), original)
            tampered = json.loads(original)
            tampered["adopted"] = True
            report.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertEqual(run("verify", "--report", str(report)).returncode, 2)
            tampered = json.loads(original)
            tampered["schemaVersion"] = True
            report.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertEqual(run("verify", "--report", str(report)).returncode, 2)
            report.write_bytes(original)
            for name in improve.INPUTS:
                path = root / f"{name}.json"
                raw = path.read_bytes()
                path.write_bytes(raw + b"\n")
                self.assertEqual(run("verify", "--report", str(report)).returncode, 2)
                self.assertEqual(run("compose", "--report", str(report),
                                     "--output", str(root / "stale.json")).returncode, 2)
                self.assertFalse((root / "stale.json").exists())
                path.write_bytes(raw)
            self.assertEqual(run("verify", "--report", str(report)).returncode, 0)

    def test_cli_invalid_input_and_blocked_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {}
            for name, value in self.data.items():
                paths[name] = root / f"{name}.json"
                paths[name].write_text(json.dumps(value), encoding="utf-8")
            inputs = [part for name in improve.INPUTS
                      for part in (f"--{name}", str(paths[name]))]
            output = root / "probe.json"
            self.data["candidate"]["results"][2]["decision"] = "post"
            paths["candidate"].write_text(json.dumps(self.data["candidate"]), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "probe", *inputs,
                                     "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(output.read_text())["status"], "blocked")
            paths["proposal"].write_text('{"id": 1, "id": 2}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "probe", *inputs,
                                     "--output", str(root / "invalid.json")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("duplicate key", result.stderr)
            self.assertFalse((root / "invalid.json").exists())

    def test_candidate_text_is_never_executed(self):
        self.data["proposal"]["changes"][0]["after"] = (
            "untrusted candidate text; must only be copied into an inert review packet"
        )
        report = self.evaluate()
        report["inputSha256"] = {}
        packet = improve.compose(report, self.data["proposal"])
        self.assertEqual(packet["proposedChanges"], self.data["proposal"]["changes"])
        self.assertFalse(packet["adopted"])


if __name__ == "__main__":
    unittest.main()
