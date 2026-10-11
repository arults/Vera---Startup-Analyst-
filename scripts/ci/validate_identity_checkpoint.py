#!/usr/bin/env python3
"""Replay the identity checkpoint in a disposable exact-head export, never the checkout.

Only hash/status evidence may be uploaded. Generated candidates and full-draw
sidecars stay together in the disposable tree and are not empirical promotion.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tarfile

GENERATORS = (
    "src.phase1d.build_republic_europe_identity_review",
    "src.phase1d.apply_republic_europe_identity_review",
    "src.phase1d.rebuild_republic_europe_outcomes_v4",
    "src.phase1d.estimate_republic_europe_candidate_v3",
)
OUTPUT_NAMES = (
    "cp3_republic_europe_identity_review_queue.csv",
    "cp3_republic_europe_identity_unmatched_after_queue.csv",
    "cp3_republic_europe_identity_review_summary.json",
    "cp3_republic_europe_identity_review_manifest.json",
    "cp3_republic_europe_identity_review_decisions.csv",
    "cp3_republic_europe_identity_matches_accepted.csv",
    "cp3_republic_europe_business_observations_v2.csv",
    "cp3_republic_europe_identity_review_applied_summary.json",
    "cp3_republic_europe_identity_review_applied_manifest.json",
    "cp3_republic_europe_outcome_ledger_v4.csv",
    "cp3_republic_europe_outcome_ledger_v4_summary.json",
    "cp3_republic_europe_outcome_ledger_v4_manifest.json",
    "cp4_republic_europe_rq1_candidate_v3.csv",
    "cp4_republic_europe_rq2_gate_v3.csv",
    "cp4_republic_europe_candidate_v3_summary.json",
    "cp4_republic_europe_candidate_v3_manifest.json",
)
DATA = "data/phase1d"
AUDIT_SOURCE_NAMES = {
    "cp3_republic_europe_outcome_ledger_v4.csv",
    "src/phase1d/estimate_republic_europe_candidate_v3.py",
    "src/phase1c/estimators.py", "src/phase1c/outcomes.py", "src/phase1c/reporting.py",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path, *, checkout: bool = False) -> dict:
    """Include all files (including ignored files), bytes, and executable bits."""
    result = {}
    for base, directories, files in os.walk(root, followlinks=False):
        if checkout and Path(base) == root and ".git" in directories:
            directories.remove(".git")
        for name in directories:
            if (Path(base) / name).is_symlink():
                raise ValueError("symlink directory is unsupported")
        for name in files:
            path = Path(base) / name
            if checkout and path == root / ".git":
                continue
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError("nonregular file is unsupported")
            result[path.relative_to(root).as_posix()] = {
                "sha256": digest(path), "executable": bool(mode & 0o111)
            }
    return result


def inventory_changes(before: dict, after: dict) -> list[dict]:
    """Deterministic path/hash metadata only; never include file contents."""
    return [{"path": name, "before": before.get(name), "after": after.get(name)}
            for name in sorted(set(before) | set(after))
            if before.get(name) != after.get(name)]


def unchanged_or_raise(before: dict, after: dict, message: str) -> None:
    changes = inventory_changes(before, after)
    if changes:
        print(json.dumps({"diagnostic": "identity_ci_inventory_change",
                          "stage": message, "changed_file_count": len(changes),
                          "changes": changes}, sort_keys=True), file=sys.stderr, flush=True)
        raise ValueError(message)


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def export_exact_head(source: Path, destination: Path, expected_sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("full triggered commit SHA required")
    if git(source, "rev-parse", "HEAD").decode().strip() != expected_sha:
        raise ValueError("checkout differs from triggered commit")
    expected = {}
    for record in git(source, "ls-tree", "-rz", expected_sha).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        path = os.fsdecode(raw_path)
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise ValueError("only regular tracked files are supported")
        if Path(path).is_absolute() or any(p in ("..", ".git") for p in Path(path).parts):
            raise ValueError("unsafe tracked path")
        expected[path] = (mode, oid.decode())
    destination.mkdir()
    archive = destination.parent / "source.tar"
    subprocess.run(["git", "-C", str(source), "archive", "--format=tar",
                    "--output", str(archive), expected_sha], check=True)
    try:
        with tarfile.open(archive) as tar:
            tar.extractall(destination, filter="data")
    finally:
        archive.unlink()
    actual = inventory(destination)
    if set(actual) != set(expected):
        raise ValueError("export inventory differs from triggered commit")
    for name, (mode, oid) in expected.items():
        raw = (destination / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != oid or actual[name]["executable"] != (mode == b"100755"):
            raise ValueError("export bytes or executable mode differ from commit")
        if raw.startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise ValueError("LFS pointers are unsupported")


def bound_file(data: Path, name: str, expected_hash: str) -> Path:
    if not isinstance(name, str) or Path(name).name != name or name in ("", ".", ".."):
        raise ValueError("artifact must be a local filename")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash or ""):
        raise ValueError("SHA-256 binding required")
    path = data / name
    if not path.is_file() or path.is_symlink() or digest(path) != expected_hash:
        raise ValueError("missing or mismatched bound artifact")
    return path


def verify_candidate(data: Path, work: Path) -> set[str]:
    """Require the complete CSV -> audit manifest -> full-draw binding chain."""
    manifest = json.loads((data / OUTPUT_NAMES[-1]).read_text())
    summary = json.loads((data / OUTPUT_NAMES[-2]).read_text())
    if summary.get("promotion_status") != "CANDIDATE_ONLY" or summary.get("rates_promoted") is not False:
        raise ValueError("candidate-only status required")
    if manifest.get("summary") != summary:
        raise ValueError("candidate manifest summary differs")
    if set(manifest["output_files"]) != set(OUTPUT_NAMES[-4:-1]):
        raise ValueError("candidate output hash inventory differs")
    if set(manifest["source_files"]) != {"cp3_republic_europe_outcome_ledger_v4.csv", "cp4_republic_europe_rq1_candidate_v2.csv"}:
        raise ValueError("candidate source hash inventory differs")
    for name, value in manifest["output_files"].items():
        bound_file(data, name, value)
    for name, value in manifest["source_files"].items():
        if value is None:
            if name != "cp4_republic_europe_rq1_candidate_v2.csv" or (data / name).exists():
                raise ValueError("missing source hash")
        else:
            bound_file(data, name, value)
    binding = manifest["bootstrap_audit"]
    audit_path = bound_file(data, binding["bootstrap_audit_manifest"], binding["bootstrap_audit_manifest_sha256"])
    draws_path = bound_file(data, binding["bootstrap_audit_artifact"], binding["bootstrap_audit_artifact_sha256"])
    if audit_path.name != f"cp4_republic_europe_candidate_v3_bootstrap_manifest.{digest(audit_path)}.json":
        raise ValueError("content-addressed manifest required")
    if draws_path.name != f"cp4_republic_europe_candidate_v3_bootstrap_draws.{digest(draws_path)}.jsonl.gz":
        raise ValueError("content-addressed draws required")
    audit = json.loads(audit_path.read_text())
    if audit["artifact"]["relative_path"] != draws_path.name or audit["artifact"]["sha256"] != digest(draws_path):
        raise ValueError("audit draw binding differs")
    if set(audit["source_sha256"]) != AUDIT_SOURCE_NAMES:
        raise ValueError("audit source hash inventory differs")
    for name, value in audit["source_sha256"].items():
        location = work / name if name.startswith("src/") else data / name
        if not location.resolve().is_relative_to(work.resolve()) or digest(location) != value:
            raise ValueError("audit source binding differs")
    with (data / "cp4_republic_europe_rq1_candidate_v3.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or any(any(row.get(k) != v for k, v in binding.items()) for row in rows):
        raise ValueError("CSV audit binding differs")
    expected_reports = set()
    for row in rows:
        prefix = f"{row['platform']}/{row['offering_year']}/{row['horizon_months']}"
        for endpoint in ("success", "closure", "survival"):
            report_id = row.get(f"{endpoint}_bootstrap_report_id")
            if report_id != f"{prefix}/{endpoint}" or report_id in expected_reports:
                raise ValueError("missing, stale, or duplicate CSV endpoint report ID")
            expected_reports.add(report_id)
    if expected_reports != set(audit["reports"]):
        raise ValueError("CSV endpoint report coverage differs from audit")
    seen = set()
    with gzip.open(draws_path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            record = json.loads(line)
            report_id, report = record["report_id"], record["report"]
            if report_id in seen or report_id not in audit["reports"]:
                raise ValueError("duplicate or unbound draw report")
            seen.add(report_id)
            meta = audit["reports"][report_id]
            if meta["line_1based"] != line_number or any(meta[k] != report[k] for k in
                    ("requested_replicates", "completed_replicates", "interval_status")):
                raise ValueError("draw report metadata differs")
            requested, completed = report["requested_replicates"], report["completed_replicates"]
            if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in (requested, completed)):
                raise ValueError("invalid replicate counts")
            if report["execution_status"].startswith("NOT_RUN_"):
                if report["draws"] or completed != 0 or report["not_run_draw_count"] != requested:
                    raise ValueError("invalid not-run draw declaration")
            elif (report["execution_status"] != "RUN_ALL_REQUESTED_DRAWS_RETAINED"
                  or len(report["draws"]) != requested or completed != requested
                  or report["not_run_draw_count"] != 0
                  or [draw["index"] for draw in report["draws"]] != list(range(requested))):
                raise ValueError("requested draws were not all retained")
    if seen != set(audit["reports"]):
        raise ValueError("missing draw report")
    return {audit_path.name, draws_path.name}


def validate(source: Path, scratch: Path, expected_sha: str, *, run=subprocess.run) -> dict:
    source, scratch = source.resolve(), scratch.resolve()
    if scratch.is_relative_to(source) or source.is_relative_to(scratch):
        raise ValueError("scratch must be outside the original checkout")
    before = inventory(source, checkout=True)
    scratch.mkdir(parents=True, exist_ok=False)
    work = scratch / "work"
    completed = []
    try:
        export_exact_head(source, work, expected_sha)
        exported = inventory(work)
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        # Drop import overrides so modules cannot resolve back to the original tree.
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=work, env=environment, check=True)
        completed.append("full_regression_suite")
        unchanged_or_raise(exported, inventory(work), "tests changed exported source files")
        for module in GENERATORS:
            # The archived apply module uses local deterministic dispositions;
            # this replay does not invoke a new JEV review or external service.
            print(f"Replaying isolated local stage: {module}", flush=True)
            run([sys.executable, "-B", "-m", module], cwd=work, env=environment, check=True)
            completed.append(module)
        sidecars = verify_candidate(work / DATA, work)
        allowed = {f"{DATA}/{name}" for name in (*OUTPUT_NAMES, *sidecars)}
        after = inventory(work)
        changed = {name for name in set(exported) | set(after) if exported.get(name) != after.get(name)}
        if changed - allowed or set(exported) - set(after):
            raise ValueError("rebuild modified a non-output source or deleted a tracked file")
        for name in OUTPUT_NAMES:
            if not (work / DATA / name).is_file():
                raise ValueError("incomplete candidate checkpoint")
        evidence = {
            "schema_version": "identity-ci-isolation-v1", "triggered_head": expected_sha,
            "status": "PASS", "completed_stages": completed,
            "original_checkout_unchanged": True, "export_verified_against_commit": True,
            "full_draw_bindings_verified": True, "rates_promoted": False,
            "promotion_status": "CANDIDATE_ONLY", "raw_artifacts_uploaded": False,
            "source_inventory_sha256": hashlib.sha256(json.dumps(exported, sort_keys=True).encode()).hexdigest(),
            "candidate_files": {name: digest(work / DATA / name) for name in sorted((*OUTPUT_NAMES, *sidecars))},
        }
    finally:
        unchanged_or_raise(before, inventory(source, checkout=True),
                           "original checkout changed during isolated validation")
    evidence_dir = scratch / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "validation.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[2]
    result = validate(source, args.scratch_root, args.expected_sha)
    print(json.dumps({k: result[k] for k in ("status", "triggered_head", "rates_promoted", "raw_artifacts_uploaded")}))


if __name__ == "__main__":
    main()
