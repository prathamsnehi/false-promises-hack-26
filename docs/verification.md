# False Promises — final verification

Verified the customer-support gate on October 10, 2026 at 2:51:26 PM Pacific. The official harness ran with default judging latency, timeout, and worker settings.

| Check | Result |
|---|---|
| Official measured score | **50.0/50**; the remaining 50 points are judged |
| Core decisions | 12/12 exact; 6/6 bad inputs caught; 0/6 false blocks; 0 errors |
| Stretch decisions | 6/6 correct; 0 errors |
| Failure drills | All six passed; 15/15 points |
| Surprise inputs | Both matched |
| Supplied mock checks | 34/34 passed |
| Contract, harness, source, decision and review tests | 48 tests passed |
| Harness flags / unfinished policy justifications | None / none |
| Audit and action gate | 48 audited decisions, 21 approvals, 21 actions |
| Protected-tool digest | `939643512c57edb1`, unchanged from pre-implementation |
| Verified wrapper digest | `4e0e8d36dfaa5a17`, matches the official report and current files |
| Official integrity | Signature and checksum valid; Markdown report matches harness rendering |

Submit `results/False Promises.json` and `results/False Promises.report.md` unchanged. Official artifacts contain held-out inputs and are ignored by Git; upload them directly to the organizers. The passphrase is not stored in source or documentation. Official logs are retained locally in `runs/False_Promises-145028/`.

## Pricing fix

Separated the billing period of each price from other claims in the same sentence. A later annual-discount claim no longer turns a monthly price into an annual price. Explicit annual billing modifiers still apply to their price. Regression coverage uses independent wording and multiple plans, with both correct and incorrect amounts.

## Browser flow

Verified through headless Chrome against a fresh complete local stack at normal mock latency:

- One-click passing, failing, and held examples display actual backend outcomes and corresponding action status.
- Reset clears the browser session while keeping persistent audit records.
- The fixed loyalty comparison returns BLOCK at 11 months and APPROVE at 12 months while preserving the edited composer.
- Practice drafts load their text and context.
- Manager revision requests persist in the audit drawer and execute no action.
- Revised and multi-clause pricing drafts require a fresh successful gate request before action.
- Empty input issues no decision request; pending requests disable controls and show progress.
- Mobile viewport at 390 pixels has no horizontal overflow.
- Interrupted requests show an unknown-outcome error; no unexpected browser errors occurred.

Detailed current browser evidence and screenshots are retained in `runs/pre-submit-browser/`. Earlier practice screenshots are in `docs/ui-*.png`. The official submission screenshot is `docs/final-results.png`; it shows the team, run time, and measured-score card without held-out inputs.

## Submission handoff

- Upload the official JSON, report, and results screenshot; enter measured score **50.0**.
- Include `docs/decision-policy.md` and the practice-only `docs/audit-sample.md`.
- Provide the public repository, exact start command `python3 wrapper/serve.py`, and persona UI response **Yes**.
- Add both team members' names and the Devpost project link, then complete the organizer confirmations.
- Publish any remaining source/documentation changes before submitting. Regenerate judging artifacts if anything under `wrapper/` changes afterward.
