# Selected identity-source cutoff guard

Selected scoped claims can depend on identity.evidence_source_ids as well as predicate evidence. The scoped report now holds release when an explicitly linked identity source has an exact retrieved_at instant after the report day in UTC, or a publication_date/as_of_date after that calendar day. Missing source references still hold; malformed exact timestamps and dates still reject. A future source outside the selected dependencies does not block the chosen scope. Identity-only sources do not become predicate corroboration, additional predicate publishers, or stronger predicate authority.

This is a report-time guard using the existing exact source fields, not a general retrieval-window model or a new historical-availability estimator. It does not infer source truth, authenticate reviewers, certify identity mappings, or turn unknown retrieval into a date. It preserves source-local publication/as-of calendar labels and compares retrieval instants in UTC.

## Reporting limitation

known_by_retrieval and freshness remain predicate-evidence projections. An identity-only source retrieved later, or with missing retrieval, does not update those fields. They must not be interpreted as all-dependency historical knowability or earliest public availability. A source assertion can remain ACCEPTED_ATTRIBUTED_OBSERVATION while the cutoff guard keeps its release_status UNRELEASED_RESEARCH_OBSERVATION.

The overall scope's reviewed origin groups cover selected fact and identity sources; this is not a per-event corroboration count or calibrated independence measure. The identity guard does not alter that existing scope contract.

## Portable regression

Run unittest discovery for tests/test_identity_source_cutoff.py within this package. Tests use the existing public synthetic fixtures and test-only reviewer registry. Negative cases deliberately pair synthetic earlier reviews with future identity-source metadata to verify that signed-off assertions cannot waive executable cutoff checks; they are not genuine historical reviews or new evidence. Four production release assertions fail before the repair and pass afterward. Controls cover UTC boundaries, an unselected future source, missing/malformed references and dates, missing retrieval, and unchanged predicate authority/freshness/known-by projection.

No estimator, native outcome, denominator, rate, probability, numerical prior, policy, real input or real reviewer authority changes.
