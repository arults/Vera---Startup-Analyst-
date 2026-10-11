# Phase 1D identity CI: dependency repair and isolated candidate replay

## Observed failure and separate latent hazard

The identity-review workflow at commit `f909af945c5b027204d02729bb6357278f5a2eaf`, run `38119213688`, job `114410278315`, discovered 339 tests and stopped with two import errors: the CP9 and closure-audit tests could not import `bs4`. There was one optional archived-replay skip. That failed run did **not** reach the producer or commit steps. This was a dependency-install failure, not evidence of a statistical failure.

The old success path had a separate persistence hazard: it checked out the mutable `phase-1d` branch, regenerated canonical-named artifacts in that checkout, and automatically committed/rebased/pushed selected CSVs and JSON files. Its fixed upload list omitted the new content-addressed bootstrap full-draw sidecars. Merely adding the missing dependency would have enabled this unsafe success path.

## Scoped correction

The existing identity-review workflow now:

1. Checks out `${{ github.sha }}`, disables persisted Git credentials, and verifies the triggered commit. Its GitHub permission is reduced to `contents: read`; there is no commit, rebase, or push stage.
2. Installs the already-established regression dependency set: `requests beautifulsoup4 curl_cffi`, using binary distributions. This is the set declared in the existing identity-dependency-validation workflow; there is no root requirements file to install.
3. Exports the exact triggered commit to a new disposable directory outside the original checkout. Every tracked regular file is checked against its Git blob and executable bit. Unsupported symlinks, gitlinks, LFS pointers, omitted export-ignore files, or export-subst byte changes fail closed.
4. Runs the full `unittest discover -s tests -v` suite in that exported tree, with bytecode writes disabled. A test failure or any file mutation by tests blocks all producer stages.
5. Runs the same four unchanged scientific producer modules in order, with the isolated tree as their working directory and no inherited Python import-path override. Their hardcoded paths resolve inside that isolated tree.
6. Requires all 16 checkpoint outputs and both referenced content-addressed bootstrap sidecars. It verifies source/output hashes, CSV-to-audit bindings, exactly three endpoint report IDs per row, full audit report coverage, sidecar hashes, report line indexes and metadata, retention of all executed draws, and explicit declarations for genuinely not-run draws. No draw is silently discarded. Candidate-only/non-promotion flags remain required.
7. Rejects deletion of any exported tracked file or mutation of any file outside the explicit checkpoint outputs and bound sidecars. Checks the original checkout's complete file-byte and executable-bit inventory in `finally`, including when a stage fails.
8. Uploads **only** `evidence/validation.json`, containing commit identity, status, and hashes. It never uploads raw source data, company identifiers, candidate CSVs, per-draw records, or the private audit manifests. The complete raw candidate and sidecars remain together in disposable runner storage and are discarded when the job ends. A separately authorized publication process is needed for durable raw outputs.

The helper deliberately keeps the original scientific producers unchanged. The local identity application is a replay of archived deterministic review dispositions, not a new external JEV call. Inspection of the four producers and their local dependencies found no network calls, service clients, credential operations, or unguarded producer calls at import time. The historical Jev labels and probability literals are preserved, not re-evaluated. No private study data or source code is submitted to JEV.

This is an isolation/integrity guard for known repository code, not an operating-system security sandbox. It does not confer authorization for future external service calls, data disclosures, empirical promotion, or canonical checkpoint replacement.

## Verification and limits

- Synthetic regressions exercise exact-head enforcement; byte-preserving isolated export; unmodified original files; full-test execution; test and producer failures; unanticipated source mutations; omitted/corrupt sidecars; stale CSV report IDs; missing output/source/audit hash inventories; missing report coverage; not-run declarations; truncated/duplicate draw indexes; symlinks; export-ignore behavior; and no writer/raw-upload workflow path.
- YAML parsing and shell syntax checks are recorded in the local review evidence.
- The unchanged candidate estimator was run on a separate copy of the available 952-row v4 ledger. Its actual emitted CSV/audit/full-draw chain passed the new verifier, including declared not-run cells. This is a caller integration check only, not a local full identity rebuild or empirical promotion. Those private replay outputs are excluded from this patch.
- A complete repository checkout was unavailable locally. The entire repository suite and all four identity producers must still pass on the published exact head in CI. An optional archived-replay test may remain skipped unless its authorized fixtures are supplied. No tests were weakened or removed.

No empirical rates, priors, RQ1 scientific definitions, RQ2 gates, company identities, frozen source files, or archived scientific checkpoints are changed by this patch.
