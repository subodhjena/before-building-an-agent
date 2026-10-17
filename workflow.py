"""A read-only workflow boundary around untrusted candidate model output.

Python 3.11+, standard library only. No model, network, payment, or message API.
"""

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Callable
import json


@dataclass(frozen=True)
class Request:
    case_id: str
    customer_id: str  # Supplied by a trusted caller, never by the model proposal.
    as_of: date


@dataclass(frozen=True)
class Policy:
    version: str = "example-v1"
    window_days: int = 14
    max_amount_minor: int = 5000
    currency: str = "USD"


@dataclass(frozen=True)
class Result:
    state: str
    reason: str
    trace: tuple[str, ...]
    review_packet: dict | None = None


def valid_proposal(proposal: object) -> bool:
    if not isinstance(proposal, dict):
        return False
    if set(proposal) != {"intent", "order_id"}:
        return False
    if proposal["intent"] not in ("refund", "other", "unclear"):
        return False
    order_id = proposal["order_id"]
    return order_id is None or (isinstance(order_id, str) and bool(order_id.strip()))


def valid_order(order: object) -> bool:
    if not isinstance(order, dict):
        return False
    for key in ("order_id", "customer_id", "currency", "status", "delivered_on"):
        if not isinstance(order.get(key), str):
            return False
    # A bool is an int subclass in Python, but is not a valid monetary amount.
    if type(order.get("amount_minor")) is not int or order["amount_minor"] <= 0:
        return False
    try:
        date.fromisoformat(order["delivered_on"])
    except ValueError:
        return False
    return True


def route_request(
    request: Request,
    proposal: object,
    lookup_order: Callable[[str], dict | None],
    policy: Policy = Policy(),
) -> Result:
    trace = ["request_received"]

    def finish(state: str, reason: str, packet: dict | None = None) -> Result:
        return Result(state, reason, tuple([*trace, state]), packet)

    if not valid_proposal(proposal):
        return finish("manual_review", "invalid_proposal")
    trace.append("proposal_validated")
    if proposal["intent"] != "refund":
        return finish("manual_review", "intent_needs_review")
    if proposal["order_id"] is None:
        return finish("needs_information", "order_unavailable")

    try:
        order = lookup_order(proposal["order_id"])
    except (TimeoutError, ConnectionError):
        return finish("waiting_for_system", "order_lookup_failed")
    trace.append("order_read")

    # Unknown and inaccessible identifiers produce the same outward result.
    if order is None:
        return finish("needs_information", "order_unavailable")
    if not valid_order(order):
        return finish("manual_review", "invalid_order_record")
    if (
        order["order_id"] != proposal["order_id"]
        or order["customer_id"] != request.customer_id
    ):
        return finish("needs_information", "order_unavailable")
    trace.append("ownership_checked")

    if order["status"] == "refunded":
        return finish("no_action", "already_refunded")
    if order["status"] != "delivered":
        return finish("manual_review", "status_needs_review")

    age_days = (request.as_of - date.fromisoformat(order["delivered_on"])).days
    if not 0 <= age_days <= policy.window_days:
        return finish("manual_review", "outside_example_window")
    if order["currency"] != policy.currency:
        return finish("manual_review", "currency_needs_review")
    if order["amount_minor"] > policy.max_amount_minor:
        return finish("manual_review", "above_example_limit")
    trace.append("policy_checked")

    packet = {
        "case_id": request.case_id,
        "customer_id": request.customer_id,
        "order_id": order["order_id"],
        "amount_minor": order["amount_minor"],
        "currency": order["currency"],
        "policy_version": policy.version,
        "evidence": {"delivered_on": order["delivered_on"], "age_days": age_days},
    }
    return finish("review_ready", "within_example_policy", packet)


def fixture_lookup(orders: dict, failure: str | None = None) -> Callable:
    def lookup(order_id: str) -> dict | None:
        if failure == "timeout":
            raise TimeoutError("Synthetic timeout")
        if failure == "connection":
            raise ConnectionError("Synthetic connection failure")
        return orders.get(order_id)
    return lookup


def run_cases(fixtures: dict) -> list[dict]:
    results = []
    for case in fixtures["cases"]:
        request = Request(case["id"], case["customer_id"], date.fromisoformat(fixtures["as_of"]))
        result = route_request(
            request,
            case["proposal"],
            fixture_lookup(fixtures["orders"], case.get("lookup_failure")),
        )
        results.append({"case_id": case["id"], **asdict(result)})
    return results


if __name__ == "__main__":
    fixtures = json.loads(Path(__file__).with_name("fixtures.json").read_text())
    results = run_cases(fixtures)
    for result in results:
        print(f"{result['case_id']}: {result['state']} ({result['reason']})")
    Path("results.json").write_text(json.dumps(results, indent=2) + "\n")
