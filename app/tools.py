"""Safe, deterministic local tools used by the included support-agent benchmark.

These tools are intentionally read-only or computational. They are examples of
an application tool registry; replace their implementations with approved
business APIs when evaluating a real workflow.
"""
from __future__ import annotations

import json
from typing import Any

ORDERS: dict[str, dict[str, Any]] = {
    "ORD-1042": {
        "order_id": "ORD-1042",
        "status": "delivered",
        "amount": 80.00,
        "currency": "USD",
        "days_since_delivery": 12,
        "item": "Wireless keyboard",
    },
    "ORD-2048": {
        "order_id": "ORD-2048",
        "status": "shipped",
        "amount": 129.99,
        "currency": "USD",
        "days_since_delivery": None,
        "item": "USB-C dock",
        "estimated_delivery": "November 2, 2026",
    },
    "ORD-3091": {
        "order_id": "ORD-3091",
        "status": "delayed",
        "amount": 44.50,
        "currency": "USD",
        "days_since_delivery": None,
        "item": "Laptop stand",
        "estimated_delivery": "November 4, 2026",
        "delay_reason": "regional weather disruption",
    },
}

POLICIES: dict[str, str] = {
    "returns": "Returns are accepted within 30 calendar days of delivery. Items must be unused and in original packaging.",
    "refunds": "Eligible returns requested within 30 calendar days of delivery receive a refund to the original payment method. Refund processing normally takes 5–7 business days after the return is received.",
    "shipping": "Standard shipping estimates are shown on the order record. Weather and carrier disruptions can delay delivery. Do not promise a compensation amount unless an approved policy explicitly allows it.",
    "privacy": "Never request a customer's password, full payment-card number, or one-time passcode. Verify an order using the order ID and the registered email address.",
}

TOOL_DESCRIPTIONS = {
    "lookup_order": {
        "description": "Look up a read-only order record by order ID. Use when the user asks about a specific order, delivery, or purchase amount.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Order identifier, for example ORD-2048."}},
            "required": ["order_id"],
        },
    },
    "get_policy": {
        "description": "Retrieve the approved support policy for returns, refunds, shipping, or privacy. Use this instead of guessing a policy.",
        "parameters": {
            "type": "object",
            "properties": {"topic": {"type": "string", "enum": ["returns", "refunds", "shipping", "privacy"], "description": "Policy topic."}},
            "required": ["topic"],
        },
    },
    "calculate_refund": {
        "description": "Calculate refund eligibility and amount under the simple benchmark policy: full refund within 30 days; not eligible after 30 days. This is a deterministic benchmark tool, not a payment action.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Original order amount."},
                "days_since_delivery": {"type": "integer", "description": "Calendar days since delivery."},
            },
            "required": ["amount", "days_since_delivery"],
        },
    },
}


def execute_tool(name: str, arguments: dict[str, Any] | str | None) -> dict[str, Any]:
    """Run one allow-listed tool and return a serializable result."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}

    if name == "lookup_order":
        order_id = str(arguments.get("order_id", "")).strip().upper()
        order = ORDERS.get(order_id)
        if not order:
            return {"ok": False, "error": f"No order found for {order_id or '(empty ID)'}"}
        return {"ok": True, "order": order}

    if name == "get_policy":
        topic = str(arguments.get("topic", "")).strip().lower()
        if topic not in POLICIES:
            return {"ok": False, "error": "Unknown policy topic. Available: returns, refunds, shipping, privacy."}
        return {"ok": True, "topic": topic, "policy": POLICIES[topic]}

    if name == "calculate_refund":
        try:
            amount = float(arguments["amount"])
            days = int(arguments["days_since_delivery"])
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": "amount and days_since_delivery must be numeric."}
        if amount < 0 or amount > 1_000_000 or days < 0 or days > 3650:
            return {"ok": False, "error": "The supplied amount or day count is outside the allowed range."}
        eligible = days <= 30
        return {
            "ok": True,
            "eligible": eligible,
            "refund_amount": round(amount, 2) if eligible else 0.0,
            "currency": "USD",
            "reason": "Within the 30-day return window." if eligible else "Outside the 30-day return window.",
        }

    return {"ok": False, "error": f"Tool '{name}' is not allow-listed."}
