# UTC cutoff correction in 1.0.4.2

Aware claim-review and source-retrieval timestamps are converted to UTC before comparison with the UTC as-of day or calculation of retrieval age. Equivalent offset representations therefore receive the same cutoff decision. Naive timestamps remain invalid. Date-only event and source-publication labels retain their existing semantics.

This changes two temporal calculations and the implementation identifier. Existing authority, evidence, policy and scientific gates are unchanged. Reports carry implementation_version 1.0.4.2-customer-local; reports from the predecessor cannot be described as byte-identical after this metadata change. The additional tests use synthetic records and simulated review roles only.

This package does not authorize empirical estimates, customer-evidence admission, native outcome changes, or scientific model promotion. Source verification and genuine independent review remain required.
