# Read-only follow-up diagnostic 0.3.0: packaging proposal

This is a local, observation-only diagnostic packaging proposal for possible future publication. It is not a release, an authenticated review system or a production model. The implementation is 0.3.0; its existing input/output schema identifiers intentionally remain v0.2.

The code projects explicitly supplied judgments and temporal relationships without deciding whether a claim is true. Supplied judgments and reviewer identities are not authenticated. A matching file hash proves byte identity only; it does not prove claim truth, adequate inspection, semantic approval or complete review-to-claim binding. Missing or stale claim-reference holds remain distinct from successful artifact-byte verification.

Source-date versus evidence-report-cutoff consistency is explicitly unevaluated. Historical availability and dependency-coverage completeness are also unevaluated. No native censor update, last-positive update, estimator integration, rate, prior or production promotion exists. Unknown values and unresolved holds remain visible; outputs must not be used as automatic admission decisions.

## Standalone synthetic checks

Python 3.10+ and the standard library are sufficient. From this directory:

    python -B -I -m unittest discover -s . -p test_diagnostic.py -v

The exact synthetic suite contains 49 methods, including an actual CLI subprocess and byte-preservation checks. Fixtures are defined within test_diagnostic.py using synthetic assertions and simulated review references; they are not real evidence or approvals. No real pilot input/output, private review, registry, source body or credential is included.

## Interface and filesystem behavior

project(document) performs an in-memory projection and does not verify filesystem dependencies. run(input_path, output_path), or the CLI below, reads the supplied JSON and explicitly listed local bindings, checks their hashes and writes only a new diagnostic output path:

    python -B -I diagnostic.py --input input.json --output new-diagnostic-output.json

Supply an authorized input file and a new destination; the command does not create an input fixture. Existing outputs and output symlinks are rejected, and input bytes are checked for mutation. Input binding paths are resolved relative to the input file and are not a sandbox boundary. Only use documents whose declared local file references are authorized to read.

Diagnostic outputs can include resolved local file paths and input/review metadata. They are not automatically safe for publication. Inspect and sanitize outputs separately before sharing them; no real run output is distributed here. The code performs no network calls or remote writes.

manifest.json binds the other three package files. File integrity is separate from evidence truth or scientific validity. Fresh remote preflight, exact publication authorization and a separate public allowlist review remain necessary for any later publication. This directory has no CI or repository ingestion wiring.
