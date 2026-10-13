# Vera investor-return probability panel v1.0.0

A reporting contract for detailed theses: always show 10x, 25x, 50x and 100x investor-return thresholds at an explicit horizon. This package does not implement or empirically validate a return-probability model. Phase 1D completion is not established by this release.

Use docs/templates/detailed-investment-thesis-v1.md and docs/return-probability-contract-v1.md. Numeric final outputs require defensible inputs and both version-bound company-specific review gates. Missing evidence or pending review produces explicit NOT ESTIMABLE rows, not invented percentages. The abstention example is a non-company illustration.

Run from this directory:

    python -I -B -m unittest discover -s tests -p 'test_*.py' -v
    python -I -B tools/validate_return_panel.py examples/return-panel-abstention-v1.json

The validator checks declared structure, domains, nesting and release metadata. It cannot authenticate source evidence, verify that reviews really occurred, or establish calibration. Its test cases contain synthetic values for software testing, not company forecasts.

## Review and corrections

Two standalone JEV methodology evaluations and an independent code/method review informed this contract. No actual company calculation or private study data was evaluated by JEV for this release.

- Replaced ambiguous first-crossing wording with the cash ratio at the stated horizon.
- Made follow-on capital, fees counted once, security conversion, dilution and payout waterfalls explicit.
- Preserved missing/censored outcomes and required treatment of correlated financing, operating and liquidity paths.
- Closed an elicitation-only loophole for investor-return probabilities without changing unrelated legacy gate policy.
- Added a DRAFT/RELEASED distinction: structural acceptance cannot substitute for actual company-specific JEV and verifier PASS reviews on matching versions with no material blockers.
- Preserved honest abstention, no-return-model and no-empirical-validation statements.

At preparation, 22 regression tests and 23 additional independent adversarial checks passed. These are software/method checks, not 45 independent investment observations or proof of accurate probabilities. Remote publication and CI must be verified separately.

The SEC describes total-loss, illiquidity and limited-disclosure risks in private placements: https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/private-placements-under-regulation-d-updated-investor-bulletin . This context supports explicit cash-realization and evidence limitations; it supplies no 10x/25x/50x/100x probabilities.
