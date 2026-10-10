# False Promises — decision policy

**Workflow:** a Lumen Cloud support lead gates a fictional customer email. **Pitch:** before AI sends a promise, we look for a customer who makes it false. Only APPROVE executes `send_email`; HOLD_FOR_REVIEW and BLOCK withhold it. Decisions follow **BLOCK > HOLD_FOR_REVIEW > APPROVE**.

**Independent signals.** Read the supplied price sheet and policies without changing them. A contradictory price, discount, refund, trial or first-response claim is BLOCK. Discount rates, eligible plans, tenure and stacking must satisfy policy. Unknown necessary context requires review. Product delivery commitments and unauthorized exceptions require manager review rather than an invented factual verdict.

**Find the Exception.** Personalized offers test the actual customer's plan and tenure. Universal or conditional offers search representative customer states within the population and qualifications stated in the draft. States come from the supplied plans and policy boundaries, including the loyalty minimum and adjacent months. A failing customer is recorded with the claim, failed condition and policy source. Searching does not execute actions. No witness found means only that modeled discount checks found no counterexample; it does not establish that all natural-language claims are true.

**Ezio signals and thresholds.** Call the supplied simulated Ezio over HTTP for every valid decision; retain its complete response. GREEN permits sending only after all other checks pass, YELLOW requires review, and RED blocks because the aggregate signals indicate substantial risk. Any contradicted claim blocks; an unverifiable claim requires review; supported public facts need no redundant verification from private company data.

| Dimension | Review below | Justification |
|---|---:|---|
| Tone | 80 | Customer correspondence should be neutral, so promotional or emotional language needs a human rewrite. |
| Bias | 80 | One-sided guidance can mislead even when its numbers match policy. |
| Agreement | 80 | Support must independently check a customer's premise rather than flatter or over-agree. |

These are operational review thresholds, not calibrated probabilities or guarantees of safety. `not_scored` adds no automatic penalty: neutral correspondence can pass and private claims still receive company checks. `unavailable` requires review because public claims may lack evidence.

**Failure behavior.** Bounded retries handle 429/503 and slow responses within the supplied 45-second upstream budget. Exhausted retries or malformed responses produce HOLD with failure evidence; an independently known contradiction remains BLOCK. Never fail open because a signal is absent.

**Record and review.** Audit every ordinary decision with timestamp, ID, input/context, checks, witnesses, complete Ezio response, reason and evidence. Managers can log rejection or request revision on held decisions. Review never overrides permission or executes an action; revised drafts require a new gate decision. UI action badges use the server response. The 11/12-month comparison uses explicitly hypothetical customers and ordinary gated mock sends.

**Practice illustration:** the same 15% loyalty offer to a Pro customer blocks at 11 months and can approve at 12 months. A routine billing update can approve; a product-release promise requires review. Policy and public audit examples contain no final judging inputs.
