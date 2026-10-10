# Prospective collector timing requirement

Before each future authorized source request, record request_started_at from the live collector clock. Immediately after the returned result, record response_received_at from the live collector clock. Preserve the exact request, response/receipt hash, timezone and those two timestamps as an observed execution window. State whether timestamps came from the collector, service, response headers or a later observation; do not equate them.

Keep publisher event date, publication date, publisher as-of/effective date, collector request/response window and any known server retrieval timestamp separate. A response completion time can be stored as a collector-retrieval-completion observation when explicitly labelled. It does not reveal when the publisher's content changed, when the underlying event happened or what the server clock said.

When the tool does not expose an exact time, preserve null with explicit missingness plus any genuinely supported bounded execution window. Do not retrospectively fill seconds from later conversation clocks or local review time. Observed completed-by markers are supplementary provenance, not exact request timestamps. Re-reading an archived receipt is offline inspection, not a new source fetch.

Implementation 1.0.2 accepts receipt-bound intervals under policy 1.1.0. Every asserted boundary must match exact archived receipt bytes and a locator. Distinct start and completion receipts may establish the two bounds. Required chronology must follow even under the worst-case bounds; overlap or an absent lower bound holds. See SCOPED_SCHEMA.md. Never alter historical missing data to make a gate pass.
