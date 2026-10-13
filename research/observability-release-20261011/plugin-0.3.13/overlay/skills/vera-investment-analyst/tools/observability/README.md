# Vera local observability and evaluation foundation v0.1.0

**Working local SDK and synthetic regression harness. Production company-analysis host integration is missing.** This is an additive companion to `research/run-metrics-v0.1.0`, not an interception layer, hosted telemetry service or a live-company validation result. No network requests, credentials, new persistent access, provider calls or paid services are required by this package.

## What is implemented

- Durable append-only JSONL spans, strict versioned event/evaluation schemas, explicit run/attempt/parent/retry IDs and safe error categories.
- A predeclared eleven-component inventory, required evaluation inventory, missing instrumentation, explicit N/A reasons and provenance references.
- Independent execution outcome, telemetry health, engineering-check results and research-quality results. An unobserved component is not a pass. An empty ledger is `not_run`.
- Actual context-manager hooks around local work. Exceptions are recorded by allowlisted category and re-raised; their messages, stacks, prompts and outputs are never captured.
- A static local HTML dashboard with component, failure, retry, provenance and evaluation drill-downs. It has no JavaScript or network resources, escapes displayed text and uses a restrictive CSP.
- A separately linked run-metrics dashboard, joined by actual run and dispatch IDs. Tokens, cost, wall time and memory remain the metrics package's responsibility; no duplicate metric collector is added here.
- Eight replayable synthetic cases and strict matched-case/config comparisons. Replaying tests contract behavior, not investment quality or calibration.

The release contains executable instrumentation, not merely documentation. It does **not** automatically activate instrumentation in ChatGPT, the plugin host, hidden workers, provider servers or every user's runs. Real host integration needs the serving runtime's owner/source and a tested adapter. No live company analysis was executed to test this foundation.

## Run locally

Python 3.10+ standard library only; verified with Python 3.12. From the repository root:

```sh
python -I -B -m unittest discover -s research/observability-v0.1.0 -p 'test_*.py' -v
python -I -B research/observability-v0.1.0/synthetic_benchmark.py run \
  --output-dir /tmp/vera-observability-baseline \
  --metrics-module research/run-metrics-v0.1.0/vera_metrics.py
python -I -B research/observability-v0.1.0/synthetic_benchmark.py run \
  --output-dir /tmp/vera-observability-candidate \
  --metrics-module research/run-metrics-v0.1.0/vera_metrics.py
python -I -B research/observability-v0.1.0/synthetic_benchmark.py compare \
  /tmp/vera-observability-baseline/benchmark.json \
  /tmp/vera-observability-candidate/benchmark.json
```

Use fresh output directories; existing benchmark traces are never overwritten. Open `complete/dashboard.html` in either output directory, or the shipped `examples/synthetic/dashboard.html`. The latter's local metrics drill-down is `metrics/dashboard.html`. No server is required.

The plugin layout can place this directory at `tools/observability` alongside `tools/run_metrics`. Point `--metrics-module` to the sibling `run_metrics/vera_metrics.py`. Imports resolve from `__file__`, so the same files work in relocated directories and under Python isolated mode. No duplicate metrics implementation is bundled here.

For a caller-supplied trace:

```sh
python -I -B research/observability-v0.1.0/vera_observability.py trace.jsonl --output-dir /tmp/vera-trace-report
```

CLI exit codes: `0` is a structurally valid report (possibly **partial**, blocked or failed execution); `1` is invalid telemetry/no observations or a failed synthetic benchmark/regression; `2` is malformed input/output or an incompatible comparison basis. Always inspect the report's separate statuses. Merely running the report command successfully does not certify an analysis.

## Integration contract

A real adapter must:

1. Create both recorders with the same opaque run ID, then declare all applicable components, evaluation IDs and version/hash references before execution.
2. Wrap each actual component with `RunRecorder.span`, pass explicit parent IDs for nesting, and put the metrics recorder's stable physical dispatch ID in `metrics_attempt_id` for each model/tool/JEV dispatch. The trace's `attempt_id` identifies a run/resume epoch; it is distinct from metrics dispatch attempts.
3. Supply real provider usage only to the metrics recorder. A local deterministic model/JEV stand-in does not have provider tokens or cost; those fields remain unavailable.
4. Emit evaluations only for actual checks. Bind component checks to an ended matching span, preserve all effective artifact/input/model/prompt/rubric/dataset/config/code references, and retain evidence by safe version/hash reference. Full-system evaluations target `system` with no span ID.
5. Finish with the actual execution and capture statuses. `finish` checks its terminal claim before appending it. Read/aggregate also independently checks imported records. If the process crashes, retain the incomplete file, reopen it, explicitly resume with a new attempt ID and link retried spans through `retry_of`.
6. Validate the metrics ledger with its own package, then call `correlate_metrics` with the validated metrics report. Supply expected generated HTML bytes to verify the linked report's bytes. The benchmark demonstrates this actual path.

Context-manager example (inside an adapter with already-created recorders):

```python
dispatch_id = 'retrieval-dispatch-1'
with trace.span('retrieval', span_id='retrieve-1', metrics_attempt_id=dispatch_id):
    with metrics.attempt('tool', 'source-retrieval', attempt_id=dispatch_id) as usage:
        result = perform_authorized_retrieval()
        # Actual available receipt fields may be assigned to usage; never guess.
# Evaluate result locally, store a safe artifact reference, and emit a bound eval.
```

`Ledger` is thread-safe within one owner instance and uses flush/fsync, owner-only permissions for newly created trace files and symlink-file rejection. It is **not** a multiprocess shared writer or a cryptographically tamper-proof archive. Use one writer per trace file and distinct run IDs; aggregate files' decoded events in the caller. Existing malformed or torn files are rejected, never silently truncated or repaired. The caller is responsible for secure directories, retention, access control, backup and opaque identifiers.

This release fails closed on contradictory event graphs and false completion claims. A recorded failure followed by a linked successful retry may recover execution. An interrupted original span that never supplied an end remains missing telemetry even after retry success. Later evidence cannot repair a false earlier complete-capture claim. Timestamps must be timezone-aware and monotonic in each run; clock reversals are visible errors. There is no attempt to infer overlapping wall time from component sums.

## Coverage and component mapping

The declared inventory is `prompt`, `identity`, `planning`, `research`, `retrieval`, `sourcing_verifier`, `analysis`, `model`, `jev`, `report`, `persistence`.

- Input/prompt resolution and identity matching belong to prompt/identity.
- Search, retrieval, extraction, normalization and provenance/claim checks belong to research/retrieval/sourcing_verifier, with additional nested spans for repeated operations.
- Reference-class selection, causal/return computations and decision logic belong to planning/analysis/model.
- Independent JEV checks, output validation/rendering, and artifact/telemetry persistence belong to jev/report/persistence as actually used.

This coarse taxonomy can contain multiple nested spans per component; it is not a claim to know a future host's complete component graph. Host adapters must map their actual boundaries and update the versioned inventory if it is insufficient. The fixed inventory cannot silently omit a component. Components not needed by a mode use `not_applicable` plus an allowlisted material reason (`NOT_USED_BY_DECLARED_MODE`, `NO_MODEL_REQUEST_REQUIRED`, `NO_JEV_REVIEW_REQUIRED`, `NO_PERSISTENCE_REQUIRED`; `FIXTURE_OUT_OF_SCOPE` is synthetic-only). An observed component declared N/A is contradictory.

Observed/required coverage measures instrumentation, not successful execution. Completed counts are separate. Explicit `not_run`, `blocked`, `failed` and `cancelled` are observed statuses; no spans means `unobserved`, and an unclosed span means `incomplete`. Each component preserves failed and retried history.

Metrics correlation reports declared/matched/total attempts, missing references, unreferenced metric attempts, duplicate attribution and HTML-verification scope. `matched_declared_refs` with extra unreferenced metric attempts is only partial coverage. `matched` requires all observed metrics attempts be linked exactly once. A report link alone proves no correlation; generic report generation leaves `not_checked`. Content verification is explicitly `existence_only` unless caller-supplied generated bytes match the actual file.

Trace instrumentation, serialization, aggregation and dashboard-rendering overhead is not separately metered in this first adapter. The metrics fixture's launcher RSS is real process-lifetime peak and includes harness overhead; it is not hosted model/worker RAM. Final assistant-response usage and hidden upstream work remain excluded. Never use these synthetic fixtures for production latency/cost comparisons.

## Evaluations and reproducibility

Schemas: `vera.observability/1`, `vera.eval/1`, `vera.observability-report/1`, `vera.synthetic-benchmark/1`, `vera.synthetic-comparison/1`. The two JSON Schema files enforce structure; Python validation adds mandatory chronology, graph, provenance and semantic rules. `build_schemas.py` reproducibly regenerates the structural schemas. Schema JSON is self-contained and does not fetch a remote resolver.

References accept only `sha256:<64 lowercase hex digits>` or short `ver:<opaque-version>` labels. Run provenance declares all eight categories; explicit unknowns are null and force partial provenance/capture. Spans inherit run refs and may override them. Passing/failing evaluations require complete effective refs and an evidence reference. Component targets must end before their evaluation; stale artifact, model, prompt, rubric or other refs cannot count as a pass. A hash attests identity, not truth, independence or safe release of the underlying artifact.

The synthetic benchmark freezes its case dataset by content hash, keeps explicit evaluator/config/input/model/prompt/rubric references and hashes the exact runtime implementation and evaluator source. Comparisons require the same cases, input/model/prompt/rubric, dataset and evaluator-source basis. Different implementations can be compared. Different configs require `--allow-config-change`, which reports both configs without causal attribution. Metrics-adapter coverage must also match. Comparisons retain per-case regressions; empty checks, duplicate cases, inconsistent flags and unmatched bases fail closed. Comparison validates matching/schema/pass consistency but trusts supplied check outcomes; it does not independently recompute them from status summaries or certify report authenticity.

All eight cases are hand-designed synthetic development fixtures, with no independent holdout, live-company labels, empirical outcome sample or calibration estimate. They exercise complete flow, omitted component, exception, retry, interrupted/resumed capture, missing evaluation, failed evaluation, and generic JEV scope. The generic JEV case is an explicitly labeled local deterministic stand-in, **not** a TypeSafe request or a stored real review result.

`passed_declared_checks` is deliberately bounded. Engineering passes do not establish research quality. Generic-method advice cannot certify implementation or system behavior. Synthetic runs and synthetic/generic scopes cannot establish research quality. A real `research` evaluation still only records the declared rubric/check; no field denotes empirical calibration, an investment probability, a promoted prior or an accepted company estimate. Existing scientific gates remain external and mandatory. JEV records retain model/question/response references, confidence and scope; confidence is never substituted for evidence. Generic methodology reviews conducted during development guided the design, not code certification or company-estimate approval.

## Privacy and security boundaries

No free-text event/error/exception/prompt/response fields are accepted. Unknown keys, arbitrary prose, URLs and markup in IDs are rejected. Errors use a fixed category vocabulary and never stringify the exception. Dashboards escape all dynamic strings and reject absolute, external, traversal, query and script links.

These controls are not a general secret detector: a caller could still misuse an allowed opaque label or version to encode sensitive content. Never put credentials, personal/company names, raw confidential research, prompts, response text, hidden reasoning or secret-bearing paths in any telemetry field. Prefer generated opaque IDs and approved artifact hashes. Raw inputs/artifacts stay in their authorized store. This package neither uploads telemetry nor grants access to it.

## Verified and not verified

See `VERIFICATION.json` for exact source hashes and test evidence. Local tests, independent fault checks, matched synthetic replays and generated HTML/link/escaping checks have been run. **Browser/visual rendering has not been verified**: the available cloud browser could not launch under executor restrictions. No visual pass is claimed. Production host instrumentation, live-company output quality, complete hosted usage/cost, remote RAM and final-response capture remain unverified.

The scoped CI workflow has read-only repository permissions, exact-triggering-commit verification, a ten-minute bound, isolated tests and two metrics-linked synthetic replays. Remote CI success must be checked on the actual publication commit separately; a staged workflow or local pass is not a remote CI result.
