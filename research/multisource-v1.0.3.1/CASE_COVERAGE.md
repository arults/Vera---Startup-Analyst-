# Independent critic cases and executable coverage

The 23 scenarios in fixtures/critic-cases.json were proposed independently before integration. Tests below execute related invariants; they do not automatically certify the natural-language truth of the real cases. All synthetic approvals are test-only.

1. Inlightened completion: real demo retains completion upper bound and missing consideration; test_narrow_buyer_claim_can_be_accepted and release positive exercise valid narrow approval.
2. One buyer source: same positive test accepts one source without a universal two-source rule.
3. Syndication: test_same_family_copies_count_once adds 20 publishers with one declared origin; origin truth remains independently reviewed, not inferred from count.
4. Asset sale: test_asset_retyped_control_is_not_entailed rejects predicate relabeling. Exact natural-language asset-vs-company classification remains reviewer responsibility.
5. Announced intent: test_intent_retyped_completed_is_not_entailed rejects completed-claim mismatch.
6. Currently Wine period: real demo retains activity_period Jan1-Mar31; test_period_not_point and test_event_activity_period_fails enforce separation.
7. Reental holder scope: real demo has project distributions only; test_enterprise_value_not_investor_return and security-chain gate cover holder ambiguity. No actual holder-payment record supplied.
8. 18.21 native marketing: not added as an accepted observation. No automatic text classifier implemented; source provenance alone cannot replace required predicate review. Dedicated real-text fixture deferred.
9. Stockcard date: temporal representation supports explicit point; this real Stockcard source is not imported. Dedicated July4-vsJuly5 source adjudication deferred.
10. Ethos current/retrospective: pending source not imported as approved evidence. Dedicated full-source semantic test deferred.
11. Seven missing reports: source audit separates unperformed, blocked, no-result and searched. No closure-producing path exists; no new external sweep claimed.
12. C-TR: positive reporting_termination and negative retyped business_cessation tests.
13. Missing C-AR: no event imputation; no real C-AR record supplied. Dedicated filing search fixture deferred.
14. Registry active: positive legal_active and negative operating_activity from registry tests.
15. Bankruptcy petition: negative final_liquidation from court_petition test.
16. Same-brand successor: name-only and security-chain guards cover ambiguity; no real legal-entity succession chain supplied. Dedicated successor-source fixture deferred.
17. Same-claim conflict: open conflict and conflicting review tests, plus independent source-counterevidence tests.
18. Different-time no-conflict: no automatic conflict inference is performed; distinct events may coexist. Dedicated relaunch natural-language fixture deferred.
19. Known-at leakage: future publication/event/review/as-of tests; unknown retrieval outputs known_by_retrieval=null. No backdated availability certification.
20. Success without payout: narrow acquisition accepted despite unknown holder terms; no success estimator/return produced.
21. Incomplete search: unperformed material route and native-only negative tests.
22. Blocked primary: all-blocked negative and reviewed optional-alternative positive tests.
23. Narrow complete/unknown returns: trusted-release positive confirms unrelated unknown payout does not block narrow acquisition, while rates stay disabled.

Test discovery reports actual executions, not count of unique real source adjudications. Passing mechanics are not empirical validation, search exhaustiveness or a research plateau.
