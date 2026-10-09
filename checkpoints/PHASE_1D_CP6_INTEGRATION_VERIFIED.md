# Phase 1D CP6 — Integration verified

Date: 2026-10-09. Execution increment: 0.6.1-dev.audit.1.
Status: REPAIR INTEGRATED AND VERIFIED; RESEARCH INCOMPLETE; GLOBAL RESEARCH PLATEAU NOT DEMONSTRATED.

This receipt supplements, without rewriting, PHASE_1D_CP6_STOP_GATE_AUDIT.md. It resolves the earlier FULL CI PENDING status only.

## Verified execution

- Baseline: 122c869911d838a8ed77e71b893b8e0104a1dd95.
- Tested repair commit: b08c26c07e0ada61c5f048e1612cb95fb8ea4346.
- Workflow: Phase 1D replay audit and research stop guard.
- Run: 37905828468; job: 113738925358; attempt: 1; completed successfully on 2026-10-09.
- Full repository regression: 218 tests, all PASS, no failures. This count is read from actual downloaded tests.txt, not extrapolated from prior counts.
- Existing scientific verifier: 43/43 PASS; rates_promoted=false.
- Historical-snapshot audit: replay_stable=true; research_plateau=false; status=PLATEAU_NOT_DEMONSTRATED. Sole reason: two_substantive_iteration_receipts_required.
- CI artifact: 11604790649, phase1d-cp6-audit-37905828468-1. Downloaded successfully and SHA-256 matched GitHub's declared digest.

Artifact ZIP SHA-256: 86222f85982f94697a3678350c4ae9e6e1688b2da599d55daae2a6ed7517b28e.
research-stop-report.json SHA-256: 78f5daccaa577ef16676f0b7ecd12bdd8899094702b06e6eccd5eeb8ad73082d.
scientific-verifier.txt SHA-256: 41abef6b5c290fcaa6a476fc5e3449a0d708c7488f96e8e4029d760afda6a20d.
tests.txt SHA-256: ef1ace8504501776df8ca5b362d574946bfd93764cf5d6b107ad3c23efb6d79d.

The CI artifact has an expiry (2027-01-07); its downloaded copy is included in this conversation's audit deliverable. Repository code, checkpoints and source data remain durable Git objects, not dependent on CI artifact retention.

## What the feedback loops achieved

Three build/rebuild iterations closed replay-only acceptance, regression acceptance, overwrite behavior, artifact rebinding/synthetic-evidence loopholes and symmetric missing-schema checks. The local suite grew 22 -> 32 -> 35 -> 39 tests. Two distinct later challenges found no additional defect within their tested scope: 10,000 seeded comparison cases and 38 required-receipt/evidence-field removals. Full integration then passed 218 tests and 43 scientific checks.

This supports ending this bounded engineering repair cycle. It is not proof that all public-source research alternatives have been exhausted.

## Final Jev evaluation

Model: jev-1.13.0.
- checkpoint_state: repair_integrated_verified_research_incomplete; selected probability 1.00, confidence 1.00.
- repair_stop_scope: bounded_engineering_stop_only; selected probability 1.00, confidence 1.00.
- promote_numerical_prior_now: yes probability 0.05; no promotion.
- merge_to_main_now: yes probability 0.05; no automatic merge.
Full returned answers are preserved in evidence/jev/PHASE_1D_CP6_FINAL_DECISION.json. These are model judgments, not calibrated empirical probabilities.

## Preservation and outstanding research

Git compare of baseline to tested repair lists only the ten intended code/test/workflow/memory/additive-audit paths. No data/, reference_classes/, VERSION, historical checkpoint, or previous decision file was modified. The old SKILLS file is also preserved byte-for-byte as an additional historical file.

No startup observations were added in this correction. Republic Europe remains 952 normalized / 796 year-eligible with 63 total qualifying follow-ons (55 eligible per the earlier detailed log), low-information outcomes and no promoted Phase 1D prior. Wefunder, Republic US, StartEngine and Crowdcube historical censuses remain incomplete. Further empirical work requires a materially different admissible source, authorized historical export, newly available platform-hosted dated outcome evidence, or changed access conditions. Unchanged blocked retries and synthetic engineering fixtures do not count as research iterations.

Main and the promoted reference-class registry were not changed. Resume from this receipt and the retained data, not from the old replay-plateau declaration.
