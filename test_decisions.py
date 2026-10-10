"""Regression tests for decisions, upstream evidence, and outage precedence."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / "wrapper"))
import wrapper
from ezio_client import EzioError


def response(claims=None, accuracy="not_scored", tone=100, bias=100, agreement=100):
    claims = claims or []
    return {"verdict": {"tier": "GREEN", "score": 99, "summary": "Aggregate looks fine"},
            "dimensions": {"accuracy": {"status": accuracy, "score": 100 if accuracy == "scored" else None,
                "claims_total": len(claims), "claims_verified": sum(c["verdict"] == "supported" for c in claims),
                "claims_contradicted": sum(c["verdict"] == "contradicted" for c in claims)},
                "tone": {"score": tone}, "bias": {"score": bias}, "agreement": {"score": agreement}},
            "claims": claims}


class DecisionTests(unittest.TestCase):
    def decide(self, text, context=None, body=None):
        with patch.object(wrapper, "analyze", return_value=body or response()):
            return wrapper.decide(text, context, audit_log=False)

    def test_boundary_same_claim_different_actual_customer(self):
        draft = "You qualify for our 15% loyalty discount on the Pro plan."
        young = self.decide(draft, {"plan": "Pro", "customer_tenure_months": 11})
        eligible = self.decide(draft, {"plan": "Pro", "customer_tenure_months": 12})
        self.assertEqual(young.decision, "BLOCK")
        self.assertEqual(eligible.decision, "APPROVE")
        self.assertTrue(any(c["outcome"] == "counterexample_found" for c in young.counterexamples))
        self.assertTrue(any(c["outcome"] == "none_found" for c in eligible.counterexamples))
        self.assertNotEqual(young.decision_id, eligible.decision_id)

    def test_public_claim_verdicts_override_green_aggregate(self):
        for verdict, expected in (("supported", "APPROVE"), ("contradicted", "BLOCK"), ("unverifiable", "HOLD_FOR_REVIEW")):
            with self.subTest(verdict=verdict):
                body = response([{"text": "A public factual statement.", "verdict": verdict,
                                 "source": {"publisher": "Public reference"}}], "scored")
                result = self.decide("A public factual statement.", body=body)
                self.assertEqual(result.decision, expected)
                self.assertTrue(any("Public reference" in e for e in result.evidence))

    def test_low_individual_dimensions_hold_even_when_green(self):
        for name in ("tone", "bias", "agreement"):
            with self.subTest(dimension=name):
                result = self.decide("Thanks for reaching out.", body=response(**{name: 79}))
                self.assertEqual(result.decision, "HOLD_FOR_REVIEW")
                self.assertIn(name, result.reason)
        self.assertEqual(self.decide("Thanks for reaching out.", body=response(tone=80)).decision, "APPROVE")

    def test_known_contradiction_survives_upstream_outage(self):
        with patch.object(wrapper, "analyze", side_effect=EzioError("HTTP 503")) as analyze:
            bad = wrapper.decide("The Pro plan is $99 per month.", {"plan": "Pro"}, audit_log=False)
            good = wrapper.decide("Thanks for reaching out.", audit_log=False)
        self.assertEqual(bad.decision, "BLOCK")
        self.assertEqual(good.decision, "HOLD_FOR_REVIEW")
        self.assertEqual(analyze.call_count, 2)
        self.assertTrue(bad.evidence and good.evidence)
        self.assertIn("503", bad.reason)

    def test_accuracy_unavailable_holds_without_erasing_local_check(self):
        result = self.decide("The Pro plan is $49 per month.", body=response(accuracy="unavailable"))
        self.assertEqual(result.decision, "HOLD_FOR_REVIEW")
        self.assertTrue(any(c["status"] == "MATCH" and "price_sheet" in c["source"] for c in result.checks))

    def test_malformed_claim_and_count_fail_closed(self):
        bodies = [response(), response()]
        bodies[0]["claims"] = [{"text": "Claim", "verdict": "made_up"}]
        bodies[1]["dimensions"]["accuracy"]["claims_contradicted"] = -1
        for body in bodies:
            with self.subTest(body=body):
                self.assertEqual(self.decide("Thanks for reaching out.", body=body).decision, "HOLD_FOR_REVIEW")

    def test_counterexample_search_has_no_action_side_effect(self):
        with patch.object(wrapper.mock_actions, "run_for_persona") as action:
            result = self.decide("Every customer gets a 15% loyalty discount.")
        self.assertEqual(result.decision, "BLOCK")
        action.assert_not_called()

    def test_approval_has_evidence_and_audits_complete_result(self):
        with patch.object(wrapper, "analyze", return_value=response()), patch.object(wrapper.audit, "record") as record:
            result = wrapper.decide("Thanks for reaching out.")
        self.assertEqual(result.decision, "APPROVE")
        self.assertTrue(result.evidence and result.decision_id and result.checks)
        record.assert_called_once_with("customer_support", "Thanks for reaching out.", {}, result)


if __name__ == "__main__":
    unittest.main()
