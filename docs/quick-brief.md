# False Promises: the quick brief

**Project:** Find the Exception. **Track:** Approval Gate. **Team:** False Promises, two members. **Persona:** a customer-support lead at fictional Lumen Cloud.

**The pitch:** “Before AI sends a promise, we look for a customer who makes it false.”

## The problem and our answer

An AI email can have a clean score and the correct discount percentage while promising that discount to someone who is not eligible. We combine the supplied simulated Ezio signals with independent company policy, then decide **APPROVE**, **HOLD_FOR_REVIEW**, or **BLOCK** before the simulated email action.

Our distinctive feature turns a discount failure into a concrete example: **this customer, this failed condition, this policy source**.

## The demo to remember

Use this draft:

> You qualify for our 15% loyalty discount on the Pro plan.

| Hypothetical customer | Result when other checks pass | Why |
|---|---|---|
| Pro, 11 months | BLOCK; no email action | Loyalty requires at least 12 months. |
| Pro, 12 months | APPROVE; mock email executes | The amount, plan, and tenure satisfy the policy. |

The comparison button sends two real backend requests. It does not fake the answers. The counterexample search itself creates no extra requests or actions.

## How it thinks

- **“You qualify”** checks the actual customer context.
- **“Every customer qualifies”** searches representative customer states within that promise's population.
- **“Eligible customers qualify”** preserves the policy conditions instead of inventing an ineligible audience.
- Search boundaries come from policy: for a 12-month minimum, check states around 11, 12, and 13 months, plus zero and relevant stated boundaries.

No counterexample found means the **modeled discount checks** found no violation. It is not a guarantee about the entire email.

## The decision rules

| Evidence | Decision effect |
|---|---|
| Wrong company fact, ineligible offer, illegal stacking, or contradicted Ezio claim | BLOCK |
| Missing necessary context, unauthorized product promise, or unresolved evidence | HOLD |
| Tone, bias, or agreement below 80 | HOLD |
| Ezio YELLOW / RED | HOLD / BLOCK |
| Ezio missing or malformed | HOLD; preserve any known local BLOCK |
| Accuracy `not_scored` | No automatic penalty; other checks still apply |
| All applicable checks pass | APPROVE |

**BLOCK wins over HOLD; HOLD wins over APPROVE.** A GREEN score never overrides a contradiction. The threshold of 80 is a justified review cutoff, not an 80% safety probability.

## What went into the build

The starter supplies the mock API, harness, fictional data, and mock actions. We implemented company-rule checks, the discount counterexample search, the decision policy, structured evidence, response validation, audit/review extensions, and the support UI.

The gate also checks prices, refunds, trials, first-response times, and agent authority. The UI has a composer, customer inputs, practice picker, witness cards, boundary comparison, loading/errors, and an audit drawer.

Held decisions can be rejected or sent back for revision with a required logged rationale. Reviews send nothing. Edited drafts require a new gate request.

Runtime: Python standard library plus local HTML/CSS/JavaScript. Required upstream: simulated Ezio over HTTP. No live Ezio, TokenRouter, Keenable, additional model, or real email service is needed. Codex assisted development and verification.

## The code you should know first

1. [`_discount_proof()`](../wrapper/source_checks.py#L123): our signature search and witness.
2. [`decide()`](../wrapper/wrapper.py#L152) and [`apply_policy()`](../wrapper/wrapper.py#L118): combine evidence and choose the result.
3. [`do_POST()`](../wrapper/serve.py#L75): the action gate; only APPROVE reaches the mock send.

Company values live in [`policies.json`](../personas/customer_support/policies.json) and [`price_sheet.csv`](../personas/customer_support/price_sheet.csv). Browser comparison lives in [`compareBoundary()`](../wrapper/ui/app.js#L205).

## What we can honestly say

Recorded practice verification: **48 unit tests passed, 34/34 mock checks, 16/16 exact practice decisions, zero false blocks on eight good practice cases, and all six failure drills passed.** Browser demo and review persistence were verified. These describe the recorded practice run.

A separate generated final report currently records **50.0 / 50 measured points**. The remaining 50 points come from judges. A report measures its recorded code version; later implementation changes require another run.

The language recognizer uses bounded English patterns. Customer context is entered by the human. The action is a log entry, not real mail. Repeated approved requests can repeat the action; production authentication and idempotency are future work.

## Start and present

```bash
python3 gate.py serve --persona customer_support
```

Open the printed local URL. Explain the false-promise problem, compare 11 versus 12 months, inspect the witness and action status, then show a held feature promise with a logged revision request.

Read the [detailed walkthrough](implementation-walkthrough.md) for the algorithms, request trace, limitations, and judge questions. Use [submission notes](submission-notes.md) for the remaining official run and upload steps.
