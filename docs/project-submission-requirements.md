# Project Submission Requirements

Fields marked **Required** must be completed.

## Measured Score — Required

Enter the measured score shown on your results page, out of 50 (for example, `27.1`). It must match your screenshot.

## Repository Link

Provide your repository link. Include a README with the exact command that runs your wrapper.

## Devpost Project Link

Provide your Devpost project link.

## One-Page Decision Policy — Required

Paste your decision policy. Include:

- Signals.
- Thresholds, with a one-sentence justification for each.
- Failure behavior.

Judges score the justifications under problem fit. Use practice inputs only.

## Audit-Log Sample

Paste a few lines from `gate.py try` using practice inputs only. Never include final-set inputs.

## Wrapper Language and Start Command — Required

Provide your wrapper language and exact start command. For example:

- **Language:** Python
- **Start command:** `python3 wrapper/serve.py`

If you use a non-default command, include the value of `GATE_WRAPPER_CMD`.

## Persona UI Page — Required Response

Did you build a persona UI page? Select **Yes** or **No**.

Building the UI is optional and worth 25 points. No UI scores 0 out of 25; the other 75 points are unaffected.

## Confirmations — Required

Confirm all of the following:

- [ ] I ran `gate.py judge` myself, and the screenshot is from that run.
- [ ] I did not edit `harness/`, `mock_ezio.py`, `fixtures.json`, or persona data.
- [ ] My wrapper contains no hard-coded answers to practice or final-set inputs.
- [ ] I did not share the passphrase or final-set contents outside my team.
- [ ] The audit sample and policy page use practice inputs only.

## Results Screenshot

Upload **one image** of the results page from your final run. It must show:

- Your team name.
- The run time.
- The **"measured score (of 50)"** card.
