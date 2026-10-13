# Republic Europe caller bootstrap support safeguard

## Scope

This is a reporting safeguard in `src/phase1d/estimate_republic_europe_candidate_v3.py`. It does not change the frozen cohort, source predicates, event clocks, point estimators, collapsed-terminal KM operating target, company resampling, seeds, horizon support definition, RQ2 gates, or promotion status. It does not adopt a new multistate estimator or claim that the existing empirical endpoint fully implements the study's frozen scientific target.

Each generated company-cluster draw is retained in its original order, including duplicated cluster rows. The caller evaluates the existing landmark support rule separately on each resampled endpoint history. For operating survival, that is the same terminal/censor history consumed by its existing KM point function. A first-success event is not an operating terminal event.

## Interval disposition

The point estimate is unchanged. The primary percentile interval is withheld when the full sample lacks landmark support, any draw has an undefined/nonfinite statistic, any draw lacks numerical support, fewer than two replicates ran, or the finite distribution is degenerate. No draw is deleted, replaced, redrawn, or given a new weight. Unsupported but finite mathematical values remain in the full audit record; they are not treated as valid supported uncertainty.

For supported, defined, nondegenerate draws, quantiles use the original `src.phase1c.estimators.percentile_interval`: clamped discrete order-statistic indices `int(B*alpha/2)` and `int(B*(1-alpha/2))-1`. There is no switch to linear interpolation. The interval status explicitly disclaims a nominal coverage guarantee. This policy addresses a reporting hazard; it does not prove frequentist coverage or repair informative censoring, source uncertainty, or endpoint mapping.

Zero observed events and primary-unestimable cells retain their existing caller behavior: no bootstrap is scheduled. Zero requested replicates and fewer than two company clusters are explicitly not run. These cases have null unobserved support/undefined/degeneracy counts, not fabricated zero failures. Configured replicate count and not-run count remain visible. Support and statistic-defined counts are separate classifications and may overlap. A degenerate draw count is the number of completed draws only when all completed statistics are defined and identical; it is null if any statistic is undefined.

## Compact CSV and full evidence

`rq1_rows(ledger, bootstrap_audit=reports)` adds compact per-endpoint counts, statuses, original seed, and a relative report ID. The optional mapping receives all full reports. The pure function has no filesystem side effects. Without a supplied mapping, compact report IDs identify the reports conceptually but do not claim persisted evidence.

`main()` writes the full reports through `write_bootstrap_audit` and binds each CSV row to:

- relative audit-manifest filename and its SHA-256;
- relative gzip JSONL artifact filename and its SHA-256;
- per-endpoint report IDs resolving to the manifest's line-number index.

Each JSONL line stores one endpoint report, including every sampled source-row index, source round/company identifier, mathematical value or null, support status, statistic status, and failure reason. JSON rejects nonfinite values. The manifest binds the ledger and relevant implementation/dependency hashes.

Artifacts are content-addressed and serialized before publication. Identical writes are byte/mtime no-ops. A conflicting pre-existing content address is rejected; changed contents receive new filenames and preserve prior evidence. New artifacts publish atomically without replacing files. The old main CSV/summary writes and timestamped run manifest keep their existing behavior; whole-main byte or mtime idempotence is not claimed.

Full audit artifacts expose source identifiers and inherit the ledger's access requirements. Do not commit or share actual-ledger sidecars merely because the implementation and synthetic tests can be published. The code does not inline the large draw arrays into the CSV.

## Verification

Synthetic seed-71 control: three companies, one early success, one censor at six months, and one followed through 24 months. The full sample supports month 12, but 257 of 1,000 original bootstrap draws lack residual-tail support. All 1,000 draws remain visible and the interval is withheld.

Regression controls cover all three endpoints, complete modeled absorption, full-sample gaps, undefined/nonfinite and arithmetic-failure draws, empty/single-company cells, zero/one replicates, invalid arguments, repeated company multiplicity, exact legacy quantiles, no input mutation, portable artifact references and hashes, immutable sidecars, malformed JSON, and isolated main-to-CSV evidence binding.

Run synthetic tests from repository root:

    python -m unittest discover -s tests -p 'test_reporting*.py' -v

The existing optional archived replay is supported through `VERA_REPORTING_REPLAY_LEDGER`, `VERA_REPORTING_REPLAY_RQ1`, and `VERA_REPORTING_REPLAY_RQ2`. It compares exact archived legacy-column bytes and ordering while explicitly validating the additive diagnostic schema. No private replay ledger is bundled with the new tests.

Local reconstruction verification on 2026-10-11 passed 47 tests with the optional 952-row replay enabled. Separate pinned v4 and v5 replays retained 13,000 and 16,000 completed draws respectively; all completed draws were supported and defined, with legacy RQ1 values and all RQ2 outputs unchanged. These checks did not discover a new actual-cohort failure or promote an empirical rate. The safeguard fixes the demonstrated synthetic reporting hazard.

## Reconstruction provenance

The old unpublished candidate could not be recovered exactly. This is a newly reconstructed successor based on published estimator blob `7951b14aaf39f15552d076f16654e08c860a0ae1` (SHA-256 `62bdd5d4fa11a0c3ba32c08d1f04e7f078f83532d9fbb724ad1029e69b848612`), with the surviving prior transformation used as a reference. It must not be represented as the old candidate with the same artifact identity. Fresh independent verification applies to the new candidate.
