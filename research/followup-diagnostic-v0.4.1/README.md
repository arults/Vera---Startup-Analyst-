# Standalone follow-up temporal diagnostic 0.4.1

A read-only, local diagnostic with synthetic tests. It does not authenticate evidence, admit source records, choose censor dates, run an estimator, or modify canonical data. The implementation retains implementation_version=0.4.1-candidate and the existing v0.2 input/output schema identifiers; packaging does not rewrite accepted code.

## Run

No third-party packages are required. From this directory run:

    python -I -B -m unittest discover -s . -v

CLI:

    python -I -B diagnostic.py --input INPUT.json --output NEW_OUTPUT.json

The four Python files are byte-identical to the independently reviewed implementation and tests. The standalone package runs 78 synthetic tests, including inherited, temporal and review-regression cases. These are local package results, not additions to earlier GitHub CI totals. Existing top-level repository discovery does not automatically cover this nested package.

## Temporal interface

Each record adds evidence_report_temporal_diagnostic. Explicit source publication/as-of dates retain source-local calendar semantics; retrieval/review/witness timezone-aware instants normalize to UTC. The report date cutoff is treated as a full closed UTC day for these diagnostics only. This convention does not redefine source event times or establish a scientific cutoff rule. Missing clocks remain unknown. Activity points and periods remain separate; period endpoints are not observations, and an exact transaction day is not required for a bounded activity predicate.

Optional supplied_availability_witness contains observed_available_at (timezone-aware instant), claim_payload_sha256, review_ref_id (one complete matching supplied review) and a nonblank basis. The diagnostic cannot determine whether real evidence establishes the witness. Publication, activity, retrieval and review dates never manufacture a witness. historical_availability_cutoff may be omitted/null/not_requested; a requested cutoff without a usable version-bound witness stays unknown. An on/before witness yields only a conditional supplied-witness status. A later witness is unknown, never proof of prior unavailability or first availability. Date-only witness values are invalid instants; no midnight or timezone is invented.

project() verifies no files. run() additionally verifies declared dependency bytes. Hash equality and a supplied review reference bind only an opaque original-claim payload and structural linkage. They do not authenticate source truth, reviewer authority, business entity, publisher, source version or historical availability. Both temporal diagnostics explicitly report entity_source_binding_evaluated=false. Detailed holds remain authoritative; top-level evaluated flags do not mean full-report validation or admission. Semantic claim review, real-record validation and historical investment backtesting are outside scope.

## Pre-release corrections

The earlier 0.4.0 proposal was held before release. In 0.4.1, availability-witness instants are also compared independently against the report cutoff, even without a historical request or with invalid witness binding. UTC normalization beyond the representable calendar range produces an explicit unrepresentable_UTC_date hold instead of an uncaught overflow. Opaque entity/source linkage is explicitly unevaluated. These corrections concern local proposal behavior; they are not discovered scientific outcomes or adopted estimator changes.

## File and disclosure limits

Explicit dependency file references are not sandboxed by this API. CLI output can contain resolved local paths, supplied claim content and review/input metadata. Use inputs you are authorized to read, and separately review any real output before sharing. Existing output files are rejected rather than overwritten. This package contains synthetic tests only: no real-record output, source body, private receipt, review artifact, model-evaluation payload or private binding file. A hypothetical model preference is not empirical validation or implementation approval.
