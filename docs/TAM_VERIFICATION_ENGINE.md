# TAM Verification Engine — Multi-Method Market Sizing

Date: 2026-10-08
Status: **PROMOTE_METHOD** — Vera market-sizing methodology. Company-level TAM remains evidence-gated.

## Purpose
Vera must not output qualitative statements such as "TAM is large" or adopt a single market-research number as truth. TAM must be estimated, triangulated, reconciled and source-audited before promotion.

## Definition
**TAM = total monetizable demand for the defined product/category at a stated time horizon**, before applying company-specific execution constraints.

TAM is not:
- current sales capacity;
- current channel reach;
- current manufacturing capacity;
- current financing capacity;
- management's aspirational market figure.

Those belong downstream in SAM/SOM/REM or the causal execution model.

## Required TAM methods
Use at least **two materially independent methods** whenever data permit; one should be bottom-up when feasible.

### M1 — Bottom-up buyer/user/unit method
Eligible buyers/users/units × realistic annual category spend or price.

### M2 — Demand-event method
Eligible annual visits/transactions/treatments/events × monetizable value per event.

### M3 — Customer-budget method
Target buyer count × relevant budget pool/category spend.

### M4 — Competitor/category revenue triangulation
Aggregate or infer market size from comparable-company revenues, customer counts and defensible share assumptions.

### M5 — Top-down market reports
Use reputable third-party market-size studies only as a **cross-check/context source**, never automatically as the TAM anchor.

### M6 — Value-based reasonableness check
Estimate economic value created/cost avoided and plausible monetizable share. This is a sanity bound, not normally the sole TAM estimate.

### M7 — Eligibility filters
Where regulation, reimbursement, clinical criteria or technical applicability determine whether demand can exist at all, explicitly filter the eligible universe before TAM.

## Time indexing
Always distinguish current TAM from future TAM:
- TAM@current
- TAM@3y
- TAM@5y
or another explicit horizon.

Do not mix today's observed market and a forecast market into one number.

## Reconciliation
If methods disagree materially:
1. preserve the estimates separately;
2. inspect product/category/geography/unit/horizon definitions;
3. identify which input assumptions create the divergence;
4. reconcile only when the difference is definitional or evidentiary;
5. otherwise report a range and downgrade confidence.

Never:
- average estimates mechanically;
- select the highest number;
- select the lowest number simply to be conservative.

## Promotion gate
A TAM may be labeled **VERIFIED** only if:
- at least two materially independent methods are present, unless one genuinely authoritative exhaustive source makes another method impossible/unnecessary;
- one method is bottom-up when feasible;
- category/product definition is explicit;
- geography is explicit;
- unit and monetization basis are explicit;
- horizon is explicit;
- material inputs have provenance/evidence states;
- broad market reports are used as cross-checks;
- method disagreement is reconciled or preserved as a documented range.

If this gate fails:
- TAM status = **UNVERIFIED** or **UNCALIBRATED**;
- Vera must not say merely "TAM is large";
- use deterministic bounds and list the missing evidence.

## Verifier gates
- **T01** category/product definition explicit.
- **T02** geography explicit.
- **T03** monetization unit explicit.
- **T04** time horizon explicit.
- **T05** >=2 materially independent estimation methods when feasible.
- **T06** bottom-up method present when feasible.
- **T07** source/provenance attached to every material input.
- **T08** management/issuer TAM separated from Vera-derived TAM.
- **T09** third-party market reports treated as cross-check/context unless uniquely authoritative.
- **T10** regulatory/clinical/technical eligibility filters applied where they define whether demand exists.
- **T11** company execution constraints excluded from TAM.
- **T12** disagreement ledger retained; no silent averaging.
- **T13** dynamic growth assumptions separated from current TAM.
- **T14** TAM outputs reconcile with SAM/REM units downstream.
- **T15** failed gate => UNVERIFIED/UNCALIBRATED, never manufactured precision.

## Relationship to REM
TAM is the verified demand ceiling.
SAM narrows by product/geography/regulatory/serviceability.
SOM remains a conventional/context obtainable estimate.
REM is Vera's probabilistic execution-constrained revenue distribution by horizon.

Company-specific sales capacity, manufacturing capacity, channel reach and financing constraints belong in REM/causal execution, not TAM.

## JEV decision
JEV (jev-1.13.0):
- current Vera needs this upgrade: **0.92 yes**
- compatibility with Vera architecture: **0.92 yes**
- **PROMOTE_METHOD: 0.96**, confidence 0.95

Earlier JEV design decisions:
- multi-method triangulation required: 0.94 yes
- bottom-up should anchor when feasible: selected with probability 1.00
- third-party market reports should be cross-checks: 1.00
- disagreement should be preserved/rersearched rather than averaged: 1.00
- TAM should be time-indexed: 0.92 yes
- company execution capacity should be excluded from TAM: 0.93 yes
- regulatory/clinical eligibility can legitimately reduce TAM: 0.94 yes
