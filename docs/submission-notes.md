# False Promises — submission package

- **Team:** False Promises (two members; add names).
- **Track:** Approval Gate.
- **Persona/action:** customer support / `send_email`.
- **Repository:** https://github.com/prathamsnehi/false-promises-hack-26 (publish the implemented source here and confirm judge access).
- **Devpost:** add project link.
- **Language:** Python 3.9+; standard library backend, offline HTML/CSS/JavaScript UI.
- **Wrapper start command:** `python3 wrapper/serve.py`. No `GATE_WRAPPER_CMD` override.
- **Complete demo start command:** `python3 gate.py serve --persona customer_support`.
- **Persona UI:** Yes.

## Approach

Before AI sends a promise, we look for a customer who makes it false. The complete gate combines simulated Ezio signals with Lumen Cloud's authoritative prices and policies. Its discount engine checks actual customer eligibility for personalized offers and searches policy-derived boundary customers for broader promises. It produces a concrete, source-backed counterexample instead of another confidence score. Only approved drafts execute the mock email; held drafts have a logged review and revision flow.

## Two-minute demo

1. Explain that a correct discount amount can still be an impossible promise.
2. Load the loyalty demo and compare hypothetical Pro customers at 11 and 12 months. Show the clean Ezio tier beside the first customer's failed tenure condition. Only the eligible approval executes.
3. Enter an overbroad offer: `Every customer gets a 15% loyalty discount.` Show the concrete failing customer and policy source.
4. Run the practice product-feature promise; record a request for revision with a reason. Show the persistent audit drawer.
5. Explain dimension thresholds and missing-evidence behavior. Invite a new draft.

## Verification and official artifacts

Completed verification is recorded in `docs/verification.md`; practice-only CLI excerpts are in `docs/audit-sample.md`. Persona screenshots are in `docs/ui-boundary.png`, `docs/ui-evidence.png`, `docs/ui-review.png`, and `docs/ui-mobile.png`.

```bash
python3 test_mock.py
python3 -m unittest test_contract test_harness test_source_checks test_decisions test_reviews
python3 gate.py practice --persona customer_support --team "False Promises" --no-show
python3 gate.py try --persona customer_support --context '{"plan":"Pro","customer_tenure_months":11}' 'You qualify for our 15% loyalty discount on the Pro plan.'
python3 gate.py try --persona customer_support --context '{"plan":"Pro","customer_tenure_months":12}' 'You qualify for our 15% loyalty discount on the Pro plan.'
```

The official run passed at **50.0/50**; see `docs/verification.md`. Its score screenshot is `docs/final-results.png`. To rerun after any wrapper changes, keep default judging latency and timeout:

```bash
python3 gate.py judge --persona customer_support --team "False Promises"
python3 gate.py results
```

Upload the final `results/False Promises.json` and `results/False Promises.report.md` unchanged. Enter measured score **50.0 out of 50** for this verified run. Upload `docs/final-results.png`, which captures the official results page with team, run time and measured-score card. Include persona screenshots/recording and the one-page policy in `docs/decision-policy.md`. Generate the public audit sample using practice-only `gate.py try` calls; do not copy final-run logs or inputs into public documentation.

## Confirm only after checking

- Ran final judging personally; screenshot comes from that run.
- Did not edit the harness, mock, fixtures or persona data.
- No hard-coded answers or shared final key/contents outside the team.
- Policy and public audit sample use practice inputs only.
- Repository contains the final implementation and is accessible to judges.

## Tools used

Codex assisted with code inspection, planning, parallel implementation, regression tests and local browser verification. The runtime gate uses the supplied simulated Ezio HTTP API and fictional persona data. It does not depend on live Ezio, TokenRouter, Keenable, or an additional model. Update this note if the team uses other tools.

Optional Ezio-use note: simulated Ezio demonstrated why a clean aggregate score and `not_scored` accuracy cannot establish private discount eligibility. We retained its public-claim verdicts and dimension signals, and added policy-backed counterexamples; judges can see the distinction in the boundary demo and decision records. Do not describe this as a live Ezio run.

## Two-person handoff

One person owns gate correctness, regression/failure checks and the final judging command; the other owns the UI walkthrough, policy, screenshots, repository/Devpost access and submission. Freeze new features at minute 45 and reserve the final 15 minutes for a complete run, artifact capture and submission.
