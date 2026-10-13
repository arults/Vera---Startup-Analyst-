# Vera component and whole-run observability contract v0.1.0

Phase 1D includes this observability/evaluation workstream. Its instrumentation, fixtures and structural checks do not complete or validate the separate investment-return model or its empirical calibration.

Purpose: make company-analysis behavior and evaluation results inspectable across each actual component and the whole run, without confusing operational success with investment validity. This extends `run-metrics-contract-v0.1.0.md`; all research, calibration and company-estimate review gates remain mandatory.

Companion trace and evaluation schema families are `vera.observability/1` and `vera.eval/1`, joined to `vera.run-metrics/1` through the same run ID. Their exact supported fields belong to the installed versioned runtime implementation; this procedure does not imply that its adapters are connected.

## Correlated component traces

- Propagate the metrics `run_id` and company/analysis identity into component traces and evaluations. Give each component execution a stable span ID, parent span ID, component name/version, worker/attempt identity, timestamps, status and safe failure category. Preserve causal nesting and parallel work; never derive wall time by summing overlapping spans.
- At run start, declare the component inventory expected for the selected mode. Cover the actual identity/input resolution, research/retrieval, source/claim extraction, terms normalization, causal/reference-class/return modeling, verification/JEV where required, synthesis/output validation, rendering and telemetry stages. Model/tool/worker attempts nest under the component that actually initiated them. Do not invent spans for work that did not happen.
- Reconcile expected versus observed spans at completion. Label completed, failed, blocked, cancelled, intentionally skipped/not applicable and missing instrumentation distinctly, with reasons. A missing span does not prove the component ran successfully, and a skipped component does not silently become a pass. Report coverage as observed/expected with excluded/not-applicable counts and gaps.
- Join attempt IDs to `vera.run-metrics/1` events rather than duplicate token/cost charges in multiple rollups. Observability overhead belongs in an explicit component/scope or disclosed exclusion, not hidden inside a flattering performance comparison.

## Three separate kinds of evidence

1. **Execution health:** real statuses, retries/failures, errors, latency, resource/cost scope and end-to-end completion. A successful tool response is not evidence that its content is correct.
2. **Research and decision quality:** source provenance/independence, sufficiency, contradictions, terms correctness, calibration/abstention behavior, return-panel compliance and actual independent company-estimate review. Retain existing gates. No telemetry score, unit-test pass, evaluator agreement or JEV vote establishes an empirical investment probability.
3. **Telemetry health:** expected/observed component and attempt coverage, missing fields, collection errors, duplicates/conflicts, clock limitations, sampling, redaction and adapter/version status. Incomplete collection must remain visible even when the analysis succeeded.

## Versioned, reproducible evaluations

Each evaluation result records an evaluation ID, associated run/span IDs, evaluator/check name and version, dataset/fixture ID and version or content hash, evaluation type, input/output artifact versions or safe hashes, criteria/expected behavior, actual result, timestamp, evidence and limits. For model-based evaluation, include evaluator model/configuration and rubric version where exposed, plus separately attributable usage; do not retain hidden reasoning or raw confidential payloads for observability.

Separate deterministic tests, synthetic scenario/replay checks, model judgments, actual company-estimate reviews and real live end-to-end observations. Mark unavailable, not run, blocked and inconclusive explicitly. Synthetic success is never presented as a measured live company run. Avoid evaluating a model solely on fixtures used to design its answer; report dataset overlap/holdout limits when relevant. Compare compatible analysis mode, component/model/prompt/rubric/pricing versions and cache/measurement scopes; show eligible sample size and missing/excluded counts. Preserve individual failure evidence rather than replacing it with a favorable average.

Required evaluations should test both useful outcomes and failure behavior: source/terms correctness, unsupported claims and abstention, missing evidence, retry/timeout/cancellation, repeated event delivery, missing telemetry, child/parent double-counting, privacy/redaction, schema violations and the five-row final output. Additional tests follow the actual component and decision risks. Run real JEV/independent reviews only when required and authorized for the relevant work; do not issue calls merely to fill a dashboard or manufacture a quality score.

## Dashboards and integration proof

Expose component drill-down plus the whole-run summary, correlated by run ID. Keep the mandatory operational table, a component coverage table, evaluation results with provenance, and separate execution/research-quality/telemetry-health statuses. Unknowns stay null/UNAVAILABLE; dashboard averages need real compatible eligible samples. Use authorized private artifacts and access controls; public examples are synthetic unless specific publication was authorized.

The implementation must state what is actually installed and tested: packaged instructions, a local harness, connected runtime adapters, and verified live end-to-end collection are different states. A skill/local helper cannot intercept all model/tool/server activity or install instrumentation for every user. Treat unconnected hooks, hosted usage/billing, final-response usage and remote RAM as explicit integration gaps. Claim complete component or whole-run coverage only against a declared inventory and observed runtime evidence; record the cutoff and missing upstream work. Actual serving-runtime integration requires its owner/source and appropriate access.

Retain only necessary operational metadata and approved redacted evaluation artifacts. Do not log credentials, raw prompts/responses, confidential research, personal identifiers, hidden reasoning or cross-user data. Use opaque IDs/hashes when company/artifact identifiers are themselves sensitive. Adding a third-party telemetry destination, persistent access or broader data sharing requires its own authorization; this contract does not authorize it.

## Bundled local implementation

Read `../tools/observability/README.md` for the installed SDK, schema definitions, synthetic replay/evaluation harness and verification boundaries. Its metrics integration uses the sibling `../tools/run_metrics/vera_metrics.py` through an explicit local module path; do not duplicate the metrics ledger or its billable events. Running the synthetic benchmark validates local contract behavior, not a real company analysis, a deployed host adapter, live billing, empirical calibration or all-user collection. Store generated live records only in an authorized private destination.
