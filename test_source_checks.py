"""Meaningful source-check regressions, with new wording and boundary scopes."""
import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "wrapper"))
from source_checks import check


class SourceCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = ROOT / "personas" / "customer_support"
        with (folder / "price_sheet.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        cls.sot = {"policies": json.loads((folder / "policies.json").read_text()), "price_sheet": rows}

    def check(self, text, context=None):
        return check(text, context or {}, self.sot)

    def decision(self, text, context=None):
        result = self.check(text, context)
        levels = [finding["level"] for finding in result["findings"]]
        return "BLOCK" if "BLOCK" in levels else "HOLD_FOR_REVIEW" if levels else "APPROVE"

    def test_ordinary_updates_do_not_become_product_commitments(self):
        self.assertEqual(self.decision("I'll send your billing update tomorrow morning."), "APPROVE")
        self.assertEqual(self.decision("We will deliver the requested integration next Tuesday."), "HOLD_FOR_REVIEW")
        self.assertEqual(self.decision("I will send engineering your feature request."), "APPROVE")

    def test_data_driven_prices_and_explicit_plan(self):
        self.assertEqual(self.decision("Business costs ninety-nine dollars per month.", {"plan": "Starter"}), "APPROVE")
        self.assertEqual(self.decision("Business costs eighty-nine dollars per month.", {"plan": "Starter"}), "BLOCK")
        self.assertEqual(self.decision("Pro costs $39.20 per month when billed annually."), "APPROVE")
        self.assertEqual(self.decision("Pro costs $470.40 per year."), "APPROVE")
        self.assertEqual(self.decision("Pro costs $49 a year."), "BLOCK")
        changed = {**self.sot, "price_sheet": [dict(row, monthly_price_usd="101") if row["plan"] == "Business" else row for row in self.sot["price_sheet"]]}
        self.assertEqual(check("Business costs $101/mo.", {}, changed)["findings"], [])

    def test_multiple_claims_and_multiple_plans(self):
        self.assertEqual(self.decision("Pro is $49/mo and Business is $99/mo."), "APPROVE")
        result = self.check("Business costs $99/mo and the first response arrives within twenty-four hours.")
        self.assertTrue(any(c["status"] == "MATCH" for c in result["checks"]))
        self.assertTrue(any(c["status"] == "CONTRADICTION" for c in result["checks"]))
        self.assertEqual(self.decision("Business is $99/mo, with an initial reply within two hundred forty minutes."), "APPROVE")
        self.assertEqual(self.decision("Business includes a fourteen-day trial and a first response within four hours."), "APPROVE")
        self.assertEqual(self.decision("Business has a first response within four hours and a fourteen-day trial."), "APPROVE")

    def test_personalized_eligibility_uses_only_actual_customer(self):
        draft = "You qualify for the fifteen percent loyalty discount."
        self.assertEqual(self.decision(draft, {"plan": "Pro", "customer_tenure_months": 12}), "APPROVE")
        self.assertEqual(self.decision(draft, {"plan": "Pro", "customer_tenure_months": 11}), "BLOCK")
        self.assertEqual(self.decision(draft, {"plan": "Starter", "customer_tenure_months": 99}), "BLOCK")
        self.assertEqual(self.decision(draft, {"plan": "Pro"}), "HOLD_FOR_REVIEW")
        for tenure in (True, -1, "twelve", float("inf")):
            self.assertEqual(self.decision(draft, {"plan": "Pro", "customer_tenure_months": tenure}), "HOLD_FOR_REVIEW")
        # An eligible individual cannot rescue an overbroad promise.
        broad = self.check("All Pro customers receive a 15% loyalty discount.", {"plan": "Pro", "customer_tenure_months": 50})
        self.assertEqual(broad["counterexamples"][0]["customer"], {"plan": "Pro", "customer_tenure_months": 11})
        self.assertEqual(broad["counterexamples"][0]["scope"], "universal")

    def test_universal_scope_prefers_tenure_only_witness(self):
        result = self.check("Every customer receives the 15% loyalty discount, regardless of tenure.")
        proof = result["counterexamples"][0]
        self.assertEqual(proof["outcome"], "counterexample_found")
        self.assertEqual(proof["customer"], {"plan": "Pro", "customer_tenure_months": 11})
        self.assertIn("tenure", proof["failed_condition"])

    def test_conditional_scopes_are_respected(self):
        good = "All Pro and Business customers with at least twelve months receive our 15% loyalty discount."
        result = self.check(good)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["counterexamples"][0]["scope"], "conditional")
        self.assertEqual(result["counterexamples"][0]["outcome"], "none_found")
        self.assertEqual(self.decision("All Pro customers with at least eleven months get a 15% loyalty discount."), "BLOCK")
        self.assertEqual(self.decision("All Starter customers with at least twelve months get a 15% loyalty discount."), "BLOCK")
        self.assertEqual(self.decision("Eligible customers receive our 15% loyalty discount."), "APPROVE")
        self.assertEqual(self.decision("The loyalty discount is fifteen percent."), "APPROVE")
        self.assertEqual(self.decision("All Pro customers with at least a twelve-month tenure get 15% loyalty discount."), "APPROVE")

    def test_discount_rate_and_stacking_negation(self):
        self.assertEqual(self.decision("Your loyalty discount is sixteen percent.", {"plan": "Pro", "customer_tenure_months": 12}), "BLOCK")
        self.assertEqual(self.decision("You cannot combine loyalty and annual discounts."), "APPROVE")
        self.assertEqual(self.decision("You can combine loyalty and annual discounts.", {"plan": "Pro", "customer_tenure_months": 12}), "BLOCK")
        self.assertEqual(self.decision("Annual billing saves twenty percent on every self-serve plan."), "APPROVE")
        combined = self.check("You can combine loyalty and annual discounts.", {"plan": "Pro", "customer_tenure_months": 12})
        self.assertTrue(any(p["policy_field"] == "discounts.stacking_allowed" and p["outcome"] == "counterexample_found" for p in combined["counterexamples"]))
        self.assertEqual(self.decision("Loyalty and annual discounts cannot be combined."), "APPROVE")

    def test_ambiguous_discount_is_reviewed_and_enterprise_is_known(self):
        self.assertEqual(self.decision("You get a discount.", {"plan": "Pro", "customer_tenure_months": 12}), "HOLD_FOR_REVIEW")
        self.assertEqual(self.decision("Your loyalty discount is 15%.", {"plan": "Enterprise", "customer_tenure_months": 20}), "BLOCK")
        self.assertEqual(self.decision("Your loyalty discount is 15%.", {"plan": "Enterprise"}), "BLOCK")
        self.assertEqual(self.decision("As one of our customers, you receive a 15% loyalty discount.", {"plan": "Pro", "customer_tenure_months": 20}), "APPROVE")

    def test_billing_period_belongs_to_each_price(self):
        self.assertEqual(self.decision("Pro is $49 monthly or $39.20/month billed annually."), "APPROVE")
        self.assertEqual(self.decision("Pro is $49 monthly or $39.00/month billed annually."), "BLOCK")
        self.assertEqual(self.decision("Starter costs fifteen dollars and twenty cents per month billed annually."), "APPROVE")

    def test_separate_discount_clause_does_not_change_price_period(self):
        for plan, monthly, annual in (("Starter", 19, 15.20), ("Pro", 49, 39.20)):
            with self.subTest(plan=plan):
                self.assertEqual(self.decision(f"{plan} costs ${monthly}/month, and annual billing saves 20%."), "APPROVE")
                self.assertEqual(self.decision(f"Yearly billing saves 20%, and {plan} costs ${monthly} monthly."), "APPROVE")
                self.assertEqual(self.decision(f"{plan} costs ${monthly - 1}/month, and annual billing saves 20%."), "BLOCK")
                self.assertEqual(self.decision(f"{plan} costs ${annual:.2f}/month billed annually and includes support."), "APPROVE")
                self.assertEqual(self.decision(f"{plan} costs ${annual:.2f}/month, billed annually."), "APPROVE")
                self.assertEqual(self.decision(f"Billed annually, {plan} costs ${annual:.2f}/month."), "APPROVE")
                self.assertEqual(self.decision(f"{plan} costs ${monthly}/month billed annually and includes support."), "BLOCK")

    def test_universal_annual_discounts_include_enterprise_unless_scoped(self):
        self.assertEqual(self.decision("Every customer receives a 20% annual billing discount."), "BLOCK")
        self.assertEqual(self.decision("Every self-serve customer receives a 20% annual billing discount."), "APPROVE")
        self.assertEqual(self.decision("Enterprise customers receive a 20% annual billing discount."), "BLOCK")
        self.assertEqual(self.decision("Your loyalty discount is thirty per cent.", {"plan": "Pro", "customer_tenure_months": 20}), "BLOCK")

    def test_refund_period_scope_and_exceptions(self):
        self.assertEqual(self.decision("A refund is available within two weeks of the first annual payment."), "APPROVE")
        self.assertEqual(self.decision("A refund is available within four weeks of the first annual payment."), "BLOCK")
        self.assertEqual(self.decision("We refund every monthly payment within thirty days."), "BLOCK")
        self.assertEqual(self.decision("I'll make an exception to our refund policy."), "HOLD_FOR_REVIEW")

    def test_trial_duration_eligibility_and_cards(self):
        self.assertEqual(self.decision("Pro comes with a two-week free trial; no credit card is required."), "APPROVE")
        self.assertEqual(self.decision("All plans include a fourteen-day free trial."), "BLOCK")
        self.assertEqual(self.decision("Starter comes with a free trial lasting fourteen days."), "BLOCK")
        self.assertEqual(self.decision("Starter has no free trial."), "APPROVE")
        self.assertEqual(self.decision("The Pro free trial requires a credit card."), "BLOCK")
        self.assertEqual(self.decision("Starter includes a free trial."), "BLOCK")
        self.assertEqual(self.decision("Pro includes a free trial."), "APPROVE")
        self.assertEqual(self.decision("Pro offers a fourteen-day trial; a credit card is required."), "BLOCK")

    def test_public_knowledge_is_left_for_ezio(self):
        self.assertEqual(self.decision("We received your GDPR deletion request."), "APPROVE")
        self.assertEqual(self.decision("Please find the billing attachment."), "APPROVE")


if __name__ == "__main__":
    unittest.main()
