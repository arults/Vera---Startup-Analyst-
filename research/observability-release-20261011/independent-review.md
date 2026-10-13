# Independent review: Vera run metrics v0.1.0

Reviewed source SHA-256: `624f781a0f547b96a9e370d0893d2aae255b6af5bdbef01db45cec89e91075ab`

Verdict: no remaining blocking findings for publication of the local utility and output contract. This verdict does not certify a live runtime integration or automatically complete capture for all users.

## Verification

- 79 package unit/integration tests passed.
- 26 independently written synthetic checks passed.
- Regenerated synthetic JSON, Markdown and HTML examples match checked-in artifacts byte-for-byte.
- Root skill amendment preserves the preexisting original bytes. Active main skill/template changes preserve preexisting research, calibration and return-review requirements.
- Contract schema and lifecycle event names align with the executable implementation.

## Independently checked behavior

Unknown/partial data remains null or an explicitly scoped subtotal; cached input is not added twice; known inclusive totals survive unavailable cache splits; duplicate event delivery is idempotent; conflicting events and cross-run provider-request double attribution fail closed; real retries remain distinct; inclusive usage rollups are rejected; complete capture cannot contain open attempts; partial charges cannot become complete bills; cached pricing is not charged twice; negative/non-finite measurements fail; wall time differs from summed concurrent work; resumed pauses count in elapsed latency; pending runs have no completed latency; data cutoff differs from closure time; RAM peaks are scoped and never summed; model versions and pricing denominators are separated; final-response exclusions are visible; unsupported raw-payload fields are rejected.

## Boundaries

All evidence above is synthetic/local. No real company analysis, hosted model usage receipt, final-response serving hook, all-user interception, remote model/GPU RAM or live provider billing was verified. Runtime callers must supply truthful metadata, exclusive attribution, complete scope claims, approved storage and actual usage. Identifier restrictions are not a general-purpose secret scanner. The utility has no telemetry network destination.

Final display check: partial cost cells retain billed versus estimated basis, with no changes to arithmetic or schema.
