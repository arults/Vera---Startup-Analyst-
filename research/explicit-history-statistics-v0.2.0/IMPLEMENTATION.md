# Explicit-history statistical reporting candidate

**Synthetic-only additive implementation. No actual study records, empirical rates, or promotion.**

This packet combines the explicit-history independent-state occupancy engine, the separate first-qualifying-success CIF component, an estimator-specific analytic uncertainty diagnostic for operating occupancy, and matched company-clustered bootstrap/reporting. It advances inherited implementation obligations without changing the frozen study target or selecting an empirical source/clock convention. `FIRST_SUCCESS.md` documents the first-success semantics, component limitations and predecessor tests.

## Execute

Python 3.10 or later, standard library only. From the parent directory:

    python -m unittest discover -s frozen-statistical-reporting-candidate-v1 -p 'test_*.py' -v

From inside the directory, use `python -m unittest -v`.

All 51 tests pass. This includes 500 exact-rational occupancy matrix comparisons, 800 fully observed first-success checks, and 180 synthetic IJ landmark configurations with round-by-round central finite-difference comparison, covariance checks and conservation identities. Tests do not load actual study records. No R runtime or third-party statistical library was used; this is not an R-validation claim.

## Analytic construction

`aj_ij_diagnostic` uses the same equal-round empirical initial-state distribution and AJ product integral as the occupancy component. The point target remains the supplied economic-round population. At all input round weights equal to one, it differentiates:

1. Initial state proportion: p_s = sum_j w_j I(initial_j=s) / sum_j w_j.
2. Every state-specific transition hazard: dA_ab = sum_j w_j I(transition_j=a→b at t) / sum_j w_j I(j at risk in a immediately before t).
3. The complete product-integral recursion with the product and quotient rules, including the initial-distribution derivative.

Let g_j be the vector derivative of state probabilities with respect to round weight j. For company c, G_c = sum of g_j for its rounds. The uncorrected infinitesimal-jackknife covariance is sum_c G_c G_cᵀ. No n/(n−1) or company-count finite-sample correction is applied. The operating variance is sum_c (G_c,pre + G_c,post)², computed as squared scores directly to avoid negative roundoff from covariance cancellation.

The official R survival documentation provides reference context for explicit initial distributions, AJ state probabilities and company/cluster influence aggregation: https://search.r-project.org/CRAN/refmans/survival/html/survfit.formula.html . This packet implements and verifies its own derivative recursion; it does not claim byte-for-byte R equivalence or numerical comparison to R.

## Interpretation and interval behavior

The diagnostic is assumption-indexed: correctly mapped histories, an appropriate censoring/observation model for the declared target, and independent company clusters under the relevant sampling interpretation. Within-company observations are grouped. Neither the covariance calculation nor company grouping establishes that a selected source frame represents the target population, corrects informative missingness, or resolves ambiguous entry state.

When not withheld below, the operating interval is a normal delta diagnostic, point ± normal quantile × IJ standard error, clipped to [0,1] for bounded presentation. Clipping is not a coverage correction. The interval is neither exact finite-sample 95% coverage nor simultaneous coverage; small samples, sparse states and boundaries can perform poorly.

The reported normal interval is withheld for:

- a detected current or previous numerical operating-state risk gap;
- fewer than two company clusters;
- a zero IJ variance or boundary operating point.

These conditions retain mathematical probabilities, derivatives, covariance and reasons as diagnostics. Zero variance is not evidence of no outcome uncertainty, and an unavailable diagnostic is not a zero-width informative confidence interval. The support flags do not claim source adequacy merely because no numerical gap was detected.

The primary company-cluster bootstrap interval is separate from this analytic diagnostic. The matched reporting wrapper below compares them only when both are available for the identical inputs, endpoint, horizon and confidence level.

## Important target boundaries

All five explicit initial occupancy states are accepted, including terminal states with no outgoing transitions. The implementation never drops funded rounds because they are non-independent at entry. First-success history requires separate explicit baseline-success meaning; terminal occupancy alone does not establish whether success occurred earlier. It rejects that unresolved first-success input rather than silently discarding the round or changing the target.

Current post-success occupancy is not ever-success CIF. A first success followed by closure stays a first success. The first-event competing CIF is not a full closure CIF. Unknown-value acquisition is not automatically success. Initial POST baseline qualification is distinct from an incident PRE success at time zero, and the incident contribution is normalized to all supplied rounds.

Times must be exact, nonnegative, finite, and common-scale. Intervals, delayed entry and ambiguous same-subject simultaneous transitions are not silently converted. Ordinary implementation of the frozen target requires no new target-selection permission; actually unresolved source, clock and event-history meanings remain dependencies for the affected empirical claim.

## Preservation and remaining work

`MANIFEST.json` binds the code, tests, result log and documents. `SOURCE_BINDINGS.json` records source/precedessor hashes without private records. The packet is self-contained and public-safe. All earlier candidates remain unchanged.

No source admission, actual estimator run, canonical output modification, external read/write, third-party review submission, rates promotion or Phase 1D completion is asserted. Remaining original obligations include actual source-qualified histories and coverage, a full closure endpoint where applicable, empirical uncertainty validation, lost-follow-up assignment sensitivity, graph-aware analysis, and defensible empirical reporting. Correct conditional arithmetic does not supply those missing facts.

## Primary company-cluster bootstrap

`operating_cluster_bootstrap` draws the number of unique companies with replacement from the sorted company list, preserving every supplied round of each selected company occurrence. It uses the existing seeded sampler. Every generated draw is retained, with selected original company IDs, original round IDs (including multiplicity), mathematical occupancy, support status and any undefined-statistic reason. There is no deletion, redrawing, reweighting or conditioning on supported draws.

The point target and denominator remain equal contribution per supplied economic round. Resampling companies does not make the point equal-company weighted; repeated-company selections can change the total number of rounds in a replicate. The entire sample is evaluated using its explicit initial states and histories.

The candidate chooses the following conservative reporting policy, which is not claimed to be the uniquely mandated interpretation of the frozen specification:

- Zero requested replicates or fewer than two company clusters: bootstrap not run; unsupported/undefined counts and degeneracy are null, not misleading zero failures out of the requested number.
- A numerical state-risk gap in the full sample: retain all requested draws for audit, but withhold the primary interval even if some draws are supported.
- Any undefined or unsupported draw: withhold the interval; retain every draw and separate counts/reasons.
- Fewer than two completed draws: no percentile interval.
- A constant complete replicate distribution: withhold an informative interval and explicitly report degeneracy. This can arise from sparse or zero-event data, finite resampling, or genuinely identical observed outcomes; it is not proof of certainty.
- Otherwise report the empirical percentile interval, with confidence-level metadata and no assertion of nominal coverage.

A zero terminal-transition count is a separate landmark-specific descriptive flag, not a reason to skip resampling. Known mixed initial terminal/operating states can vary across companies with no post-entry transitions. Initial terminal count and total transitions through the requested landmark are therefore reported separately. No new n≥30 RQ1 suppression is imposed.

The default requested replicate count is 1000. Other explicitly supplied nonnegative counts are allowed; small finite B gives unstable quantiles, and neither B=1000 nor passed computational tests establish coverage. The interval quantiles use linear interpolation at position (B−1)q in the sorted complete vector, at q=alpha/2 and 1−alpha/2. This is an explicit numerical convention, not an undocumented order-statistic choice. Withheld runs do not compute an interval from a surviving subset.

The exception branch retains only declared arithmetic/value failures as undefined draws; other programming errors propagate instead of being silently hidden. A producer fault-injection test verifies undefined-draw retention without requiring an actual malformed empirical record.

## Matched primary-versus-analytic disagreement

`operating_uncertainty_report` evaluates the primary bootstrap and analytic IJ for exactly the same histories, operating-occupancy endpoint, horizon and confidence level. Its `disagreement_threshold` argument is mandatory. The original frozen study required material-disagreement reporting but did not prescribe a numeric threshold; this candidate does not invent one as frozen policy.

When both intervals are present, the report records the maximum absolute difference between their corresponding lower and upper endpoints and flags whether it strictly exceeds the supplied threshold. Equality to the threshold is not flagged. When either interval is unavailable, comparison is `NOT_COMPARABLE_INTERVAL_UNAVAILABLE`; the numerical difference and disagreement flag are both null, never false. Agreement does not establish valid inference, and disagreement does not itself identify the better method.

This wrapper covers operating occupancy only. Success/closure interval implementations, actual evidence mapping and population claims are not implied by these bounded additions. Existing first-success tests establish endpoint arithmetic, not complete uncertainty reporting for every frozen endpoint.
