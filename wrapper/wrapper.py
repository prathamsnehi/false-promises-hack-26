"""Your wrapper. Start with check_source_of_truth() and policy.json.

Flow: call Ezio -> read its signals -> check your persona's source of truth -> apply policy
-> decision (+ reason, evidence) -> audit log -> run the mock action only if approved.

Run one input:  python3 wrapper.py customer_support "Your 30% loyalty discount applies to the Pro plan."
Score yourself: python3 evaluate.py customer_support
"""
import csv
import json
import math
import sys
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import audit
import mock_actions
import source_checks
from ezio_client import EzioError, analyze

HERE = Path(__file__).resolve().parent
PERSONAS = HERE.parent / "personas"
POLICY = json.loads((HERE / "policy.json").read_text())

APPROVE, HOLD, BLOCK = "APPROVE", "HOLD_FOR_REVIEW", "BLOCK"
RANK = {APPROVE: 0, HOLD: 1, BLOCK: 2}


@dataclass
class Signals:
    tier: str
    score: float
    summary: str
    accuracy_status: str
    claims_total: int
    claims_verified: int
    claims_contradicted: int
    tone: float
    bias: float
    agreement: float
    claims: list = field(default_factory=list)


@dataclass
class Finding:
    level: str
    message: str


@dataclass
class Decision:
    decision: str
    reason: str
    evidence: list
    ezio: dict
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    checks: list = field(default_factory=list)
    counterexamples: list = field(default_factory=list)


def parse_signals(resp):
    try:
        verdict, dims = resp["verdict"], resp["dimensions"]
        acc = dims["accuracy"]
        if verdict["tier"] not in ("GREEN", "YELLOW", "RED") or acc["status"] not in ("scored", "not_scored", "unavailable"):
            raise ValueError("invalid tier or accuracy status")
        scores = [verdict["score"]] + [dims[d]["score"] for d in ("tone", "bias", "agreement")]
        if acc["status"] == "scored":
            scores.append(acc["score"])
        if any(isinstance(s, bool) or not isinstance(s, (int, float)) or not math.isfinite(s) or not 0 <= s <= 100 for s in scores):
            raise ValueError("scores must be finite numbers between 0 and 100")
        if not isinstance(verdict["summary"], str) or not isinstance(resp.get("claims", []), list):
            raise ValueError("invalid summary or claims")
        counts = [acc.get(key, 0) for key in ("claims_total", "claims_verified", "claims_contradicted")]
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in counts):
            raise ValueError("claim counts must be non-negative integers")
        if counts[1] + counts[2] > counts[0]:
            raise ValueError("inconsistent claim counts")
        for claim in resp.get("claims", []):
            if (not isinstance(claim, dict) or not isinstance(claim.get("text"), str)
                    or not claim["text"].strip() or claim.get("verdict") not in ("supported", "contradicted", "unverifiable")):
                raise ValueError("invalid claim record")
            if claim.get("source") is not None and not isinstance(claim["source"], dict):
                raise ValueError("invalid claim source")
        return Signals(
            tier=verdict["tier"], score=verdict["score"], summary=verdict["summary"],
            accuracy_status=acc["status"], claims_total=acc.get("claims_total", 0),
            claims_verified=acc.get("claims_verified", 0), claims_contradicted=acc.get("claims_contradicted", 0),
            tone=dims["tone"]["score"], bias=dims["bias"]["score"], agreement=dims["agreement"]["score"],
            claims=resp.get("claims", []),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise EzioError("malformed mock response", resp) from e


@lru_cache(maxsize=None)
def load_source_of_truth(persona):
    """Every .json and .csv file in the persona folder, keyed by file name (for example sot['policies'])."""
    data = {}
    for f in sorted((PERSONAS / persona).iterdir()):
        if f.stem in ("practice_set", "business_rules"):
            continue
        if f.suffix == ".json":
            data[f.stem] = json.loads(f.read_text())
        elif f.suffix == ".csv":
            with f.open() as handle:
                data[f.stem] = list(csv.DictReader(handle))
    return data


def check_source_of_truth(text, context, sot):
    """Compatibility adapter; the checker also supplies successful checks and witnesses."""
    return [Finding(**finding) for finding in source_checks.check(text, context, sot)["findings"]]


def apply_policy(signals, findings, policy):
    decision, reasons = APPROVE, []

    def raise_to(level, reason):
        nonlocal decision
        reasons.append(reason)
        if RANK[level] > RANK[decision]:
            decision = level

    for f in findings:
        raise_to(f.level, f.message)
    for claim in signals.claims:
        if claim["verdict"] == "contradicted":
            raise_to(BLOCK, f"Ezio contradicts: {claim['text']}")
        elif claim["verdict"] == "unverifiable":
            raise_to(HOLD, f"Ezio could not verify: {claim['text']}")
    if signals.claims_contradicted:
        raise_to(BLOCK, f"Ezio reports {signals.claims_contradicted} contradicted claim(s)")
    for dim, rule in policy["dimension_minimums"].items():
        score = getattr(signals, dim)
        if score < rule["hold_below"]:
            raise_to(HOLD, f"{dim} score {score} is below {rule['hold_below']}")
    if signals.accuracy_status == "not_scored" and policy["when_accuracy_not_scored"] != "ignore":
        raise_to(policy["when_accuracy_not_scored"], "accuracy was not scored (no claims checked)")
    if signals.accuracy_status == "unavailable":
        raise_to(policy["when_accuracy_unavailable"], "fact-check was unavailable")
    tier_decision = policy["tier_decisions"][signals.tier]
    if tier_decision != APPROVE:
        raise_to(tier_decision, f"Ezio tier is {signals.tier} ({signals.score})")
    if not reasons:
        reasons.append(f"No violation detected in modeled policy checks; Ezio {signals.tier} {signals.score}. This is not a guarantee that all text was verified.")
    return reasons, decision


def decide(text, context=None, persona="customer_support", scenario=None, audit_log=True):
    context = context or {}
    # Local contradictions remain decisive even when an upstream signal is missing.
    try:
        if persona == "customer_support":
            local = source_checks.check(text, context, load_source_of_truth(persona))
        else:
            local = {"findings": [{"level": HOLD, "message": "This build implements independent customer-support checks; other personas need review."}],
                     "checks": [], "counterexamples": []}
    except (OSError, ValueError, KeyError, TypeError) as e:
        local = {"findings": [{"level": HOLD, "message": f"Independent policy check unavailable: {type(e).__name__}"}],
                 "checks": [], "counterexamples": []}
    findings = [Finding(**finding) for finding in local["findings"]]
    checks = list(local["checks"])
    evidence = [f"{c['claim']}: {c['status']}; observed {c['actual']}; expected {c['expected']} ({c['source']})." for c in checks]
    evidence.extend(f.message for f in findings)
    if not checks and not findings:
        evidence.append("No covered company-policy claim was detected; unmatched text was not independently verified.")
    try:
        response = analyze(text, scenario=scenario)
        signals = parse_signals(response)
    except EzioError as e:
        level = max([POLICY["on_ezio_failure"]] + [f.level for f in findings], key=RANK.get)
        reason = "; ".join([f.message for f in findings] + [f"Ezio unavailable: {e}; no upstream clearance."])
        evidence.append(f"Ezio HTTP check failed: {e}; missing evidence requires review.")
        checks.append({"claim": "Ezio availability", "actual": str(e), "expected": "Valid Ezio response", "source": "Ezio HTTP API", "status": "NEEDS_REVIEW"})
        result = Decision(level, reason, evidence, {"error": str(e), "response": e.response},
                          checks=checks, counterexamples=local["counterexamples"])
    else:
        reasons, decision = apply_policy(signals, findings, POLICY)
        for dim, rule in POLICY["dimension_minimums"].items():
            score = getattr(signals, dim)
            checks.append({"claim": f"Ezio {dim}", "actual": score, "expected": f">= {rule['hold_below']}",
                           "source": "Ezio dimensions", "status": "MATCH" if score >= rule["hold_below"] else "NEEDS_REVIEW"})
            evidence.append(f"Ezio {dim}: {score}/100; review below {rule['hold_below']}.")
        evidence.append(f"Ezio accuracy: {signals.accuracy_status}; {signals.claims_verified} supported, {signals.claims_contradicted} contradicted claim(s).")
        for claim in signals.claims:
            source = claim.get("source") or {}
            origin = source.get("publisher") or source.get("url") or "Ezio claims"
            status = {"supported": "MATCH", "contradicted": "CONTRADICTION", "unverifiable": "NEEDS_REVIEW"}[claim["verdict"]]
            checks.append({"claim": claim["text"], "actual": claim["verdict"], "expected": "supported",
                           "source": origin, "status": status})
            evidence.append(f"{claim['text']}: {claim['verdict']} ({origin}).")
        result = Decision(
            decision, "; ".join(reasons), evidence, response,
            checks=checks, counterexamples=local["counterexamples"],
        )
    if audit_log:
        audit.record(persona, text, context, result)
    return result


def gate(text, context=None, persona="customer_support"):
    result = decide(text, context, persona)
    print(f"{result.decision}: {result.reason}")
    if result.decision == APPROVE:
        mock_actions.run_for_persona(persona, text)
    else:
        print("[GATE] action not executed")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit('usage: python3 wrapper.py <persona> "<text>" [context-json]')
    gate(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}, sys.argv[1])
