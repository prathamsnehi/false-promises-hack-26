# Four-Person, One-Hour Build Plan

Use the existing Python starter and build one complete persona workflow. This plan assumes **customer support** unless the team has already chosen another persona. Its price table and explicit policies make it a practical scope for one hour; paralegal holding interpretation and financial metric/period parsing require more semantic work.

## Codebase Review

The application flow is:

`gate.py` → private mock + wrapper server → `POST /decide` → mock HTTP analysis → independent data checks → policy → audit → mock action only on APPROVE.

| Area | Current state | Build implication |
|---|---|---|
| `gate.py`, `harness/runner.py` | Starts and stops the local stack; passes ports, mock URL, and log directory through the environment | Use the supplied commands and keep their contracts |
| `mock_ezio.py`, `fixtures.json` | Simulated scores, public-knowledge claims, and six failure modes | Read signals through HTTP; the mock cannot verify private persona data |
| `wrapper/serve.py` | Request validation, static UI, samples endpoint, and approval-only action execution already implemented | Keep the server; UI can integrate immediately |
| `wrapper/ezio_client.py` | Bounded retry/backoff for 429/503, timeouts, response limits, 45-second budget | Verify existing resilience rather than rebuilding the client |
| `wrapper/wrapper.py` | Data loader and policy plumbing work; `check_source_of_truth()` returns `[]` | Independent checks are the highest-priority missing feature |
| `wrapper/policy.json` | Tier mappings exist; all three dimension thresholds are zero; seven justifications are TODO | Add meaningful thresholds and explain each choice |
| Decision evidence | Only source-of-truth violations populate evidence; approvals, Ezio-only decisions, and failures can have empty evidence | Make evidence useful for every outcome |
| `wrapper/audit.py`, `wrapper/mock_actions.py` | Thread-safe JSONL decision/action logging already implemented | Preserve `GATE_LOG_DIR` and verify action counts |
| `wrapper/ui/persona.html` | Basic draft button and raw JSON output; sample picker is unwired; errors/loading are unhandled | Build the persona experience here, using offline HTML/CSS/JS |
| `personas/` | Three supplied rule sets, source data, and 16 labeled practice items per persona | Choose one; use data-driven rules and test new phrasings |
| `wrapper/evaluate.py`, `test_*.py` | Practice helper and infrastructure tests provided | Existing passing tests do not establish business-rule correctness |
| `harness/results_server.py`, `harness/results.html` | Results viewer already implemented | Use it for the final screenshot |
| `harness/seal.py`, `final/final_set.sealed` | Final inputs encrypted until organizer release | Run the official judging command after release |
| `example_client.py`, `Dockerfile` | Alternate demo client and optional mock container | Neither is needed for this build |
| `docs/project-submission-requirements.md` | Submission checklist | Person 4 owns completing the submission package |

Baseline verified on the current starter:

- Mock checks: **34/34 passed**.
- Contract/harness tests: **21/21 passed**.
- Customer-support practice: **1/8 bad inputs caught**, **0/8 good inputs falsely blocked**, **9/16 exact decisions**.
- Failure drills: **7.5/15**. Down, malformed, and unavailable pass; rate-limited, server-error, and slow fail because the bad probe is approved after a successful mock response.
- Flags: seven unfinished policy justifications and missing evidence on some decisions.

This is a runnable starter, but it currently approves most bad drafts. Completing the independent checker should improve normal decisions and the three failing drills together.

## Assignments

### Person 1 — Business Rules and Independent Checks

**Own:** a new `wrapper/source_checks.py`. Read `personas/customer_support/business_rules.md`, `policies.json`, and `price_sheet.csv`.

Implement general checks for:

1. Plan prices, including monthly versus annual billing.
2. Annual and loyalty discount percentages, eligible plans, customer tenure, and prohibited stacking.
3. Monthly/annual refund windows and first-payment scope.
4. Trial duration, eligible plans, card requirement, and response-time promises.
5. Product-feature promises, delivery dates, and unauthorized exceptions → HOLD_FOR_REVIEW.
6. Different numeric formats and several claims in one sentence. A correct price must not hide an incorrect response time.

Compare extracted facts with the supplied data rather than matching practice sentences. Associate each number with its claim and plan; use `context` for eligibility without letting it override an explicitly named plan. Missing eligibility information should produce a specific review reason rather than an exception.

**Shared interface:** `check(text, context, sot)` returns a list of `(level, message)` tuples; `level` is `BLOCK` or `HOLD_FOR_REVIEW`. Return `[]` when no violation is detected. Messages identify the claimed value, expected value, and source file. Do not import `wrapper.py` from this module.

**Handoff:** usable first version by minute 20; variant handling complete by minute 35. Person 2 owns the adapter into `Finding` in `wrapper.py`.

**Done when:** wrong prices/discounts/refund terms are blocked, unauthorized promises are held, valid statements pass, and new wording does not rely on practice IDs or exact text.

### Person 2 — Decision Policy, Evidence, and Resilience

**Own:** `wrapper/wrapper.py`, `wrapper/policy.json`; change `ezio_client.py` or `audit.py` only for a demonstrated issue. Read `wrapper/README.md`.

1. Wire Person 1's checker into `check_source_of_truth()` and preserve BLOCK > HOLD_FOR_REVIEW > APPROVE precedence.
2. Explicitly block contradicted Ezio claims; preserve supported claim text and source as evidence. Do not require the company price sheet to verify unrelated public facts that Ezio supports.
3. Set tone, bias, and agreement thresholds with one-sentence business justifications. Start with a defensible review threshold such as 60, then validate against good inputs and independently written variants; it is a proposed starting value, not an official cutoff.
4. Handle `scored`, `not_scored`, and `unavailable` explicitly. Neutral drafts with no claims may pass after other checks. Missing fact-check service or malformed responses should produce a reasoned hold.
5. Include evidence for every outcome: relevant source checks, claim verdicts, actual dimension values, and failure details. State "no violation detected" rather than claiming unmatched text was verified.
6. Preserve the existing audit/action flow and 60-second decision limit. Confirm checks still run after successful retries and slow responses.

**Handoff:** policy and meaningful response evidence by minute 20; checker integration by minute 30; final justifications by minute 40.

**Done when:** all accuracy states have explicit behavior, low dimensions can cause review despite GREEN tier, failures return valid decisions, every response has meaningful evidence, and policy TODOs are gone.

### Person 3 — Customer-Support Persona UI

**Own:** `wrapper/ui/persona.html` and any local CSS/JS/assets under `wrapper/ui/`. Read the UI rubric in the root README.

Build an email approval workspace with:

1. Draft input, plan selector, and customer-tenure input. Send `{text, persona: "customer_support", context: {plan, customer_tenure_months}}` to `POST /decide`.
2. Clear APPROVE / HOLD_FOR_REVIEW / BLOCK status, plain-language reason, evidence, and explicit "email action executed / not executed" status from the server.
3. Practice sample picker using `GET /api/samples?persona=customer_support`; load both text and context. Allow judges to edit the draft and try their own input.
4. Loading state, disabled buttons while pending, visible request failures, and empty/oversized-input validation. Allow enough time for the backend's 45-second mock budget; a short browser timeout does not cancel backend action execution.
5. Relevant Ezio dimensions and accuracy status, plus a small session history of returned decisions for side-by-side demo comparison. Session history is not a substitute for the persistent audit log.

Use labels/icons as well as color. Keep all assets local and all decisions in the backend.

**Handoff:** first working UI by minute 20; complete good/bad/held sample flow by minute 35; polish and browser checks by minute 45.

**Done when:** a judge can enter a draft, send a practice sample with its context, understand the risk/evidence, and see that held/blocked drafts do not execute the email action.

### Person 4 — Integration, QA, Demo, and Submission

**Own:** new business-rule tests, `docs/decision-policy.md`, demo notes, and `wrapper/README.md` run instructions. Coordinate changes from the other three people.

1. Record the baseline and tool digest. Keep a short issue list with failing input, expected behavior, and owner.
2. Write a small set of meaningful regression cases for the chosen persona: valid/invalid prices, eligibility, stacking, refunds, promises, word-form numbers, multiple claims, no claims, supported/contradicted Ezio claims, and degradation. Include new wording and boundary values.
3. Run full practice after the first integrated backend, inspect the report, and route failures to Person 1 or 2. Check that audit entries exist and actions run exactly for approvals.
4. Start the UI, test the complete flow in a browser, and verify sample context reaches the backend.
5. Write the one-page policy from implemented behavior and Person 2's justifications. Capture a few practice-only audit lines generated by `gate.py try`.
6. Prepare a two-minute demo: business stakes → valid approval/action → wrong fact blocked with source evidence → manager-review case → threshold/failure explanation.
7. After organizer release, run `gate.py judge` with the actual team name. Capture the final results screenshot with team, run time, and measured score out of 50. Prepare repository/Devpost links, exact start command, unmodified JSON/report, policy, audit sample, and confirmations.

**Handoff:** test cases by minute 15; first integrated practice run by minute 30; policy/demo draft by minute 40; submission package by minute 60.

**Done when:** the merged build runs from documented commands, practice has no request errors or action mismatches, final artifacts are collected when the key is available, and the team can finish the demo in two minutes.

## One-Hour Schedule

| Minutes | Person 1 | Person 2 | Person 3 | Person 4 |
|---|---|---|---|---|
| 0–5 | Agree persona and checker interface | Confirm response contract | Confirm UI inputs/context | Set ownership, record baseline |
| 5–20 | Prices, discounts, eligibility | Policy, Ezio claims, evidence | Draft form, decision view, samples | New variants/tests, draft demo/policy |
| 20–35 | Refunds, trials, promises, numeric variants | Integrate checker; fix degradation/evidence | Complete sample flow, errors, history | Practice run; triage misses and inspect logs |
| 35–45 | Fix highest-impact rule misses | Finalize thresholds/justifications | Browser usability and polish | Full verification; finalize policy/demo |
| 45–53 | Support integration fixes | Support integration fixes | Final UI fixes | Official judge run when key is released; inspect results |
| 53–60 | Freeze code and rehearse | Explain policy in rehearsal | Drive UI in rehearsal | Screenshot, artifacts, links, confirmations |

**At minute 45, stop adding features.** Reserve the last 15 minutes for integration, official judging, and submission. If final inputs are not released yet, complete everything else and run judging as soon as the key arrives. The repository lists release at 2:30 PM Pacific; that release is an external dependency, not a guaranteed minute of this relative schedule.

## Verification Commands

Run from the repository root. Restart `gate.py serve` after Python or policy changes because policy and source data are loaded/cached in the running process.

```bash
python3 test_mock.py
python3 -m unittest test_contract test_harness
python3 gate.py practice --persona customer_support --team "Your Team Name" --no-show
python3 gate.py serve --persona customer_support
```

The `serve` command prints the UI URL. Use a separate terminal for these practice-only demo inputs:

```bash
python3 gate.py try --persona customer_support 'The Pro plan is $49 per month.'
python3 gate.py try --persona customer_support 'Your 30% loyalty discount applies to the Pro plan.'
```

After the organizer releases the key:

```bash
python3 gate.py judge --persona customer_support --team "Your Team Name"
python3 gate.py results
```

Keep default official judging latency/timeouts. Aim for 8/8 bad practice inputs caught, 0/8 good inputs falsely blocked, 16/16 exact decisions, and 15/15 failure points. These are targets, not a guarantee of held-out performance.

## Scope and Ownership Boundaries

- Build one persona. Keep Python and the supplied HTTP stack; plain HTML/CSS/JS avoids a new build pipeline.
- Prioritize the independent signal, meaningful policy/evidence, and working UI. Scoring is 35 held-out + 15 failure handling + 25 judge rubric + 25 UI.
- Person 2 is the sole editor of `wrapper.py`. Person 1 works in a separate module; Person 3 stays under `ui/`; Person 4 owns tests/docs. Share interfaces at minute 5, not at the final merge.
- Preserve `gate.py`, `harness/`, `mock_ezio.py`, `fixtures.json`, persona data, and generated official results. Do not hard-code practice/final answers or share final inputs/passphrases outside the team.
- Defer a second model, framework migration, Docker deployment, caching, and manual approval overrides. A logged backend review workflow can be a stretch feature only after the required path is verified.

If the team has chosen **paralegal**, Person 1 substitutes citation normalization, fabricated/unknown cases, reporter/year validation, short aliases, and holding checks; Person 3 builds a memo-review UI. For **financial analyst**, Person 1 substitutes metric/period/unit extraction, rounding tolerances, guidance bounds, and unverified company claims; Person 3 builds a client-note UI. The other responsibilities and schedule remain the same, with matching persona flags in commands.
