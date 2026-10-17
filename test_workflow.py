from copy import deepcopy
from dataclasses import asdict
from datetime import date
from pathlib import Path
import json
import unittest

from workflow import Request, fixture_lookup, route_request, run_cases


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = json.loads(Path(__file__).with_name("fixtures.json").read_text())
        self.request = Request("test", "customer-a", date(2026, 8, 12))
        self.proposal = {"intent": "refund", "order_id": "ord-101"}

    def route(self, proposal=None, **order_changes):
        orders = deepcopy(self.fixtures["orders"])
        orders["ord-101"].update(order_changes)
        return route_request(self.request, self.proposal if proposal is None else proposal, fixture_lookup(orders))

    def test_fixture_outcomes_and_required_checkpoints(self):
        for case, result in zip(self.fixtures["cases"], run_cases(self.fixtures), strict=True):
            with self.subTest(case=case["id"]):
                self.assertEqual([result["state"], result["reason"]], case["expected"])
                if result["state"] == "review_ready":
                    self.assertEqual(result["trace"], (
                        "request_received", "proposal_validated", "order_read",
                        "ownership_checked", "policy_checked", "review_ready",
                    ))
                    self.assertEqual(result["review_packet"]["policy_version"], "example-v1")
                else:
                    self.assertIsNone(result["review_packet"])

    def test_window_and_amount_boundaries_are_inclusive(self):
        self.assertEqual(self.route(delivered_on="2026-07-29", amount_minor=5000).state, "review_ready")
        self.assertEqual(self.route(delivered_on="2026-07-28").state, "manual_review")
        self.assertEqual(self.route(amount_minor=5001).state, "manual_review")
        self.assertEqual(self.route(delivered_on="2026-08-13").state, "manual_review")

    def test_proposal_cannot_supply_authority_or_trusted_values(self):
        for key, value in {"customer_id": "customer-b", "approved": True, "amount_minor": 1, "policy_version": "bypass"}.items():
            with self.subTest(key=key):
                result = self.route(proposal={**self.proposal, key: value})
                self.assertEqual(result.reason, "invalid_proposal")
                self.assertNotIn("order_read", result.trace)

    def test_wrong_customer_and_unknown_order_are_indistinguishable(self):
        wrong = self.route(proposal={**self.proposal, "order_id": "ord-102"})
        unknown = self.route(proposal={**self.proposal, "order_id": "not-an-order"})
        self.assertEqual(asdict(wrong), asdict(unknown))

    def test_malformed_proposals_stop_before_lookup(self):
        def forbidden_lookup(_):
            self.fail("Invalid proposal reached order lookup")
        for proposal in (None, [], {}, {"intent": "refund"}, {"intent": "refund", "order_id": 101}, {"intent": "refund", "order_id": " "}):
            with self.subTest(proposal=proposal):
                result = route_request(self.request, proposal, forbidden_lookup)
                self.assertEqual(result.reason, "invalid_proposal")

    def test_bad_records_do_not_create_review_packets(self):
        for patch in ({"amount_minor": True}, {"amount_minor": -1}, {"delivered_on": "bad-date"}, {"customer_id": None}, {"order_id": "mismatched"}, {"status": "pending"}):
            with self.subTest(patch=patch):
                self.assertIsNone(self.route(**patch).review_packet)

    def test_packet_uses_record_values_and_preserves_ledger(self):
        before = deepcopy(self.fixtures["orders"])
        result = route_request(self.request, self.proposal, fixture_lookup(self.fixtures["orders"]))
        self.assertEqual(result.review_packet["amount_minor"], 2400)
        self.assertEqual(result.review_packet["evidence"]["age_days"], 7)
        self.assertEqual(self.fixtures["orders"], before)

    def test_external_failure_does_not_become_rejection(self):
        for failure in ("timeout", "connection"):
            result = route_request(self.request, self.proposal, fixture_lookup({}, failure))
            self.assertEqual(result.state, "waiting_for_system")
            self.assertIsNone(result.review_packet)


if __name__ == "__main__":
    unittest.main()
