# First-success uncertainty v0.1.0

Additive, synthetic-verified component candidate for the existing explicit-history statistics package. Frozen files are unchanged. No empirical cohort adoption, coverage guarantee, source qualification or new prior is claimed.

- Whole-company percentile bootstrap retains every company occurrence, round and draw.
- Explicit targets: unconditional incident first-success CIF, or baseline-qualified fraction plus incident success. Neither silently becomes a conditional CIF.
- Analytic diagnostic differentiates the first-event product integral, including baseline mass, then aggregates round scores by company. It does not reuse operating-occupancy IJ.
- Unsupported tails, undefined draws, NOT_RUN, exact/numerical degeneracy, terminal-at-entry ambiguity and unavailable comparisons remain explicit.
- Reviewer-found extreme-confidence and full-success floating-point interval bugs are fixed; raw scalar/draw values are retained.

## Run and verify

Python 3.10+ standard library only; tested on Python 3.12. From repository root:

```sh
python -I -B research/first-success-uncertainty-v0.1.0/validate.py
```

The same command with an absolute script path works from any directory with `PYTHONPATH` unset. The runner verifies eight frozen source/test Git blob hashes against `dependency_bindings.json` before importing them from sibling `explicit-history-statistics-v0.2.0`.

**94 tests passed:** 51 frozen baseline + 30 new implementation + 13 independent review tests. This includes 960 randomized endpoint/horizon reference cases and 514 independently reconstructed bootstrap draws. This is one combined count; the separate 23 lost-follow-up sensitivity tests were not rerun here.

## Use

Add this directory and the frozen baseline directory to your Python import path, then:

```python
from first_success import InitialPostPolicy
from first_success_uncertainty import SuccessEndpoint, first_success_uncertainty_report

report = first_success_uncertainty_report(
    reviewed_exact_histories, 36, InitialPostPolicy.BASELINE_QUALIFIED,
    endpoint=SuccessEndpoint.INCIDENT,
    disagreement_threshold=0.05,  # explicit reporting setting, not an adopted cutoff
    n_boot=1000, seed=20261011, confidence_level=0.95,
)
```

See [METHODS.md](METHODS.md) for estimator derivation, endpoint semantics, gates, dependency hashes and limitations; [REVIEW.md](REVIEW.md) for independent findings and numerical verification. The proposed source-neutral CI workflow is `.github/workflows/phase1d-first-success-uncertainty-validation.yml`.
