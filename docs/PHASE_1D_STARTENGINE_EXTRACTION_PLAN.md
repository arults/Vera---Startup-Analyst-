# StartEngine Extraction Plan

Date: 2026-10-17

## Target
StartEngine Capital LLC, CIK 0001665160, Form C / C-U filings 2020–2022.

## Steps
1. EDGAR company search filtered to Form C and Form C-U.
2. Extract issuer legal name, accession number, filing date, and (where present) funding amount from C-U.
3. Emit discovery RoundRecords with discovery_flag = "edgar_cik_search".
4. Apply multi-source rules and identity resolution before any outcome labeling.
5. Store content hashes of the primary EDGAR XML/HTML.

## Hypothesis
H6: A systematic EDGAR parse of intermediary CIK 0001665160 will produce a usable 2020–2021 Layer B discovery cohort comparable in structure to the Phase 1B Wefunder manifest.

## Current status
Skeleton exists. Real parse pending network/EDGAR access.
