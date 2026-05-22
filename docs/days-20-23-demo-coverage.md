# Days 20-23 — Demo rubric-rule coverage audit

**Generated:** 2026-05-21 (hackathon Day 6 of 26)
**Source data:** `rubric/v1.yaml` v1 (15 rules) × `scripts/seed-archetype-mrs.sh` (5 archetypes)

## Goal

Per `mr-sentinel-hackathon-spec.md` §9 Days 20-23: "Demo repo seeded with 8-12 archetypal MRs, every rule has at least one tripping example." This audit is the gap analysis that drives which new archetypes to add.

## Coverage matrix

For each rubric rule, which of the 5 existing archetypes (`!9`-`!13`) trip it. Each cell is a designed-to-trip / likely-to-trip / not-applicable assessment based on the seeding script source and the rule's `evaluator_prompt`. Live verdicts may be richer than the design intent because Gemini will flag adjacent issues it spots in the diff.

| # | Rule | Severity | !9 admin-dump | !10 secrets | !11 migration-no-down | !12 refactor-no-spec | !13 dep-CVE |
|---|------|----------|---------------|-------------|------------------------|----------------------|-------------|
| 1 | contract-has-spec-link | warning | 🎯 (no spec ref) | 🎯 (no spec) | ✓ (`Closes #142`) | 🎯 ("small fix") | ✓ (`Closes #189`) |
| 2 | acceptance-criteria-testable | warning | 🎯 (no spec → no criteria) | 🎯 | n/a | 🎯 | n/a |
| 3 | spec-implementation-match | error | likely (no spec) | likely (no spec) | — | likely (no spec) | — |
| 4 | integration-boundaries-explicit | warning | 🎯 (new endpoint, no OpenAPI) | — | partial (DB schema, no schema doc) | — | — |
| 5 | kill-switch-path | warning | 🎯 (new behavior, no flag) | — | — | — | — |
| 6 | changed-method-coverage | error | 🎯 (no test for `dump_all_patients`) | — | — | 🎯 (no test for `charge_invoice` changes) | — |
| 7 | mutation-resilience-critical-paths | warning | — | — | — | — | — |
| 8 | no-skipped-tests-introduced | error | — | — | — | — | — |
| 9 | no-commented-out-code | info | — | — | — | — | — |
| 10 | dependency-advisory-check | blocker | — | — | — | — | 🎯 (pyyaml 5.1 + requests 2.20) |
| 11 | no-secrets-in-diff | blocker | — | 🎯 (Stripe + AWS + DB pw + JWT) | — | — | — |
| 12 | auth-on-new-public-endpoints | blocker | 🎯 (`/admin/dump-patients` no auth) | — | — | — | — |
| 13 | observability-on-new-endpoints | warning | 🎯 (no log line in handler) | — | — | — | — |
| 14 | error-budget-impact-declared | warning | — | — | — | — | — |
| 15 | rollback-documented-for-migrations | error | — | — | 🎯 (no `downgrade()`) | — | — |

Legend: 🎯 = designed to trip (seeding script intent) · ✓ = explicitly satisfies the rule · partial = adjacent issue (Gemini may flag) · likely = expected trip based on weak description · — = rule not exercised

## Rules with no existing archetype

5 of 15 rules have no archetype designed to trip them:

| # | Rule | Severity | Note |
|---|------|----------|------|
| 7 | mutation-resilience-critical-paths | warning | Needs file metadata `critical_path: true` + degraded mutation score. **Skip — too synthetic for a 3-min demo.** |
| 8 | no-skipped-tests-introduced | error | Cheap to demonstrate: add 2-3 `@pytest.mark.skip` decorators in a test file. |
| 9 | no-commented-out-code | info | Cheap to demonstrate: refactor that leaves a 20-line commented-out block. |
| 14 | error-budget-impact-declared | warning | Requires an `slo.yaml` in the repo. Can be added in a setup commit + MR that rewrites the request hot path with no SLO note. |
| 3 | spec-implementation-match | error | Multiple archetypes "likely" trip it because they have no spec; needs an MR that EXPLICITLY links a spec and then adds out-of-scope behavior — that's the cleanest demonstration. |

## Recommendation — 4 new archetypes (Story 3)

Total after addition: **9 archetype MRs**, hits **14 of 15 rubric rules** (skipping `mutation-resilience-critical-paths` as overly synthetic for the demo window). Brings the demo into the spec §9 target band (8-12).

| # | Working title | Branch | Files | Primary rule | Secondary rules likely |
|---|--------------|--------|-------|--------------|------------------------|
| 6 | `feat(refunds): admin refund-all endpoint per #220` | `feature/admin-refund-all` | `app/routes/admin.py` + spec link in description | spec-implementation-match (error) — spec #220 says "audit-only", MR adds destructive endpoint | auth-on-new-public-endpoints (blocker), changed-method-coverage (error) |
| 7 | `fix(billing): skip flaky Stripe retry tests` | `fix/skip-stripe-retry-tests` | `tests/test_billing.py` | no-skipped-tests-introduced (error) — adds 2 `@pytest.mark.skip` with no linked issue | no-commented-out-code (info) — also leaves an old version commented |
| 8 | `refactor(auth): simplify token validation` | `refactor/auth-token-simplify` | `app/auth.py` | no-commented-out-code (info) — leaves 25-line block of old validator commented out | changed-method-coverage (error) |
| 9 | `feat(slo): adopt SLO + rewrite invoice hot path` | `feature/slo-and-hot-path-rewrite` | new `slo.yaml` + modified `app/services.py` | error-budget-impact-declared (warning) — touches hot-path, no error-budget section | spec-implementation-match (error) (no spec link) |

**MR 9 caveat:** Requires `slo.yaml` to already exist on `main` for the rule to fire correctly per the evaluator prompt ("For diffs touching files in services with an SLO file..."). The cleanest approach is to commit the `slo.yaml` to `main` first (small chore commit, no MR), then open the hot-path MR. Plan accordingly in `scripts/seed-archetype-mrs-v2.sh`.

## Coverage after Story 3 lands

| Coverage tier | Count | Rules |
|--------------|-------|-------|
| Hit by 2+ archetypes (robust signal) | 6 | contract-has-spec-link, acceptance-criteria-testable, changed-method-coverage, integration-boundaries-explicit, spec-implementation-match, kill-switch-path |
| Hit by exactly 1 archetype | 8 | dependency-advisory-check, no-secrets-in-diff, auth-on-new-public-endpoints, observability-on-new-endpoints, rollback-documented-for-migrations, no-skipped-tests-introduced, no-commented-out-code, error-budget-impact-declared |
| Not hit (deliberately deferred) | 1 | mutation-resilience-critical-paths |

## Notes / decisions

- **Why skip mutation-resilience-critical-paths.** The rule depends on running mutation tests and reading file-level metadata. Faking it would require either committing a fake mutation-test score file or instrumenting the demo repo's mutation harness. Either path adds 4-6 hrs for one rule in info/warning tier. The 3-min demo storyboard (`docs/demo-script.md`) does not call out this rule. Cost > benefit.
- **Why 4 new MRs not 7.** The spec target is 8-12; 9 lands cleanly in band. Adding 7 risks visual noise in dashboard Shot 8 (recent MRs table) and dilutes the hero `!10` story.
- **Risk of double-tripping.** Several new archetypes are designed to trip 2-3 rules. This is by design — it demonstrates the agent finds compounding issues, not just one-trick wonders. The demo-script's Shot 6 specifically benefits from a "four security rules failing" frame on `!10`; MR 6 will produce a similar multi-rule failure frame for the spec-mismatch story.
- **Verification strategy.** Once seeded, run a single live-fire sweep capturing per-MR verdict + rule-outcome list (see [`live-fire-2026-05-21.md`](live-fire-2026-05-21.md) — generated by Story 4). If any new MR fails to trip its primary rule, iterate the seed payload.

---

*Generated by Story 2 of `/daily-priority mr-sentinel hackathon` 2026-05-21-b. Feeds Story 3 + Story 4.*
