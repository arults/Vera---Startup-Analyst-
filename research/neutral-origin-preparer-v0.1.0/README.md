# Neutral origin-preparation diagnostic 0.1.0

UNADOPTED. HYPOTHETICAL GROUNDWORK ONLY. This standalone package preserves supplied assertions and computes calendar/order diagnostics. It does not select a scientific origin, authenticate evidence, ingest empirical records, run an estimator or implement a production analytical adapter. Independent acceptance is limited to those synthetic diagnostic mechanics.

## Run

No third-party dependencies are required. From this directory:

    python -I -B -m unittest discover -s . -p 'test_neutral_preparer.py' -v

This runs 28 synthetic tests in discovery mode. Directly executing test_neutral_preparer.py instead writes TEST_RESULT.json beside itself; use the command above when no persistent test-result file is wanted. The exact reviewed code and tests are unchanged. Their independent review also ran 11 separate controls, which are not included in this package or added to its standalone test count.

## Typed input and neutral output

close, event and entry assertion IDs must be nonempty and unique within their respective lists, with nonempty provenance objects. Predicate statuses are the exact strings TRUE, FALSE and UNKNOWN; booleans or other truthy values are invalid. UNKNOWN never becomes TRUE. Provenance objects and completeness flags are supplied assertions, not source validation.

Dates are canonical ISO calendar days or explicit earliest/latest intervals. Overlap, including distinct same-day events, retains unresolved order. No within-day sequence or midpoint is imputed. Input and provenance survive in input_record; normalized ledgers are deterministic by ID.

Both concepts remain visible: A considers the first completed position-producing close and requires an explicit TRUE close-ledger-completeness assertion; B considers aggregate completion with separately supplied round-position qualification. B does not require the final close to create a new position. Multiple or uncertain qualifying completions, potentially earlier UNKNOWN closes, overlapping order and later position-producing closes can require review. These concepts are not adopted alternatives, identified bounds or a continuous uncertainty interval.

Entry independence assertions are distinct from close facts. Explicit negative entry assertions, contradictory positive/negative assertions, prior terminal histories and ambiguous terminal order remain visible as conflicts or holds. No resurrection, new-clock independence or uninterrupted operation is inferred. Last affirmative operation is passed through unchanged and is not advanced by financing. within_admin_window is only a calendar-boundary comparison, not analytical eligibility.

## Deliberate limitations

index_relative_success_qualification and analytical_endpoint_eligibility remain NOT_EVALUATED; post_success_operating_state remains NOT_INFERRED. No primary origin is selected. Source truth/completeness, economic-round/entity identity, instrument/valuation qualification, risk sets, terminal-transition mapping, endpoint observation, multistate support, confidence bounds and lost-follow-up sensitivity remain unresolved.

This is not a polished ingestion API. Missing required top-level fields may raise KeyError rather than a standardized validation exception. Entry applicability compares supplied date representations, not adjudicated equivalent intervals or coverage. No exact timestamps or within-day resolution are implemented. A TRUE completeness flag and nonempty provenance do not prove a real record complete or qualified. Separate scientific and source-preparation review is required before any empirical reuse.

All packaged controls are hypothetical. No actual company data, source body, private binding, raw review, model-evaluation payload or real-record output is included. A passing suite establishes bounded implementation behavior, not scientific readiness or empirical accuracy.
