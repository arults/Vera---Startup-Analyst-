# Implementation1.0.3.1local verification

The shared-version reporting fix passed130tests:126predecessor regressions plus scoped/unscoped version and declaration-lineage checks. Independent review checked the exact minimal runtime diff and reran129tests before the final declaration-lineage test was added; it also executed both old/new engines on the immutable actual input and found only implementation_version changed. Exact runtime hashes are in manifest.json.

Root cause: a duplicate scoped report-version literal escaped tests that only checked the unscoped path. Prevention: exercise all public report paths and check engine, manifest, lineage and publication metadata together. Passing a large test count alone did not detect this missing invariant.

Actual pilot data and approval artifacts are excluded from the portable package. Separately reviewed narrow findings do not enable estimators or numerical priors. Public demo remains held. Final private implementation external review is pending specific authorization.

Run python verify_package.py and python -m unittest discover -s tests -q. Original native archives are verified only when present; isolated distribution explicitly skips one unavailable-archive test. No source bodies/private receipts or reviewer approvals are bundled.
