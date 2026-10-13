# Vera per-company operational metrics contract v0.1.0

Applies to every company-analysis or company-tracking update execution: SCREEN, STANDARD and DEEP DILIGENCE; single-company, comparison/directory runs, reruns, resumed work and terminal blocked/failed/cancelled work. This supplements all research, return-probability, review and calibration requirements. Operational telemetry is evidence about execution, never evidence that an investment conclusion is correct.

## 1. Capability boundary

A skill can require a ledger and an honest final table. It cannot intercept every host/model/tool call, read unavailable provider billing, profile remote hosts, or install collection across other users simply by being published. Distinguish:

- The required output/collection procedure in this skill.
- An actually installed and tested host adapter or explicitly supplied usage feed.
- Optional local event-ledger utilities that process events supplied to them; these are not automatic host instrumentation.
- Missing runtime support, which must be visible as unavailable or partial coverage.

Never claim system-wide automatic tracking without a verified runtime integration. Do not invent APIs, scrape internal session stores, infer hidden reasoning tokens, or issue extra model/JEV calls just to obtain a usage-looking number. Genuine necessary JEV/review calls belong in the ledger if metadata is exposed.

This procedure applies to every execution using this updated plugin within its existing authorized installation and audience. It does not change sharing, publish a public plugin, grant cross-user data access or assert that other users' hosts have installed instrumentation.

## 2. Start, scope and finish

1. At the accepted request / analysis start boundary, assign a unique opaque `run_id`, canonical `company_id`, depth, plugin/contract version, cache state and UTC start time. A batch also has a parent/batch reference; each company still has its own run. Do this before research, not from memory after finishing.
2. Check which runtime fields are actually available. Record collector/version, event source, included/excluded worker and tool scopes, billing coverage and process measurement scope. Record provider request IDs only when exposed and safe to store; never a credential or URL containing a secret.
3. Append stable event IDs and timestamps as work occurs. Include parent orchestration, attributable workers, required reviewers, failed attempts and retries. Each retry is a new attempt; replaying the same observed event is not new work. Deduplicate by event/attempt identity, not by identical prompts or company name.
   Pass company `run_id` and unique worker/attempt identifiers in delegated research/sourcing/verification/review tasks. Require children to return exposed events/usage with timestamps, measurement source, scope and unavailable fields; a child need not produce another full user report. Parent aggregation owns the final table. Preserve IDs when delivering the same event again and never sum an inclusive parent rollup with its constituent child records.
4. A continuation of the same analysis may resume the same run without erasing prior usage; a new independent analysis gets a new run linked to its predecessor. Preserve restart/retry history and distinguish a live snapshot from a terminal outcome.
5. Before the final answer, aggregate the available ledger and render the five-row table. State the exact observation cutoff and whether final-response generation is included. A host may expose final output usage only after it has sent the answer. In that case the in-answer table is explicitly a pre-response snapshot; finalize only through an actual supported completion hook or subsequent exposed usage. Do not assert final completeness early or keep calling tools forever to measure the last measurement call.
6. Preserve the machine-readable record in the current authorized private workspace when possible; otherwise disclose that the table is the only retained record. Never silently publish real company/user run logs to a public repository or dashboard.

If tracking starts late, report the actual start of instrumentation and missing earlier activity. A null is more honest than reconstructed precision. Capturing all available fields is required; inaccessible fields do not block delivery of an otherwise valid analysis.

## 3. Metric definitions and aggregation

### Tokens used

Report total billed/accounted model tokens across all attributable model calls plus input and output breakdowns where exposed. Preserve each provider's model/version, request/attempt ID, usage source and accounting semantics.

- Normalize whether provider input includes cached input. Cached input is a subset of normalized total input, not an extra addition to input plus output. An unknown cache subset remains unknown, not zero.
- Normalize provider reasoning/audio/other token semantics only when documented. Do not add a subcategory that is already included in an aggregate. Report incompatible or unavailable components separately.
- Include workers, reviewers, retries and failed-but-billed attempts whenever usage is available. If a tool exposes only its own response usage, that is scoped tool usage, not the parent or complete company run.
- Never add a parent's inclusive usage rollup to its children's exclusive calls. Use one authoritative representation for each underlying request and preserve excluded rollups for audit only.
- Known usage with missing requests is an observed subtotal with partial coverage. Missing all usage means `null`/UNAVAILABLE. Response length, context-window size and characters are not actual token usage. A tokenizer-derived estimate must be labeled estimated with its method and cannot recover hidden or unobserved work.

### Total tool invocations

Count actual dispatched tool attempts, including errors, timeouts, cancellations after dispatch and retries. Never count only successful results. Report distinct tool names separately; ten calls to one tool are ten invocations and one distinct tool.

Use a declared boundary. The default is leaf tool dispatches, excluding orchestration-only batch/wrapper containers to avoid counting a wrapper and its enclosed calls twice. A multi-query/multi-page request is one invocation unless the runtime actually dispatches separate tool calls. A JEV tool dispatch is one tool invocation; any exposed exclusive model usage may also enter the token ledger, without inventing internal calls. If the host only exposes top-level wrappers, state that different limited counting scope. A manual visible-call ledger may be accurate within its scope but is not evidence that hidden host/internal calls are included.

### Wall-clock latency

Use elapsed time from the accepted company-analysis request to report-ready at the final analysis cutoff, including actual waits, retries and parallel work. If only a later instrumentation/analysis start is observable, state that narrower boundary and the unmeasured earlier interval. Prefer monotonic elapsed measurements within one runtime; retain UTC timestamps for provenance. Record clock discontinuity or restarted-runtime limitations.

Do not sum worker/tool durations to obtain latency. Parallel five-second tasks can contribute ten worker-seconds while adding about five seconds of wall time. Optional active time and summed worker duration must have separate labels. A resumed run's end-to-end elapsed interval includes its pause; if active-session time is also reported, disclose the pause exclusion. For a batch, per-company intervals may overlap; their sum is not batch latency. A pre-response snapshot is not complete user-visible end-to-end delivery latency.

### Total cost

Report amount and currency. An actual total requires an authoritative billing/usage source covering all attributable model, tool and other billed work. A recorded charge for one service is only that service's known subtotal when other components are missing.

- Keep actual billed amounts separate from estimates. A mixed actual/estimated aggregate is an estimate or partial amount, never a fully measured bill.
- An estimate uses a dated/versioned rate card for the exact model/provider, cached versus uncached input, output, and any separately charged tool units. Keep rate source, currency, effective date/version and assumptions. Never silently use a current price for historical activity.
- Do not assume a subscription, included quota, unpriced tool, failure or cache hit costs zero. Confirmed zero is allowed only with complete applicable evidence.
- Add monetary amounts using decimal arithmetic; do not sum different currencies without a disclosed dated FX conversion. Costs and failed/retried attempts may be billable even when no usable answer is returned.
- Do not double count a bundled tool's inclusive bill and separately listed component charges. Shared batch costs remain in a separately identified unallocated batch bucket unless an explicit reproducible allocation rule and weights exist. A company's allocated share must be labeled allocated; company shares must not exceed the original charge.

### Memory used

The mandatory memory row means **peak RAM / resident set size in bytes or MiB, with the measured process/container scope**. It is not the model's context window, tokens processed or private notes/storage size.

- Only report an exposed process/container measurement with its identity, method, interval and units. A process-lifetime high-water RSS belongs to that process lifetime, which may include unrelated work; do not relabel it a company-run peak. An isolated analysis subprocess can improve attribution.
- A sampled maximum is a sampling-based lower bound on the true peak; disclose the sampling interval. A single snapshot is current RSS, not peak RSS.
- Do not sum independent process peaks as concurrent RAM. A process-tree/container peak needs time-aligned samples or a real runtime high-water measurement. Local helper RSS does not measure hosted model/server RAM.
- RAM unavailable in a managed host remains `null`/UNAVAILABLE. Optional context-token occupancy and persistent storage bytes can be separately named rows, each with scope and source; they never fill the RAM cell.

## 4. Status, coverage and final table

Every metric needs value/null, unit, measurement basis, scope, provenance and completeness. Measured/estimated and complete/partial are separate dimensions: an estimated number can also have partial coverage. The display may combine them as `measured · partial` or `estimated · partial`. No telemetry is `unavailable` with a reason. An actual observed zero is valid only when its stated scope is fully measured.

Use this minimum table for every company. A matrix with separate company/run columns is acceptable for compact comparisons if all five metrics retain coverage/provenance. A batch total alone is not enough.

| Metric | Value and unit | Basis / coverage | Scope and evidence |
|---|---|---|---|
| Tokens used | total tokens or UNAVAILABLE | measured / estimated; complete / partial / unavailable | input/output/cache breakdown, request/worker coverage and usage source |
| Total tool invocations | count or UNAVAILABLE | measured / estimated; complete / partial / unavailable | counting boundary, retries/errors, distinct tools separately |
| Wall-clock latency | seconds or UNAVAILABLE | measured / estimated; complete / partial / unavailable | start and cutoff, pauses, clock source, final-response inclusion |
| Total cost | amount + currency or UNAVAILABLE | actual billed / estimated; complete / partial / unavailable | billing source/rate-card version, included charges and missing components |
| Memory used (peak RAM/RSS) | bytes or MiB or UNAVAILABLE | measured; complete / partial / unavailable | process/container scope, method, interval and attribution limits |

State run ID, company, mode, run outcome, cache state and observation cutoff near the table. Preserve unknown numeric fields as JSON `null`, not zero, empty strings or the string `"null"`. Machine validation is structural evidence only; it cannot establish that reported telemetry is true or complete.

## 5. Dashboard contract and privacy

Dashboards must render all five metrics per company/run, retain unavailable/partial states and coverage denominators, and link only to audience-authorized evidence. Separate measured billed costs from estimates and local process RSS from hosted/runtime RAM. Filter or group comparisons by compatible depth, cache state, collector scope/version, model/version, pricing version and terminal run status; show sample count, metric-specific available/missing denominators, excluded/incomplete counts and currency. For compatible observed runs, show completion/failure rates, means and latency percentiles with their sample counts; never pool incompatible groups to imply comparable performance. Do not silently impute missing values into zeros, averages or percentiles. Wall-time trends must share the same boundary definition. A table/contract is not proof that a live dashboard or collection integration was deployed.

Store operational metadata only: opaque run/request/event identifiers, safe company identifier, tool/model names and versions, timestamps, counters, billed/estimated amounts and scopes. Never log or publish raw prompts, responses, documents, credentials, private user data, hidden reasoning or sensitive research merely for telemetry. If an identifier itself discloses confidential activity, use an opaque mapping stored privately. Public code repositories and examples use synthetic fixtures unless publication of specific real data was explicitly authorized. Keep existing plugin audience and access unchanged.

## 6. Event format and supported tooling

The bundled helper is `../tools/run_metrics/vera_metrics.py`; read `../tools/run_metrics/README.md` for its exact event schema, adapter integration, tests and CLI. From the skill directory, `python tools/run_metrics/vera_metrics.py report <authorized-private-ledger.jsonl> --output-dir <authorized-private-output-directory>` validates a supplied ledger and produces the table plus machine-readable/dashboard artifacts. The command does not collect undisclosed historical host usage, install a service or publish files. Use the no-telemetry table directly if Python or a ledger is unavailable.

The companion event schema is `vera.run-metrics/1` (contract release v0.1.0). `analysis_mode` uses SCREEN, STANDARD or DEEP (DEEP means DEEP DILIGENCE). It uses append-only events with stable `event_id`, `run_id` and UTC `at`, and `run_start`/`run_resume`/`run_end`, worker, attempt and memory events. Attempt IDs identify real attempts; retries get new IDs. Usage payloads are exclusive; parent inclusive rollups cannot be double-counted. The normative executable validation and exact optional fields are provided by the accompanying runtime utility when installed. This document does not claim the host automatically emits those events.

Validate and aggregate a supplied ledger before relying on a generated summary. Reject conflicting duplicate events, invalid cache accounting, negative/non-finite counters, mixed currency totals, inconsistent lifecycle ordering and unsupported schemas. Preserve incomplete attempts and absent usage as gaps. Retain the actual validator version and test result separately from claims about runtime integration. Synthetic fixtures demonstrate behavior only; do not present them as measured company-analysis runs.
