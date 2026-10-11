"""Synthetic safety regressions; no private source fixtures or external services."""
import csv
import gzip
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("identity_ci", ROOT / "scripts/ci/validate_identity_checkpoint.py")
ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci)


class IdentityCIIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "checkout"
        self.source.mkdir()
        (self.source / "frozen.csv").write_bytes(b"original,bytes\r\n1,2\r\n")
        (self.source / "tests").mkdir()
        (self.source / "tests/test_fixture.py").write_text("import unittest\nclass Fixture(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n")
        for name in ci.AUDIT_SOURCE_NAMES:
            if name.startswith("src/"):
                path = self.source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# synthetic source fixture\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        self.head = self.git("rev-parse", "HEAD").decode().strip()
        self.scratch = self.base / "scratch"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], stderr=subprocess.DEVNULL)

    def write_candidate(self, work, report_override=None, audit_override=None):
        data = work / ci.DATA
        data.mkdir(parents=True, exist_ok=True)
        for name in ci.OUTPUT_NAMES:
            (data / name).write_text("synthetic\n")
        summary = {"promotion_status": "CANDIDATE_ONLY", "rates_promoted": False}
        (data / ci.OUTPUT_NAMES[-2]).write_text(json.dumps(summary))
        report = {"requested_replicates": 2, "completed_replicates": 2,
                  "execution_status": "RUN_ALL_REQUESTED_DRAWS_RETAINED", "not_run_draw_count": 0,
                  "interval_status": "WITHHELD", "draws": [{"index": 0, "estimate": 0.1}, {"index": 1, "estimate": None}]}
        if report_override:
            report.update(report_override)
        report_ids = [f"republic_europe/2020/12/{endpoint}" for endpoint in ("closure", "success", "survival")]
        draw_bytes = gzip.compress("".join(json.dumps({"report_id": report_id, "report": report}) + "\n" for report_id in report_ids).encode(), mtime=0)
        draw_hash = ci.hashlib.sha256(draw_bytes).hexdigest()
        draw_name = f"cp4_republic_europe_candidate_v3_bootstrap_draws.{draw_hash}.jsonl.gz"
        (data / draw_name).write_bytes(draw_bytes)
        audit = {"artifact": {"relative_path": draw_name, "sha256": draw_hash},
                 "source_sha256": {name: ci.digest(work / name if name.startswith("src/") else data / name) for name in ci.AUDIT_SOURCE_NAMES},
                 "reports": {report_id: {"line_1based": i + 1, **{k: report[k] for k in ("requested_replicates", "completed_replicates", "interval_status")}} for i, report_id in enumerate(report_ids)}}
        if audit_override is not None:
            audit.update(audit_override)
        audit_bytes = json.dumps(audit).encode()
        audit_hash = ci.hashlib.sha256(audit_bytes).hexdigest()
        audit_name = f"cp4_republic_europe_candidate_v3_bootstrap_manifest.{audit_hash}.json"
        (data / audit_name).write_bytes(audit_bytes)
        binding = {"bootstrap_audit_manifest": audit_name, "bootstrap_audit_manifest_sha256": audit_hash,
                   "bootstrap_audit_artifact": draw_name, "bootstrap_audit_artifact_sha256": draw_hash}
        csv_row = dict(binding, platform="republic_europe", offering_year="2020", horizon_months="12")
        csv_row.update({f"{endpoint}_bootstrap_report_id": f"republic_europe/2020/12/{endpoint}" for endpoint in ("success", "closure", "survival")})
        with (data / "cp4_republic_europe_rq1_candidate_v3.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_row)); writer.writeheader(); writer.writerow(csv_row)
        manifest = {"summary": summary, "bootstrap_audit": binding,
                    "output_files": {name: ci.digest(data / name) for name in ci.OUTPUT_NAMES[-4:-1]},
                    "source_files": {"cp3_republic_europe_outcome_ledger_v4.csv": ci.digest(data / "cp3_republic_europe_outcome_ledger_v4.csv"), "cp4_republic_europe_rq1_candidate_v2.csv": None}}
        (data / ci.OUTPUT_NAMES[-1]).write_text(json.dumps(manifest))
        return binding

    def fake_run(self, args, *, cwd, env, check):
        self.assertEqual(cwd, self.scratch / "work")
        self.assertTrue(check)
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertNotIn("PYTHONPATH", env)
        if args[-1] == ci.GENERATORS[-1]:
            self.write_candidate(cwd)

    def test_success_preserves_original_and_emits_hashes_only(self):
        before = ci.inventory(self.source, checkout=True)
        with mock.patch.dict(ci.os.environ, {"PYTHONPATH": str(self.source)}):
            result = ci.validate(self.source, self.scratch, self.head, run=self.fake_run)
        self.assertEqual(before, ci.inventory(self.source, checkout=True))
        self.assertEqual(result["triggered_head"], self.head)
        self.assertEqual(result["completed_stages"], ["full_regression_suite", *ci.GENERATORS])
        self.assertEqual(len(result["candidate_files"]), 18)
        self.assertFalse(result["rates_promoted"])
        self.assertFalse(result["raw_artifacts_uploaded"])
        self.assertEqual([p.name for p in (self.scratch / "evidence").iterdir()], ["validation.json"])
        self.assertNotIn("synthetic/cell", (self.scratch / "evidence/validation.json").read_text())

    def test_original_frozen_bytes_remain_identical(self):
        ci.validate(self.source, self.scratch, self.head, run=self.fake_run)
        self.assertEqual((self.source / "frozen.csv").read_bytes(), b"original,bytes\r\n1,2\r\n")
        self.assertFalse((self.source / ci.DATA).exists())
        self.assertFalse((self.scratch / "work/.git").exists())

    def test_wrong_head_fails_before_any_stage(self):
        with self.assertRaisesRegex(ValueError, "triggered commit"):
            ci.validate(self.source, self.scratch, "0" * 40, run=lambda *a, **k: self.fail("must not run"))
        self.assertFalse((self.scratch / "evidence").exists())

    def test_mutable_ref_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "full triggered"):
            ci.validate(self.source, self.scratch, "phase-1d", run=self.fake_run)

    def test_nested_scratch_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            ci.validate(self.source, self.source / "scratch", self.head)

    def test_existing_scratch_rejected(self):
        self.scratch.mkdir()
        with self.assertRaises(FileExistsError):
            ci.validate(self.source, self.scratch, self.head)

    def test_test_failure_blocks_generators_and_evidence(self):
        calls = []
        def fail(args, **kwargs):
            calls.append(args)
            raise subprocess.CalledProcessError(1, args)
        with self.assertRaises(subprocess.CalledProcessError):
            ci.validate(self.source, self.scratch, self.head, run=fail)
        self.assertEqual(len(calls), 1)
        self.assertFalse((self.scratch / "evidence").exists())

    def test_test_source_mutation_fails(self):
        def mutate(args, **kwargs):
            (kwargs["cwd"] / "frozen.csv").write_text("mutated")
        with self.assertRaisesRegex(ValueError, "tests changed"):
            ci.validate(self.source, self.scratch, self.head, run=mutate)
        self.assertFalse((self.scratch / "evidence").exists())

    def test_generator_source_mutation_fails(self):
        def mutate(args, **kwargs):
            self.fake_run(args, **kwargs)
            if args[-1] == ci.GENERATORS[-1]:
                (kwargs["cwd"] / "frozen.csv").write_text("mutated")
        with self.assertRaisesRegex(ValueError, "non-output"):
            ci.validate(self.source, self.scratch, self.head, run=mutate)

    def test_original_mutation_fails_even_on_exception(self):
        def mutate(args, **kwargs):
            (self.source / "frozen.csv").write_text("mutated")
            raise RuntimeError("stage failed")
        with self.assertRaisesRegex(ValueError, "original checkout changed"):
            ci.validate(self.source, self.scratch, self.head, run=mutate)

    def test_missing_sidecar_rejected(self):
        binding = self.write_candidate(self.source)
        (self.source / ci.DATA / binding["bootstrap_audit_artifact"]).unlink()
        with self.assertRaisesRegex(ValueError, "bound artifact"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_sidecar_tamper_rejected(self):
        binding = self.write_candidate(self.source)
        (self.source / ci.DATA / binding["bootstrap_audit_artifact"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "bound artifact"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_path_traversal_binding_rejected(self):
        with self.assertRaisesRegex(ValueError, "local filename"):
            ci.bound_file(self.source, "../outside", "0" * 64)

    def test_tracked_symlink_rejected(self):
        (self.source / "link").symlink_to("frozen.csv")
        self.git("add", "link")
        self.git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "link")
        self.scratch.mkdir()
        with self.assertRaisesRegex(ValueError, "regular tracked"):
            ci.export_exact_head(self.source, self.scratch / "work", self.git("rev-parse", "HEAD").decode().strip())

    def test_export_ignore_cannot_silently_omit_source(self):
        (self.source / ".gitattributes").write_text("frozen.csv export-ignore\n")
        self.git("add", ".")
        self.git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "ignore")
        with self.assertRaisesRegex(ValueError, "export inventory"):
            ci.validate(self.source, self.scratch, self.git("rev-parse", "HEAD").decode().strip())

    def test_real_test_command_runs_in_export(self):
        calls = []
        def execute_tests(args, **kwargs):
            calls.append(args)
            if "unittest" in args:
                subprocess.run(args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                self.fake_run(args, **kwargs)
        ci.validate(self.source, self.scratch, self.head, run=execute_tests)
        self.assertEqual(calls[0][2:], ["-m", "unittest", "discover", "-s", "tests", "-v"])

    def test_declared_not_run_reports_are_valid(self):
        self.write_candidate(self.source, {
            "completed_replicates": 0, "execution_status": "NOT_RUN_ZERO_OBSERVED_EVENTS",
            "not_run_draw_count": 2, "draws": []})
        self.assertEqual(len(ci.verify_candidate(self.source / ci.DATA, self.source)), 2)

    def test_false_not_run_declaration_rejected(self):
        self.write_candidate(self.source, {"execution_status": "NOT_RUN_ZERO_OBSERVED_EVENTS"})
        with self.assertRaisesRegex(ValueError, "not-run"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_missing_draw_is_rejected_even_with_rebound_hashes(self):
        self.write_candidate(self.source, {"draws": [{"index": 0, "estimate": 0.1}]})
        with self.assertRaisesRegex(ValueError, "not all retained"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_duplicate_draw_index_is_rejected(self):
        self.write_candidate(self.source, {"draws": [{"index": 0}, {"index": 0}]})
        with self.assertRaisesRegex(ValueError, "not all retained"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_candidate_promotion_is_rejected(self):
        self.write_candidate(self.source)
        path = self.source / ci.DATA / ci.OUTPUT_NAMES[-2]
        path.write_text(json.dumps({"promotion_status": "PROMOTED", "rates_promoted": True}))
        with self.assertRaisesRegex(ValueError, "candidate-only"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_generator_failure_blocks_evidence(self):
        calls = []
        def fail(args, **kwargs):
            calls.append(args)
            if args[-1] == ci.GENERATORS[1]:
                raise subprocess.CalledProcessError(1, args)
        with self.assertRaises(subprocess.CalledProcessError):
            ci.validate(self.source, self.scratch, self.head, run=fail)
        self.assertEqual(len(calls), 3)
        self.assertFalse((self.scratch / "evidence").exists())
        self.assertEqual((self.source / "frozen.csv").read_bytes(), b"original,bytes\r\n1,2\r\n")

    def test_stale_csv_report_id_rejected_with_rebound_csv_hash(self):
        self.write_candidate(self.source)
        data = self.source / ci.DATA
        csv_path = data / "cp4_republic_europe_rq1_candidate_v3.csv"
        csv_path.write_text(csv_path.read_text().replace("republic_europe/2020/12/success", "stale/success"))
        path = data / ci.OUTPUT_NAMES[-1]
        manifest = json.loads(path.read_text())
        manifest["output_files"][csv_path.name] = ci.digest(csv_path)
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "CSV endpoint report ID"):
            ci.verify_candidate(data, self.source)

    def test_missing_output_hash_inventory_rejected(self):
        self.write_candidate(self.source)
        path = self.source / ci.DATA / ci.OUTPUT_NAMES[-1]
        manifest = json.loads(path.read_text()); manifest["output_files"] = {}
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "output hash inventory"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_missing_source_hash_inventory_rejected(self):
        self.write_candidate(self.source)
        path = self.source / ci.DATA / ci.OUTPUT_NAMES[-1]
        manifest = json.loads(path.read_text()); manifest["source_files"] = {}
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "source hash inventory"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_missing_audit_source_hashes_rejected(self):
        self.write_candidate(self.source, audit_override={"source_sha256": {}})
        with self.assertRaisesRegex(ValueError, "audit source hash inventory"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_missing_audit_report_coverage_rejected(self):
        self.write_candidate(self.source, audit_override={"reports": {}})
        with self.assertRaisesRegex(ValueError, "report coverage"):
            ci.verify_candidate(self.source / ci.DATA, self.source)

    def test_inventory_diagnostic_is_sorted_hash_metadata_only(self):
        old = {"z.csv": {"sha256": "a" * 64, "executable": False},
               "removed.csv": {"sha256": "b" * 64, "executable": False}}
        new = {"z.csv": {"sha256": "c" * 64, "executable": True},
               "added.csv": {"sha256": "d" * 64, "executable": False}}
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.assertRaisesRegex(ValueError, "tests changed"):
            ci.unchanged_or_raise(old, new, "tests changed exported source files")
        result = json.loads(stream.getvalue())
        self.assertEqual(result["changed_file_count"], 3)
        self.assertEqual([row["path"] for row in result["changes"]], ["added.csv", "removed.csv", "z.csv"])
        self.assertIsNone(result["changes"][0]["before"])
        self.assertIsNone(result["changes"][1]["after"])
        self.assertEqual(result["changes"][2]["after"], new["z.csv"])
        self.assertEqual(set(result["changes"][2]), {"path", "before", "after"})

    def test_unchanged_inventory_emits_no_diagnostic(self):
        value = {"file.py": {"sha256": "a" * 64, "executable": False}}
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            ci.unchanged_or_raise(value, value, "must not fail")
        self.assertEqual(stream.getvalue(), "")

    def test_test_mutation_reports_relative_hashes_without_contents(self):
        stream = io.StringIO()
        secret_fixture = "SYNTHETIC_CONTENT_MUST_NOT_BE_LOGGED"
        def mutate(args, **kwargs):
            (kwargs["cwd"] / "frozen.csv").write_text(secret_fixture)
        with contextlib.redirect_stderr(stream), self.assertRaisesRegex(ValueError, "tests changed"):
            ci.validate(self.source, self.scratch, self.head, run=mutate)
        text = stream.getvalue()
        result = json.loads(text)
        self.assertEqual(result["changes"][0]["path"], "frozen.csv")
        self.assertNotIn(secret_fixture, text)
        self.assertNotIn(str(self.source), text)
        self.assertFalse((self.scratch / "evidence").exists())

    def test_workflow_has_no_writer_or_raw_upload_path(self):
        text = (ROOT / ".github/workflows/phase1d-republic-europe-identity-review.yml").read_text()
        for forbidden in ("contents: write", "git add", "git commit", "git push", "git rebase", "ref: phase-1d", "data/phase1d/"):
            self.assertNotIn(forbidden, text)
        for required in ("ref: ${{ github.sha }}", "persist-credentials: false", "requests beautifulsoup4 curl_cffi", "evidence/validation.json", "--expected-sha", "--scratch-root"):
            self.assertIn(required, text)
        self.assertNotIn("continue-on-error", text)


if __name__ == "__main__":
    unittest.main()
