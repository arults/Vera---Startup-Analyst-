# Crua selected issuer-identity review view v0.1.1

This is a read-only view over the immutable company register v0.1.0. It applies
one reviewed, hash-pinned finding: six selected native Republic Europe campaigns
can be attributed to Thermo Tents Limited, Irish registration 553249. The original
two company keys, six source round IDs, source memberships and records stay intact.

The six matches appear in 16 existing assessments across two source scopes. These
are 16 applications of six reviewed links, not 16 independent matches. A round's
identity result means issuer attribution only. Economic-round equivalence and the
broader identity pipeline remain unassessed.

## Use

Python 3.10+ on POSIX, standard library only. From a repository checkout containing
the unchanged baseline, original sources and existing native captures:

```sh
python research/company-register-v0.1.1/inspect_reviewed.py --root .
python -m unittest discover -s research/company-register-v0.1.1/tests -v
python -m unittest discover -s research/company-register-v0.1.0/tests -v
python research/company-register-v0.1.0/verify_release.py --root .
```

The CLI prints JSON and writes no files. It exits 0 for the exact verified view
and 2 for HOLD. There is no caller-supplied status, receipt path, target list or
approval flag. A missing, changed or mismatched dependency yields HOLD with no
verified rows; use the old inspector to see the unchanged original register.

## Output and unchanged values

Each selected assessment is returned as an `original` and `reviewed` pair. The
only differences allowed in `reviewed` are:

- `gates.identity`: `VERIFIED_ISSUER_IDENTITY`
- `gates.identity_qa`: `VERIFIED_SELECTED_MATCHES`

Original gate values and lineage IDs are carried in separate review metadata.
Every other assessment field remains identical, including economic-round, cohort,
funding-time-zero, taxonomy, outcome/follow-up, cross-platform and unresolved-reason
fields. Existing records are returned unchanged; jurisdiction strings and source
keys are not rewritten into a merged legal-company record. Completion stays
unclassified, completion counts stay unestablished, verified-complete/partial stay
null, and empirical promotion stays false. No outcomes, censor dates, rates, priors,
eligibility or production configuration are changed. No new observations are added.

## Frozen inputs and native-only evidence

The inspected repository snapshot is `e1991e3d924f44dbc3b7964c06c428c5f5af49ef`.
The unchanged baseline register's own source contract pins
`717e7be8f6ee672815f69ef8d8885ff9a555055d`; these are different provenance roles.
The implementation pins the original reader, artifact-hash manifest, source
contract, frozen Phase 1C policy and the corrected evidence-review files. It reuses
the unchanged reader over checked in-memory table bytes. It verifies all seven
original source files and checks selected logical CSV ordinals and row hashes.
Company-key assessment applications require their full relevant lineage set for
the assessed scope, not merely one matching round.

The required study-gate proof is the six original native archives already stored
under `data/phase1d/cp7/cycle-3/batch-0002/captures/`. Every run checks the 12 gzip
file Git blobs, compressed/raw/text hashes, and the native number/date/domain/
location/brand predicates. Four explicit issuer-name/553249(Ireland) anchors support
the combined native match for the two unsuffixed number fields. Missing native
proof cannot be replaced by Companies House or CRO material.

External registry findings in the evidence derivative are outside-study context.
No external registry file is opened, fetched or required by the gate validation.
The whole corrected derivative is byte-pinned for provenance; changing any of it
requires a newly reviewed release, even if the changed text concerns context.

`evidence/REVIEW_RECEIPT.json` supersedes the previous review's registry-dependent
rationale. Only the corrected v0.1.1 receipt is accepted. The old source review
remains historical and is not an alternate admission route. SapientX is outside
this allowlist. No JEV was called for this implementation.

## Review scope and portability

Only this new directory is the proposed additive implementation. The baseline,
source CSVs and native captures are dependencies already present in the repository;
they are not copied into the new release. Raw HTML/PDF/XML/images and token-bearing
captures are excluded from its publication set. Existing historical source files
may be read locally but are never emitted by the view. There is no network access,
new data collection, application to canonical tables or plugin/global version bump.

The tests exercise exact two-field differences, original preservation, repeated
read-only execution, stale/missing evidence and sources, attempted self-approval,
mutated policy/IDs/ordinals/rows, incomplete company lineage, and symlink/FIFO holds.
The independent implementation review is separate from the source review.
