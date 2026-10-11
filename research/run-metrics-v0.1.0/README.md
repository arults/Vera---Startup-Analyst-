# Vera per-company run metrics v0.1.0

An additive, standard-library-only operational telemetry package. It does not change research observations, admissions, estimators, priors or scientific outputs. Python 3.10+; CI uses Python 3.12. All checked-in examples are synthetic.

## What is implemented

- An append-only, payload-free JSONL ledger with stable run, worker, attempt and event identities.
- Validated recorder and attempt context hooks for a caller that actually receives provider usage and tool dispatch events.
- An executable command-boundary adapter, which preserves the command's stdout/stderr and exit status and generates a report on success, failure or handled cancellation.
- Idempotent merging of worker shards; conflicting identities fail closed. Retries are separate attempts, including failures and cancellations that may incur cost.
- A mandatory per-company/per-run Markdown table, machine-readable JSON and a static HTML dashboard generated together.
- Matched aggregate groups with sample sizes, missing counts and descriptive statistics. Synthetic and live rows are separate.

## Honest integration boundary

Repository snapshot inspected: `486a773c8dfc5717a88020c765cd16cd4d147ec5`, branch `phase-1d`.

`src/phase1d/capture_cp10_campaigns.py` is a multi-company requests-based collection entrypoint; `src/phase1d/analyze_cp7_empirical.py` is an empirical batch analysis entrypoint. The repository has no central company-analysis LLM host or provider SDK usage callback. SKILLS records the earlier budgeted-agent package as separately delivered and unintegrated. Instrumenting those scientific batch collectors as if they were one company LLM run would misattribute work. They are unchanged.

This package is executable integration support, not global runtime interception. It does not automatically measure ChatGPT, native workers, hidden provider tools, JEV internals or other users. A live host must call these hooks or export conforming events. If it cannot expose usage, report null/partial. A command wrapper sees one orchestration boundary; inner tools, model tokens, remote memory and billing remain unknown. No real company analysis or external model invocation was used for verification.

## Quick start

From this directory:

```sh
python -I -B -m unittest discover -s . -p 'test_*.py' -v
python -I -B vera_metrics.py report examples/synthetic.jsonl --output-dir /tmp/vera-metrics-example
python -I -B vera_metrics.py run-command --ledger /tmp/vera-command.jsonl --run-id synthetic-command-1 --company-id synthetic-company --mode SCREEN --synthetic --output-dir /tmp/vera-command-report -- python -I -B -c 'print("synthetic command only")'
```

`report` always prints the table. `--output-dir` writes `metrics.json`, `metrics.md` and `dashboard.html`. These are derived local reports, not automatically published or uploaded. Supply a private output path and do not publish live operational data without authorization. `run-command` requires a new run ID; resume through the recorder API. It never logs the command arguments or stdout/stderr. It invokes no shell.

To append a supplied event without recording payloads:

```sh
python -I -B vera_metrics.py append --ledger /tmp/run.jsonl --event-file /tmp/event.json
python -I -B vera_metrics.py report /tmp/coordinator.jsonl /tmp/worker-a.jsonl /tmp/worker-b.jsonl --output-dir /tmp/report
```

Use one writer per file. A `Ledger` instance serializes its threads, but separate processes must write separate shards. Flush/fsync is used for each event. A truncated final line is rejected for explicit recovery, never silently removed. Retain immutable original shards. Do not run simultaneous writers against the same file.

## Host adapter hooks

Import `vera_metrics.py` from its installed directory; the file has no dependencies. Under isolated Python, load it with `importlib.util.spec_from_file_location` as the tests do, or explicitly make its installed directory importable in your host.

```python
ledger = Ledger('/private/run/coordinator.jsonl')
recorder = RunRecorder(ledger, 'run-unique-id').start(
    'opaque-company-id', 'STANDARD', cache_state='cold',
    collection_source='adapter')
status = 'failed'
try:
    with recorder.attempt('model', 'analysis', provider='provider-id',
                          model='model-id', model_version='version-id',
                          provider_request_id='opaque-provider-request-id') as observed:
        response = existing_authorized_model_call()
        # Map only actual provider usage. Do not estimate missing token counts.
        observed['token_usage'] = {
            'input_tokens': response.input_tokens,
            'cached_input_tokens': response.cached_input_tokens,
            'output_tokens': response.output_tokens,
            'input_includes_cached': True,
            'source': 'provider-reported-usage',
        }
        # Assign prices ONLY from a verified provider/model/version price record;
        # or set cost from an actual billing receipt. Leave both null if unknown.
    recorder.sample_process()  # local caller process-lifetime RSS only
    status = 'completed'
except (KeyboardInterrupt, SystemExit):
    status = 'cancelled'
    raise
finally:
    # Set status to the actual outcome. "complete" requires capture of every
    # expected attempt/worker. Final answer usage must actually be included.
    recorder.finish(status=status, capture_status='partial',
                    final_response_included=False)
    report = aggregate(read_events(['/private/run/coordinator.jsonl']))
    write_report(report, '/private/run/report')
    print(render_table(report))
```

The caller retains failed/cancelled run status; attempt contexts also map those outcomes, rethrow exceptions and never serialize exception text. Explicit `recorder.event('attempt_start', ...)` / `attempt_end` callbacks support async runtimes and providers whose request ID becomes available only after dispatch. Use the same stable request/attempt identity on replay. No hidden work is inferred.

Worker setup: emit `worker_start` once with `parent_worker_id`. A worker shard uses the same run ID; its local `RunRecorder` emits attempts only. The coordinator owns `run_start`, `run_resume` and `run_end`. A resume retains the run ID, emits `run_resume` after a terminal checkpoint and gives genuinely new attempts new IDs. Its summary remains cumulative, and wall latency includes pauses. Do not start a fresh duplicate run to disguise prior usage.

## Measurement semantics

### Tokens

`input_tokens` is either inclusive or exclusive of cached input, as declared by `input_includes_cached`. Inclusive input 1,000 with cache 400 becomes uncached 600 + cached 400, not 1,400. Output is separate. If inclusive input is known but the cache split is unknown, total input and total tokens can still be known. Unknown cache is never assumed zero. All counts are null or nonnegative bounded integers. Token metrics include known subtotals, known/expected attempt counts, status and completeness.

Only model and JEV attempts may report tokens. A tool wrapper cannot duplicate its child model's tokens. For JEV, record one outer dispatch and only returned, actually exposed token usage; do not infer internal tools or model work. If separate nested model attempts are emitted, omit those same tokens from the outer JEV attempt. Attribution is explicitly `exclusive`; inclusive parent rollups are rejected. Reusing a provider request ID under another run/attempt is rejected rather than charged twice. This is a guard, not a way to recover unknown runtime usage.

### Tools

The canonical convention is leaf dispatch attempts. Retries are separate; failed/cancelled dispatched attempts count. `kind=jev` counts as one tool dispatch as well as a usage-bearing service. `dispatch_role=wrapper` orchestration boundaries do not count as leaf tools. Distinct tool names and total attempts are separate. Never log orchestration and its nested dispatch again as the same leaf. Unknown/unavailable totals remain null; observed attempts are explicitly labelled lower-bound observations. Expected unobserved work is not guessed.

### Latency and completion

ISO timestamps require a timezone. `wall_seconds` is first run start through `data_cutoff`, including pauses/resumes and parallel work once. `closure_wall_seconds` separately measures first start to final `run_end.at`. `summed_attempt_seconds` may exceed wall time and is never substituted for it. A running/resumed run has null final wall latency. Invalid/reversed/out-of-interval times are rejected. Unknown vendor clocks must not be fabricated.

`run_end.status` is `completed`, `failed`, `cancelled` or `blocked`. These are operational states, not scientific approval. `capture_status` separately declares `complete`, `partial` or `unavailable`. `final_response_included=false` keeps full-run token/cost completeness false even if a process boundary is finished. Record the actual data cutoff; answer rendering and later work are excluded until observed.

### Cost

Use either explicit `cost` or token `prices`, never both on the same attempt. Monetary inputs are finite nonnegative decimal strings with an explicit currency. `cost.basis` is `invoice`, `provider_reported`, `estimate` or `explicit_no_charge`; actual zero requires evidence. Prices have source/version and distinct uncached input, cached input and output rates per million tokens. No current prices are hardcoded. Verify provider, model, version and rate coverage before adding a schedule.

A known subtotal is always separate from a complete total. Partial token-rate calculations remain usable subtotals; unknown attempt/tool/JEV fees keep the total incomplete. JEV token pricing alone never claims to cover the JEV service fee. A complete explicit cost can cover the attempt's full exclusive charge. Do not put a parent invoice containing its children's charges beside those children's charges; map it to one owner or retain it separately. Currencies are never converted or pooled. Groups separate billing bases and price versions. A complete estimated cost is still an estimate, not a paid invoice. Free/self-hosted compute is not assumed to cost zero.

Shared batch work must retain a separate unallocated owner/run; this version implements no arbitrary per-company allocation. Do not copy shared usage into each company. Cross-run provider request collisions are rejected.

### Memory

RSS, context tokens and storage bytes are separate. Each RSS sample names process, scope, method, platform and measurement interval. `sample_process()` uses `getrusage(RUSAGE_SELF).ru_maxrss`, converting Linux KiB and macOS bytes correctly; unsupported platforms return null. Its scope is `process_lifetime`, which may include pre-run work and excludes remote workers. The wrapper measures its own launcher process, not the launched command.

`run_isolated_process` is allowed only when the collector proves the process lifetime belongs to that run. The maximum observed process peak is not a simultaneous process-tree peak. Process peaks are never summed; simultaneous total RSS stays null. Process instances should use stable unique IDs; a PID alone is only valid within a known process lifetime. Context/storage are optional reported counts, not RAM estimates. This package does not measure GPU/remote model memory.

### Dashboard comparisons

Groups match mode, cache state, operational status, synthetic/live flag, collection source, final-response inclusion and the provider/model/model-version set. Costs additionally match currency, billing basis and price version. RSS additionally matches scope, method and platform. Per-metric n and missing counts are reported. Cost/RSS subgroups separately report eligible_n, missing among eligible runs, unknown-provenance rows and excluded incompatible rows; incompatible pricing or memory scopes are not called missing. Groups with entirely unknown provenance are not evidence of comparability; token/tool averages use complete measurements only. Wall latency remains observed latency and must be interpreted with the group boundary. Median/p90/p95 are descriptive linear-interpolation statistics; small samples are not robust performance predictions. No population extrapolation, predicted future bill or architecture optimization is inferred.

## Contract and privacy

`event.schema.json` describes structural validation; `validate_event` and `aggregate` enforce additional chronology, identity and coverage rules. The executable validator is authoritative for semantic invariants. Unknown fields are rejected. Identifier fields are restricted labels, not payload containers. Do not store prompts, responses, documents, tool arguments, URLs containing secrets, API keys, auth tokens, private reviewer content or exception text. Use opaque company/run/provider request IDs and preserve existing access boundaries. Metrics still may be private operational data.

## Verification and remaining work

Tests cover cache conventions, missing and partial values, actual zero, pricing, JEV fees, retries, duplicate events/requests, concurrent attempts, worker hierarchy, resumed runs, cancellation, negative/nonfinite inputs, corrupt ledgers, RSS scopes, group boundaries and command failure propagation. Exact counts belong in the release verification receipt; a test count is not company evidence.

Remaining live integration gate: bind a real company-analysis host's dispatch/usage/billing callbacks and verify one authorized real run against provider receipts. The ChatGPT runtime and all-user system are outside this repository package's control. No live billing validation, empirical company analysis or scientific prior promotion is claimed.
