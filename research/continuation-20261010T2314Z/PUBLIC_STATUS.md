# Verified post-publication status

October 10, 2026, 23:13:51 UTC. This local status candidate supersedes the earlier pending-runtime-review snapshot; it has not itself been published.

The [checkpoint commit](https://github.com/arults/Vera---Startup-Analyst-/commit/48400432094816645d599b4b3194afc1ff64a4f6) is published. Independent review of exact saved GitHub job receipts and full logs confirms four successful observed runs, including every listed step:

- [Isolated dependency validation](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38094022366/job/114336087229): 341 tests ran, 340 passed and one was skipped. The actual checkout was immutable c57ab8d645dbd904909f30223bc93ff2e45734aa. Exact source-export parity, the source-free dependency build, BeautifulSoup smoke and unchanged regression discovery all succeeded.
- [Phase 1B PR verifier](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38094027233/job/114336101280): 341 ran, 340 passed and one skipped.
- [Phase 1C PR verifier](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38094027269/job/114336101499): 79 passed, no skips.
- [Phase 1D PR verifier](https://github.com/arults/Vera---Startup-Analyst-/actions/runs/38094027277/job/114336101517): 341 ran, 340 passed and one skipped. Its separate 43 scientific-verifier gates passed; rates remained unpromoted and no outcome labels changed.

All three PR jobs actually checked out merge commit 17140cf3ff3ecbfa660f3e6f97f4a53de7e6301f, not the isolated job's historical checkout or simply the API-reported head SHA. Their results therefore have different exact code bindings.

## What remains untested or unchanged

The skip in each 341-test run was the optional exact 952-row replay because its authorized ledger and archived CSVs were not supplied. That replay remains unperformed; the skip was not a CP9-summary skip. Separately, 49 nested public diagnostic tests passed locally, with zero test-identifier overlap with the CI inventories. They were not run by these CI jobs and must not be added to the remote totals. Verifier gates are also separate from test counts.

The isolated job completed under the logged network-disabled, read-only root/source, nonroot, capability-dropped and bounded-resource container invocation. This establishes one observed successful runtime, not universal containment or a container-escape test. Observed Python was 3.12.15 with beautifulsoup4 4.15.0, requests 2.34.2 and curl_cffi 0.16.3. The base-image digest was sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1. Mutable image/package/action/runner tags remain a future reproducibility limitation; these versions describe this run only.

The original identity workflow's earlier missing-dependency failure remains historical. Its scientific writer was neither repaired nor rerun by this validation route, and remains unchanged. Four current successful checks do not mean every historical workflow is repaired.

## Trigger-prediction correction

The branch push synchronized an existing pull request and triggered the three prior verifiers, in addition to the new push-triggered validation. The original direct-push-only prediction omitted this effect. An explicit PR edit is not required for synchronize. Those prior verifier definitions use network-enabled/default-checkout execution, distinct from the new isolated route; absence of an explicit writer is not a general transitive-side-effect guarantee.

Prevention: inspect existing PR associations and synchronize/base-branch filters alongside direct push triggers, then reconcile the predicted event set with observed runs and actual checkout commits. Preserve the original prediction and an additive correction rather than rewriting history.

## Scientific and subsequent-work status

Phase 1D remains incomplete. These engineering checks do not resolve source-to-state, historical identity, denominator, origin, observation or uncertainty assumptions; authorize canonical regeneration; establish measured model accuracy; or promote sources, censor dates, methods or returns. A verifier PASS is bounded by its retained inputs and gates, with rates_promoted=false.

The separate temporal-diagnostic candidate is not accepted or published: an independent critic requested a successor to address a missing availability-witness-after-report flag. Its prior 70 candidate tests and a hypothetical model judgment cannot substitute for that correction and review. The original scientific holds remain intact.
