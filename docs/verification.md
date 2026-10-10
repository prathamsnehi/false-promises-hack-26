# False Promises — verification

Verified the implemented customer-support gate on October 10, 2026. This is practice and local verification, not a final held-out score.

| Check | Result |
|---|---|
| Supplied mock checks | 34/34 passed |
| Contract, harness, source, decision and review tests | 47 tests passed |
| Customer-support practice | 16/16 exact; 8/8 bad caught; 0/8 false blocks; 0 errors |
| Failure drills | All six passed; 15/15 failure points |
| Harness flags / unfinished policy justifications | None / none |
| Action gate | 28 audited requests, 11 approvals, 11 action-log entries |
| Protected-tool digest | `939643512c57edb1`, unchanged from pre-implementation |
| Verified wrapper digest | `e0d0e737feed186b`, matches practice report |

Practice artifacts: `results/False Promises.practice.json` and `.practice.report.md`, generated with the supplied `gate.py practice` command and left unchanged. They are not substitutes for official judging artifacts.

## Browser flow

Verified through installed headless Chrome against the complete local stack at normal mock latency:

- Backend returns BLOCK for hypothetical Pro at 11 months and APPROVE at 12 months; action badges match the actual responses.
- Comparison preserves the composer's selected customer context.
- Practice samples load their text and context.
- Held product promise records a manager revision request; rationale persists in the audit drawer and the review executes no action.
- Revised pricing draft requires a fresh gate request before approval and action.
- Empty draft issues no request; pending checks disable controls and show loading.
- Mobile viewport at 390 pixels has no horizontal overflow.
- Deliberately interrupted request shows an unknown-outcome error. Its expected `net::ERR_FAILED` console message is recorded separately; no unexpected browser errors occurred.

Detailed browser results: `docs/browser-verification.json`. Persona screenshots: `ui-boundary.png`, `ui-evidence.png`, `ui-review.png`, and `ui-mobile.png` in this folder. The boundary screenshot shows both actual backend outcomes.

## Remaining submission steps

The final judging key was not available in the environment. Once released, run personally:

```bash
python3 gate.py judge --persona customer_support --team "False Promises"
python3 gate.py results
```

Submit the generated final JSON/report unchanged and capture the official viewer's team, time, and measured-score card. Add both member names and the Devpost link to submission notes, and ensure the latest source is published to the supplied repository. No final-set input or key was opened, decrypted or included in these public notes.
