# Report version and hash provenance

Both public report paths must emit implementation_version equal to evidence.IMPLEMENTATION_VERSION. scoped_review imports that constant; it has no separate hardcoded version. The report version is implementation metadata, not evidence policy or dataset version.

When fixing a report-label bug, recompute reports using the unchanged source input and reviewer registry. Compare complete parsed objects and record all changed fields. Never edit a persisted report label by hand. Preserve predecessor reports under their original hashes.

For 1.0.3.1, all scientific fields in the recomputed actual pilot equal the predecessor; only implementation_version changes from the erroneous output label1.0.2 to1.0.3.1. The actual prior engine was1.0.3. Actual pilot inputs/private approvals are not bundled. Public demo reports are freshly recomputed by this engine; historical outputs remain in predecessor packages.

Regression contract: tests/test_report_version.py checks scoped and unscoped output labels against the same engine constant. Policy version remains vera.multisource.claim-policy.v1.1.0 and exchange envelope remains vera.multisource.evidence.v1.
