# Judge-facing frontend

Start the complete offline demo from the repository root:

```bash
python3 gate.py serve --persona customer_support
```

Open the local address printed by the command. No packages, keys, or external services are needed.

## A one-minute walkthrough

1. **Run passing example.** A Pro customer at 12 months receives a valid 15% loyalty offer. The gate approves and executes one simulated email.
2. **Run failing example.** The same offer goes to a Pro customer at 11 months. The gate blocks it, even though Ezio's aggregate signal is GREEN. The visible counterexample identifies the unmet eligibility condition.
3. **Run review example.** A feature delivery promise needs manager review. Record a revision request, then open the audit trail to see the saved rationale. Review itself does not send an email.
4. **Run the 11 vs. 12 month test.** Compare the canonical offer side by side. This uses two ordinary backend decisions and preserves the custom draft. Each approval executes a simulated email.
5. Invite the judge to edit the email, plan, or tenure and run a fresh check. An existing result is labeled stale when its inputs no longer match.

The examples describe expected outcomes; the displayed decisions and action badges always come from `POST /decide`. Outcome progress tracks responses actually received during this browser session. Reset clears the local demo but keeps persistent audit records.

## Frontend changes

- A direct problem statement and three one-click examples replace the sample-selection process as the starting point.
- Results lead with the decision, actual action status, policy rationale, and a concrete counterexample. Ezio's tier and accuracy state remain visible to explain why a good score can still be blocked.
- Detailed checks, signal metrics, practice drafts, and session history expand when needed.
- Responsive layouts, visible keyboard focus, result/error navigation, loading feedback, and reduced-motion support make the walkthrough easier to operate.

The frontend remains plain HTML, CSS, and JavaScript served by the existing Python wrapper. Decision policy and action execution stay in the backend.

## Verification

Verified in local headless Chrome on October 10, 2026 against the complete wrapper and supplied mock, with mock latency set to zero for repeatable checks. A delayed request also verified disabled controls and loading feedback. All 48 existing contract, harness, source, decision, and review tests passed.

The browser pass covered the three actual outcomes, GREEN signal with BLOCK, saved review notes, a revised draft passing a fresh check, fixed comparison inputs, practice context loading, stale-result notices, empty-input validation, reset preserving audit records, interrupted requests, and result/error navigation. No JavaScript page errors occurred. Layouts fit at 375, 390, 768, and 1024 pixels, and reduced-motion settings disable animations.

Evidence: [browser verification](frontend-verification.json), [desktop](frontend-desktop.png), [blocked decision](frontend-blocked.png), and [mobile](frontend-mobile.png). These are local demo checks, not official judging scores.
