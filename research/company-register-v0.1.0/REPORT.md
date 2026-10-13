# Imported inventory and research completion

## What this release establishes

All **2,865 rows in seven pinned source tables** are reconciled to a versioned,
additive company/round/evidence register. Source bytes and old outcomes remain
unchanged. The import does not establish the full accumulated repository population
or a final study population. No rates or numerical priors are promoted.

Full research-complete and partially-complete counts remain **unclassified**.
The original study's primary unit is economic company-round; it does not supply a
universal company-level completion rule. Existing metadata and prior source claims
are retained without converting them into new completion certificates.

## Platform inventory: keep the units separate

| Platform | Imported inventory | Interpretation |
| --- | --- | --- |
| Wefunder | 42 SEC-identified issuers and 42 frozen funded-2020 offerings; separately 57 native profiles with 65 candidate events; 46 discovery URLs | The issuer identities and frozen membership are retained. Profile/event material does not establish a unique economic round. The 42 issuers' overlap with the 57 profiles is unresolved. |
| Republic Europe | 789 source company keys and 952 source rounds | 783 keys are legal-number source identifiers and six are name fallbacks. Legal jurisdiction is not guessed. 796 rows / 676 keys have offering-year 2020–2025 in the source; remaining offering years remain unresolved. |
| Republic US | 568 native offering IDs; 108 discovery URLs | 363 offerings have a source year-in-study assertion. Canonical issuer/economic-round identity remains unresolved; linked CIKs are not automatically issuers. |
| StartEngine | 112 discovery URLs | Search discovery inventory only; neither verified companies nor an admitted cohort. |
| Crowdcube | 20 discovery URLs | Search discovery inventory only; neither verified companies nor an admitted cohort. |

These are overlapping inventory types and must not be summed into “total companies.”
The separately reported **985 retained Wefunder raw profiles were not loaded**:
this register imports the 65-event/57-profile candidate table, not the raw archive.
The candidate IDs were derived from that archive; a raw profile count is not a
verified legal-entity count.

## Preserved evidence

- The 42 Wefunder funded-2020 rows and issuer CIKs remain the frozen membership;
  inclusion does not assert completed outcome research.
- Europe retains all 952 normalized rows and all 952 v5 outcome rows, with the
  same source round and company keys. The original v5 observations remain
  950 `RIGHT_CENSORED_NO_CLOSURE_EVENT` and two
  `TERMINAL_ACQUISITION_VALUE_UNKNOWN_INTERVAL`. Unknown acquisition value is
  not success. The source's 370 eligible-evidence flags and 582 false flags are
  preserved assertions, not newly evaluated company-completion counts.
- Every imported row has a source commit, original-file SHA-256 / Git blob binding,
  logical-row hash, record links, and explicit disposition. Original complete
  assertions remain recoverable from their immutable source rows.
- No incompatible assertions were detected by this import's limited conflict
  checks. That is not proof that all identities, dates, or evidence are correct.

## Next research queue

1. **Identity reconciliation:** resolve the EU jurisdiction and six name fallbacks;
   validate Republic US issuer/coissuer links; establish overlap between Wefunder
   CIKs and native profiles. Keep ambiguous matches separate until evidence supports
   them. Preserve the frozen funded-2020 membership throughout.
2. **Economic rounds and cohort eligibility:** apply the original first-live-year,
   successful-close, instrument/terms, and co-host requirements. Separate discovery
   and candidate records from admitted study rounds; retain all exclusion reasons.
3. **Population strategy:** freeze the original accessible-deal/funded-layer census
   or a defensible sampling design for each platform/year. Imported availability
   alone is not a representative denominator.
4. **Outcome and follow-up evidence:** adjudicate platform-hosted typed outcomes,
   interval dates, affirmative last-positive evidence, and missing follow-up under
   the existing spec. An absent claim is not failure or closure.
5. **QA and reporting:** complete identity review and graph checks, then connect
   eligible rounds to the existing censoring, uncertainty, RQ1/RQ2, and scientific
   promotion gates. Report full completion only within an explicit evaluated scope.

The component matrix and unresolved reasons make this queue inspectable. They do
not replace the original requirements or assert that Phase 1D is finished.
