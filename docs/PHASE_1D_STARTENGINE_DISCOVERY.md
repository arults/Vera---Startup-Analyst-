# StartEngine Discovery Notes

Date: 2026-10-17

## Intermediary
- StartEngine Capital LLC
- CIK: 0001665160
- File Number: 007-00007
- Role: Funding portal for Reg CF offerings.

## Known context
- As of March 2021: acted as intermediary for ~585 Reg CF offerings; companies had raised ~$297M across types.
- 2020 platform-reported company raises ~$147M (context only, not row-level).
- FINRA $350k fine (2022) for 2016-2018 supervision issues (platform-level bias item).

## Next extraction steps
1. EDGAR company search for CIK 0001665160 filtered to Form C / C-U filings 2020-2022.
2. Extract issuer name, accession, funding amount from C-U where available.
3. Convert to discovery RoundRecords with discovery_flag = "edgar_cik_search".
4. Apply multi-source rules before any outcome labeling.

## Hypothesis for next cycle
H3: Systematic EDGAR Form C search on intermediary CIK will yield a usable 2020-2021 StartEngine Layer B discovery cohort comparable in structure to the Phase 1B Wefunder manifest.
