"""Reviewer decisions remain separate from the automatic action gate."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "wrapper"))
import audit
import serve


class ReviewTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.log = Path(directory.name) / "audit_log.jsonl"
        log_patch = patch.object(audit, "LOG", self.log)
        log_patch.start()
        self.addCleanup(log_patch.stop)
        action_patch = patch.object(serve.mock_actions, "run_for_persona")
        self.action = action_patch.start()
        self.addCleanup(action_patch.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def record(self, decision_id, decision="HOLD_FOR_REVIEW"):
        audit.record("customer_support", "Please review the feature promise.", {},
                     SimpleNamespace(decision_id=decision_id, decision=decision, reason="Needs manager review",
                                     evidence=["Agent lacks feature authority"], ezio={"raw": "preserved"},
                                     checks=[{"status": "review", "source": "policies.json"}],
                                     counterexamples=[{"change": "Remove the feature promise"}]))

    def request(self, path, payload=None):
        request = urllib.request.Request(self.base + path,
                                         data=None if payload is None else json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_review_persists_and_joins_audit_without_action(self):
        self.record("held-1")
        self.record("good-2", "APPROVE")
        status, result = self.request("/api/reviews", {"decision_id": "held-1", "disposition": "request_revision",
                                                      "note": "Remove the feature promise."})
        self.assertEqual(status, 200)
        event = result["review"]
        self.assertTrue(event["review_id"] and event["timestamp"])
        self.assertEqual(json.loads((self.log.parent / "reviews.jsonl").read_text()), event)
        status, result = self.request("/api/audit")
        self.assertEqual(status, 200)
        entries = result["entries"]
        self.assertEqual([entry["decision_id"] for entry in entries], ["good-2", "held-1"])
        self.assertEqual(entries[0]["reviews"], [])
        self.assertEqual(entries[1]["reviews"], [event])
        self.assertEqual(entries[1]["ezio"], {"raw": "preserved"})
        self.assertTrue(entries[1]["checks"] and entries[1]["counterexamples"])
        self.action.assert_not_called()

    def test_invalid_reviews_and_unheld_decisions_never_write_or_act(self):
        self.record("approved", "APPROVE")
        self.record("blocked", "BLOCK")
        self.record("held")
        base = {"decision_id": "held", "disposition": "reject", "note": "Needs correction"}
        for payload in ([], {}, {**base, "decision_id": 1}, {**base, "note": " "},
                        {**base, "note": "x" * 1001}, {**base, "disposition": "approve"}):
            self.assertEqual(self.request("/api/reviews", payload)[0], 400)
        self.assertEqual(self.request("/api/reviews", {**base, "decision_id": "missing"})[0], 404)
        for decision_id in ("approved", "blocked"):
            self.assertEqual(self.request("/api/reviews", {**base, "decision_id": decision_id})[0], 409)
        self.assertFalse((self.log.parent / "reviews.jsonl").exists())
        self.action.assert_not_called()

    def test_latest_thirty_skip_corrupt_or_partial_lines(self):
        self.assertEqual(self.request("/api/audit")[1], {"entries": []})
        for number in range(35):
            self.record(f"decision-{number}")
        with self.log.open("a") as handle:
            handle.write("not-json\n{\"partial\":")
        entries = self.request("/api/audit")[1]["entries"]
        self.assertEqual(len(entries), 30)
        self.assertEqual(entries[0]["decision_id"], "decision-34")
        self.assertEqual(entries[-1]["decision_id"], "decision-5")

    def test_concurrent_reviews_are_complete_unique_records(self):
        self.record("held")
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda index: self.request("/api/reviews", {
                "decision_id": "held", "disposition": "reject", "note": f"Reviewer note {index}"}), range(8)))
        self.assertTrue(all(status == 200 for status, _ in responses))
        reviews = [json.loads(line) for line in (self.log.parent / "reviews.jsonl").read_text().splitlines()]
        self.assertEqual(len(reviews), 8)
        self.assertEqual(len({review["review_id"] for review in reviews}), 8)
        self.assertEqual(len(self.request("/api/audit")[1]["entries"][0]["reviews"]), 8)
        self.action.assert_not_called()

    def test_nonfinite_context_rejected_before_decision_or_action(self):
        prefix = b'{"text":"You qualify for a loyalty discount.","persona":"customer_support","context":{"plan":"Pro","customer_tenure_months":'
        with patch.object(serve, "decide") as decide:
            for value in (b'NaN', b'Infinity', b'1e999'):
                request = urllib.request.Request(self.base + "/decide", data=prefix + value + b'}}',
                                                 headers={"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 400)
            decide.assert_not_called()
        self.action.assert_not_called()


if __name__ == "__main__":
    unittest.main()
