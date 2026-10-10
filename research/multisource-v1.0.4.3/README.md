# Customer observation engine: 1.0.4.3 public delivery candidate

This versioned local candidate adds selected-identity source cutoff validation while preserving the prior UTC-day correction. Read [IDENTITY_CUTOFF_CHANGE.md](IDENTITY_CUTOFF_CHANGE.md) for the required field-scope limitation: known_by_retrieval and freshness summarize predicate evidence, not all dependency history or earliest public availability. Unknown identity retrieval dates stay unknown; overall reviewed origin groups are not per-event corroboration. The earlier correction is documented in UTC_CUTOFF_CHANGE.md. It has not been published by preparation. The runtime identifier is 1.0.4.3-customer-local.

The extension represents customer_project_observation and customer_product_use without treating installed-equipment use as issuer operation or survival. Read CUSTOMER_OBSERVATIONS.md and POLICY.md. Event time remains unknown; source publication dates are separate. Native outcomes, censor dates, financing, returns, estimators and numerical priors are not promoted.

Run with Python 3.10+ and its standard library:

    python -m unittest discover -s tests -v
    python verify_package.py
    python evidence.py demo.json --as-of 2026-10-10

The portable suite discovers 191 tests: 190 pass and one native-pin availability test skips when original sibling archives are absent. Package integrity does not certify omitted native archives. The three unavailable native pins are explicitly reported.

The inherited public demo contains short public excerpts with genuine claim approvals pending. Synthetic tests simulate reviews and registries solely to exercise gates; they are not real approvals. Actual customer inputs, private original receipts, reviewer reports, operator registries and genuine approvals are excluded.

Exact policy requirements remain conditional admission gates, not a statement of the present review status of an external dataset. Use report()/CLI for validation and release gates, not internal adjudicate(). Automated validation cannot establish testimony truth or authenticate arbitrary names.

PUBLIC_ALLOWLIST.json identifies all intended delivery files. manifest.json binds every other file. lineage.json records the code/policy lineage without private review artifacts. This candidate adds selected-identity cutoff handling and version metadata; it makes no byte-identical report claim across versions. No external or JEV calls, publication, deployment or remote writes occurred during preparation.
