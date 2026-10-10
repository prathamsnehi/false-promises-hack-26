"""Data-backed customer-support checks and small, inspectable policy proofs.

This module never reads example labels and makes no network calls.  Numeric
comparisons use the supplied CSV/JSON; counterexamples test the stated scope of
a discount against policy boundary customers rather than inventing customers
for an individual entitlement claim.
"""
import itertools
import re


_ONES = dict(zip("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(), range(20)))
_TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10)))
_WORDS = dict(_ONES, **_TENS)
_WORD_NUMBER = re.compile(r"\b(?:" + "|".join(_WORDS) + r")(?:[ -]+(?:hundred|thousand|" + "|".join(_ONES) + r"))?(?:[ -]+and[ -]+(?:" + "|".join(_WORDS) + r"))?\b", re.I)
_NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"


def _number_words(match):
    parts = re.split(r"[ -]+", match.group().lower())
    value = 0
    for part in parts:
        if part == "and":
            continue
        if part == "hundred":
            value *= 100
        elif part == "thousand":
            value *= 1000
        else:
            value += _WORDS.get(part, 0)
    return str(value)


def _normal(text):
    text = text.replace("’", "'").replace("–", "-").replace("—", "-")
    text = _WORD_NUMBER.sub(_number_words, text)
    text = re.sub(r"\bpercent(?:age)?\b", "%", text, flags=re.I)
    return re.sub(r"(?<=\d)\s*%", "%", text).lower()


def _sentences(text):
    return [part.strip() for part in re.split(r"[!?;\n]+|\.(?!\d)", text) if part.strip()]


def _float(value):
    return float(value.replace(",", ""))


def _negated(text, position):
    prefix = text[max(0, position - 48):position]
    return bool(re.search(r"\b(?:not|no|never|cannot|can't|don't|doesn't|isn't|aren't|won't)\b[^,.;]*$", prefix))


def _plan_mentions(text, plans):
    return [(m.start(), name) for name in plans for m in re.finditer(r"\b" + re.escape(name.lower()) + r"\b", text)]


def _nearest_plan(text, position, plans, context=None):
    mentions = _plan_mentions(text, plans)
    if mentions:
        before = [mention for mention in mentions if mention[0] <= position]
        return max(before)[1] if before else min(mentions)[1]
    raw = (context or {}).get("plan")
    return next((name for name in plans if str(raw).lower() == name.lower()), None)


def _personal(text):
    return bool(re.search(r"\b(?:you|your|you're|you've|i qualify|my plan|my discount|this customer)\b", text))


def _tenure_constraint(text):
    """Return the qualification the draft actually states, not the real policy."""
    # More specific forms come first: 'more than' must not become >=.
    patterns = [
        (r"(?:more than|over|longer than)\s+(\d+)\s*(?:months?|mos?)", ">"),
        (r"(?:at least|minimum(?: of)?|no fewer than)\s+(\d+)\s*(?:months?|mos?)", ">="),
        (r"(\d+)\s*\+\s*(?:months?|mos?)", ">="),
        (r"(\d+)\s*(?:months?|mos?)\s*(?:or more|and above|and up|or longer)", ">="),
        (r"(?:less than|under|fewer than)\s+(\d+)\s*(?:months?|mos?)", "<"),
        (r"(?:after|for|with)\s+(\d+)\s*(?:months?|mos?)", ">="),
    ]
    for pattern, op in patterns:
        match = re.search(pattern, text)
        if match:
            return op, int(match.group(1))
    match = re.search(r"(?:at least|after|for|over|more than)\s+(\d+)\s*years?", text)
    if match:
        return (">" if re.search(r"over|more than", match.group()) else ">="), int(match.group(1)) * 12
    if re.search(r"\b(?:at least a year|after a year|a year or more)\b", text):
        return ">=", 12
    return None


def _in_constraint(tenure, constraint):
    if not constraint:
        return True
    op, boundary = constraint
    return {">": tenure > boundary, ">=": tenure >= boundary, "<": tenure < boundary}[op]


def _discount_proof(claim, kind, context, policies, plans, percent=None):
    policy = policies["discounts"][kind]
    minimum = policy.get("min_tenure_months", 0)
    qualifies = _tenure_constraint(claim)
    broad = bool(re.search(r"\b(?:every|all|any|everyone|regardless|no matter|customers|subscribers|users)\b", claim))
    personal = _personal(claim) and not broad
    mentioned = list(dict.fromkeys(name for _, name in sorted(_plan_mentions(claim, plans))))
    # 'eligible/qualifying customers' explicitly incorporates the policy conditions.
    incorporates_policy = bool(re.search(r"\b(?:eligible|qualifying)\s+(?:customers|subscribers|users|plans)\b", claim))
    # Merely stating a rate does not promise it to every possible customer.
    rate_only = not personal and not broad and not mentioned and not re.search(r"\b(?:get|receive|qualify|applies|entitled|anyone)\b", claim)
    incorporates_policy = incorporates_policy or rate_only
    scope = "personalized" if personal else "conditional" if qualifies or incorporates_policy else "universal"
    proof = {"claim": claim, "scope": scope, "customer": {},
             "claimed_benefit": (f"{percent:g}% " if percent is not None else "") + kind.replace("_", " ") + " discount",
             "failed_condition": "", "expected": {"percent": policy["percent"], "plans": policy["applies_to"], "min_tenure_months": minimum},
             "source": "policies.json", "policy_field": "discounts." + kind, "outcome": "none_found"}

    def violation(customer):
        if percent is not None and abs(percent - policy["percent"]) > 0.001:
            return f"discount must be {policy['percent']}%, rather than {percent:g}%"
        if customer["plan"] not in policy["applies_to"]:
            return f"{customer['plan']} is not eligible for {kind.replace('_', ' ')}"
        if customer["customer_tenure_months"] < minimum:
            return f"tenure must be at least {minimum} months; this customer has {customer['customer_tenure_months']}"
        return ""

    if personal:
        raw_plan = context.get("plan")
        actual_plan = next((p for p in plans if str(raw_plan).lower() == p.lower()), None)
        tenure = context.get("customer_tenure_months")
        valid_tenure = isinstance(tenure, (int, float)) and not isinstance(tenure, bool) and tenure >= 0
        if actual_plan is None or (minimum and not valid_tenure):
            proof.update(outcome="insufficient_information", customer=dict(context),
                         failed_condition="Actual customer plan and tenure are required to verify eligibility" if minimum else "Actual customer plan is required to verify eligibility")
            return proof
        customer = {"plan": actual_plan, "customer_tenure_months": tenure if valid_tenure else 0}
        failure = violation(customer)
        proof.update(customer=customer, failed_condition=failure, outcome="counterexample_found" if failure else "none_found")
        return proof

    candidates = mentioned or list(plans)
    if incorporates_policy:
        candidates = [p for p in candidates if p in policy["applies_to"]]
        if not qualifies:
            qualifies = (">=", minimum)
    boundaries = {0, max(0, minimum - 1), minimum, minimum + 1}
    if qualifies:
        boundaries.update((max(0, qualifies[1] - 1), qualifies[1], qualifies[1] + 1))
    # Prefer a useful tenure-only witness over a Starter plan violation.
    customers = [{"plan": p, "customer_tenure_months": t}
                 for p, t in itertools.product(candidates, sorted(boundaries)) if _in_constraint(t, qualifies)]
    customers.sort(key=lambda c: (c["plan"] not in policy["applies_to"], abs(c["customer_tenure_months"] - max(0, minimum - 1)), c["plan"] != "Pro", c["plan"]))
    for customer in customers:
        failure = violation(customer)
        if failure:
            proof.update(customer=customer, failed_condition=failure, outcome="counterexample_found")
            return proof
    if not customers:
        proof.update(outcome="insufficient_information", failed_condition="Could not construct a customer within the draft's stated scope")
    return proof


def check(text, context, sot):
    """Return findings, checked claims, and discount scope counterexamples."""
    context = context or {}
    policies = sot["policies"]
    prices = {row["plan"]: row for row in sot["price_sheet"]}
    plans = list(prices)
    output = {"findings": [], "checks": [], "counterexamples": []}

    def record(claim, actual, expected, source, status, message=None):
        output["checks"].append({"claim": claim, "actual": actual, "expected": expected, "source": source, "status": status})
        if status != "MATCH":
            level = "BLOCK" if status == "CONTRADICTION" else "HOLD_FOR_REVIEW"
            message = message or f"{claim}: draft says {actual}; {source} requires {expected}."
            if not any(f["message"] == message for f in output["findings"]):
                output["findings"].append({"level": level, "message": message})

    for sentence in _sentences(_normal(text)):
        # Discounts are both quantitative claims and eligibility claims.
        discount_kinds = []
        if re.search(r"\bloyalty\b", sentence):
            discount_kinds.append("loyalty")
        if re.search(r"\bannual\b|\byearly\b", sentence) and re.search(r"\bdiscount\b|\boff\b|\bsave\b|\bsaving", sentence):
            discount_kinds.append("annual_billing")
        percentages = list(re.finditer(r"(" + _NUMBER + r")\s*%", sentence))
        for kind in discount_kinds:
            label_pattern = r"\bloyalty\b" if kind == "loyalty" else r"\b(?:annual|yearly)\b"
            label = re.search(label_pattern, sentence)
            eligible_percentages = percentages
            if len(discount_kinds) > 1:
                labels = [(re.search(r"\bloyalty\b", sentence).start(), "loyalty"), (re.search(r"\b(?:annual|yearly)\b", sentence).start(), "annual_billing")]
                eligible_percentages = [m for m in percentages if min(labels, key=lambda item: abs(item[0] - m.start()))[1] == kind]
            percent = _float(eligible_percentages[0].group(1)) if eligible_percentages else None
            negated = _negated(sentence, label.start())
            denial = negated or bool(re.search(r"\b(?:not eligible|ineligible|do not qualify|don't qualify|doesn't qualify|not available)\b", sentence))
            if denial:
                # A denial has no positive entitlement to refute. Verify concrete
                # context when it exists, otherwise preserve the stated limitation.
                proof = _discount_proof(sentence, kind, context, policies, plans, None)
                if proof["scope"] == "personalized" and proof["outcome"] != "insufficient_information":
                    denied_eligible = proof["outcome"] == "none_found"
                    record(sentence, "eligibility denied", "eligible" if denied_eligible else "ineligible", "policies.json", "CONTRADICTION" if denied_eligible else "MATCH")
                continue
            proof = _discount_proof(sentence, kind, context, policies, plans, percent)
            output["counterexamples"].append(proof)
            status = {"none_found": "MATCH", "counterexample_found": "CONTRADICTION", "insufficient_information": "NEEDS_REVIEW"}[proof["outcome"]]
            record(sentence, {"percent": percent, "customer": proof["customer"]}, proof["expected"], "policies.json", status,
                   ("Discount policy: " + proof["failed_condition"] + ". Source: policies.json (" + proof["policy_field"] + ").") if status != "MATCH" else None)
            # Even missing customer metadata cannot rescue a known wrong rate.
            if percent is not None and abs(percent - policies["discounts"][kind]["percent"]) > 0.001 and status == "NEEDS_REVIEW":
                record(sentence, percent, policies["discounts"][kind]["percent"], "policies.json", "CONTRADICTION")

        stacking = re.search(r"\b(?:stack\w*|combin\w*|together|both discounts|additional discount|on top of)\b", sentence)
        if stacking and re.search(r"\bdiscount|\bloyalty|\bannual", sentence):
            denies_stacking = _negated(sentence, stacking.start()) or bool(re.search(r"\b(?:not (?:permitted|allowed)|prohibited|forbidden|cannot|can't)\b", sentence))
            allowed = policies["discounts"]["stacking_allowed"]
            actual = not denies_stacking
            record(sentence, actual, allowed, "policies.json", "MATCH" if actual == allowed else "CONTRADICTION", "Discounts cannot be stacked under policies.json." if actual != allowed else None)

        # Prices: money belongs to the nearest explicitly named plan, not the
        # context plan. Annual per-month prices and annual totals are distinct.
        money = list(re.finditer(r"\$\s*(" + _NUMBER + r")|\b(" + _NUMBER + r")\s*(?:usd|dollars?)\b", sentence))
        for match in money:
            plan = _nearest_plan(sentence, match.start(), plans, context)
            if not plan:
                if re.search(r"\benterprise\b", sentence):
                    record(sentence, match.group(), "custom pricing; contact sales", "policies.json", "CONTRADICTION")
                elif re.search(r"\b(?:plan|subscription|per month|/mo|monthly|per year)\b", sentence):
                    record(sentence, match.group(), "identified plan", "price_sheet.csv", "NEEDS_REVIEW", "A plan is required to verify this price against price_sheet.csv.")
                continue
            if re.search(r"\b(?:refund|credit|compensation|credit card)\b", sentence) and not re.search(r"\b(?:cost|price|per month|/mo|monthly|billed)\b", sentence):
                continue
            actual = _float(match.group(1) or match.group(2))
            following = sentence[match.end():match.end() + 55]
            annual = bool(re.search(r"\b(?:annual|annually|yearly|per year|a year)\b|/yr\b", sentence))
            annual_total = bool(re.search(r"^\s*(?:per year|a year|/year|/yr|annually|yearly)\b", following))
            key = "annual_price_per_month_usd" if annual else "monthly_price_usd"
            expected = float(prices[plan][key]) * (12 if annual_total else 1)
            if not annual and "loyalty" in discount_kinds and re.search(r"\b(?:after|with|including|discounted|pay)\b", sentence):
                expected *= 1 - policies["discounts"]["loyalty"]["percent"] / 100
            record(sentence, actual, round(expected, 2), "price_sheet.csv", "MATCH" if abs(actual - expected) < .011 else "CONTRADICTION",
                   f"{plan} {'annual total' if annual_total else 'annual per-month' if annual else 'monthly'} price is ${expected:.2f}; the draft says ${actual:.2f}. Source: price_sheet.csv." if abs(actual - expected) >= .011 else None)

        # Refund duration and first-payment restriction.
        if re.search(r"\brefund\w*\b", sentence):
            annual = bool(re.search(r"\b(?:annual|yearly)\b", sentence))
            monthly = bool(re.search(r"\bmonthly\b", sentence))
            durations = list(re.finditer(r"(" + _NUMBER + r")\s*[- ]?\s*(days?|weeks?|months?|years?)\b", sentence))
            if re.search(r"\b(?:first|within (?:the )?first)\s+year\b", sentence):
                durations.append(re.search(r"\byear\b", sentence))
            for duration in durations:
                if duration.lastindex:
                    actual = _float(duration.group(1)) * {"day": 1, "week": 7, "month": 30, "year": 365}[duration.group(2).rstrip("s")]
                else:
                    actual = 365
                # Existing account tenure is not itself the promised refund window.
                if _tenure_constraint(sentence[:duration.end()]) and re.search(r"\bcustomer\b", sentence) and not re.search(r"\bwithin|\bwindow|\brefund\w*\s+(?:within|for)\b", sentence):
                    continue
                if annual or monthly:
                    expected = policies["refunds"]["annual_plans_days" if annual else "monthly_plans_days"]
                    record(sentence, actual, expected, "policies.json", "MATCH" if actual == expected else "CONTRADICTION")
                elif actual not in (policies["refunds"]["annual_plans_days"], policies["refunds"]["monthly_plans_days"]):
                    record(sentence, actual, "14 annual / 30 monthly days", "policies.json", "CONTRADICTION")
                else:
                    record(sentence, actual, "billing period required", "policies.json", "NEEDS_REVIEW", "Refund window depends on monthly versus annual billing; specify the billing period.")
            if re.search(r"\b(?:any|every|all|each|renewal|subsequent|second)\s+(?:monthly\s+|annual\s+)?(?:payments?|charges?|invoices?)\b", sentence):
                record(sentence, "refund extends beyond first payment", policies["refunds"]["scope"], "policies.json", "CONTRADICTION")
            if re.search(r"\b(?:any time|anytime|whenever|no time limit|unlimited)\b", sentence) and not durations:
                record(sentence, "unlimited refund window", policies["refunds"], "policies.json", "CONTRADICTION")

        # Trials: plan eligibility, duration, and card requirement.
        if re.search(r"\btrial\b", sentence):
            mentioned = [p for _, p in sorted(_plan_mentions(sentence, plans))]
            trial_plans = list(dict.fromkeys(mentioned)) or ([context["plan"]] if context.get("plan") in plans else [])
            if re.search(r"\b(?:all|every|any)\s+(?:self-serve\s+)?plans?\b", sentence):
                trial_plans = plans
            trial_days = re.search(r"(" + _NUMBER + r")\s*[- ]?\s*(days?|weeks?)\b", sentence)
            no_trial = bool(re.search(r"\b(?:no|not|without|doesn't include|does not include)\s+(?:a\s+|free\s+)*trial\b", sentence))
            if no_trial or trial_days:
                actual = 0 if no_trial else _float(trial_days.group(1)) * (7 if trial_days.group(2).startswith("week") else 1)
                if not trial_plans:
                    record(sentence, actual, "plan required for trial eligibility", "price_sheet.csv", "NEEDS_REVIEW")
                for plan in trial_plans:
                    expected = float(prices[plan]["free_trial_days"])
                    record(sentence, {"plan": plan, "days": actual}, {"plan": plan, "days": expected}, "price_sheet.csv", "MATCH" if actual == expected else "CONTRADICTION")
            if re.search(r"\b(?:credit )?card\b", sentence) and re.search(r"\b(?:required|require|need|necessary|without|no|not)\b", sentence):
                actual = not bool(re.search(r"\b(?:no|without|not required|isn't required|don't need|do not need|not necessary)\b|\bnot\b[^.]*\brequir", sentence))
                expected = policies["free_trial"]["card_required"]
                record(sentence, actual, expected, "policies.json", "MATCH" if actual == expected else "CONTRADICTION")

        if re.search(r"\b(?:first|initial)\s+(?:support\s+)?(?:response|reply)\b|\bresponse (?:time|within)\b", sentence):
            for duration in re.finditer(r"(" + _NUMBER + r")\s*[- ]?\s*(hours?|hrs?|days?|minutes?|mins?)\b", sentence):
                unit = duration.group(2)
                actual = _float(duration.group(1)) * (24 if unit.startswith("day") else 1 / 60 if unit.startswith("min") else 1)
                plan = _nearest_plan(sentence, duration.start(), plans, context)
                if plan:
                    expected = float(prices[plan]["first_response_hours"])
                    record(sentence, actual, expected, "price_sheet.csv", "MATCH" if actual == expected else "CONTRADICTION",
                           f"{plan} first-response commitment is {expected:g} hours, rather than {actual:g}. Source: price_sheet.csv." if actual != expected else None)
                else:
                    record(sentence, actual, "plan required", "price_sheet.csv", "NEEDS_REVIEW")

        product = re.search(r"\b(?:features?|custom export|integrations?|engineering|roadmap|product update)\b", sentence)
        commitment = re.search(r"\b(?:will|we'll|i'll|promise|guarantee|make sure)\b[^.]*\b(?:ships?|deliver|release|launch|add|build|implement|roll out)\b|\b(?:ship|deliver|release|launch)\b[^.]*\b(?:by|next|tomorrow)\b", sentence)
        if product and commitment and not _negated(sentence, commitment.start()):
            record(sentence, "product delivery commitment", "manager authorization required", "policies.json", "NEEDS_REVIEW", "Agents cannot promise product features or delivery dates; manager review is required. Source: policies.json (agent_authority).")
        if re.search(r"\b(?:make an exception|outside (?:the )?policy|override (?:the )?policy|waive (?:the )?(?:rule|requirement)|special exception)\b", sentence) and not re.search(r"\b(?:cannot|can't|not able|won't|will not)\b", sentence):
            record(sentence, "policy exception", "manager authorization required", "policies.json", "NEEDS_REVIEW", "An agent cannot authorize an exception to company policy; manager review is required.")
        if re.search(r"\bamazing news\b|\byou will love\b|\byou'll love\b|\bguaranteed\b", sentence):
            record(sentence, "promotional guarantee", "professional, independent tone", "business_rules.md", "NEEDS_REVIEW", "Promotional guarantees or exaggerated language require manager review.")
    return output
