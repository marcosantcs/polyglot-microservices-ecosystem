"""
Unit tests for AnalyticsService event handlers.
All tests run without RabbitMQ or network — pure unit tests.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collections import defaultdict
import pytest

# ── Reset analytics state before each test ────────────────────────────────────
import main as svc

@pytest.fixture(autouse=True)
def reset_analytics():
    svc.analytics["total_orders"]       = 0
    svc.analytics["total_revenue"]      = 0.0
    svc.analytics["cancelled_orders"]   = 0
    svc.analytics["orders_by_customer"] = defaultdict(int)
    svc.analytics["recent_events"]      = []
    yield

# ── handle_order_created ──────────────────────────────────────────────────────
class TestHandleOrderCreated:

    def test_increments_total_orders(self):
        svc.handle_order_created({"OrderId": "1", "CustomerId": "c1", "Total": 100.0, "Items": []})
        assert svc.analytics["total_orders"] == 1

    def test_accumulates_revenue(self):
        svc.handle_order_created({"OrderId": "1", "CustomerId": "c1", "Total": 1000.0, "Items": []})
        svc.handle_order_created({"OrderId": "2", "CustomerId": "c1", "Total":  500.0, "Items": []})
        assert svc.analytics["total_revenue"] == 1500.0

    def test_tracks_customer_orders(self):
        svc.handle_order_created({"OrderId": "1", "CustomerId": "c1", "Total": 100.0, "Items": []})
        svc.handle_order_created({"OrderId": "2", "CustomerId": "c1", "Total": 200.0, "Items": []})
        svc.handle_order_created({"OrderId": "3", "CustomerId": "c2", "Total":  50.0, "Items": []})
        assert svc.analytics["orders_by_customer"]["c1"] == 2
        assert svc.analytics["orders_by_customer"]["c2"] == 1

    def test_appends_to_recent_events(self):
        svc.handle_order_created({"OrderId": "1", "CustomerId": "c1", "Total": 100.0, "Items": []})
        assert len(svc.analytics["recent_events"]) == 1
        assert svc.analytics["recent_events"][0]["event"] == "order.created"

    def test_recent_events_capped_at_20(self):
        for i in range(25):
            svc.handle_order_created({"OrderId": str(i), "CustomerId": "c1", "Total": 10.0, "Items": []})
        assert len(svc.analytics["recent_events"]) == 20

    def test_missing_total_defaults_to_zero(self):
        svc.handle_order_created({"OrderId": "1", "CustomerId": "c1", "Items": []})
        assert svc.analytics["total_revenue"] == 0.0

    def test_unknown_customer_defaults_to_unknown(self):
        svc.handle_order_created({"OrderId": "1", "Total": 50.0, "Items": []})
        assert svc.analytics["orders_by_customer"]["unknown"] == 1


# ── handle_order_cancelled ────────────────────────────────────────────────────
class TestHandleOrderCancelled:

    def test_increments_cancelled_orders(self):
        svc.handle_order_cancelled({"OrderId": "1", "Reason": "Customer request"})
        assert svc.analytics["cancelled_orders"] == 1

    def test_multiple_cancellations_accumulate(self):
        svc.handle_order_cancelled({"OrderId": "1", "Reason": "A"})
        svc.handle_order_cancelled({"OrderId": "2", "Reason": "B"})
        assert svc.analytics["cancelled_orders"] == 2

    def test_appends_to_recent_events(self):
        svc.handle_order_cancelled({"OrderId": "1", "Reason": "Test"})
        assert svc.analytics["recent_events"][0]["event"] == "order.cancelled"

    def test_does_not_affect_total_orders(self):
        svc.handle_order_cancelled({"OrderId": "1", "Reason": "Test"})
        assert svc.analytics["total_orders"] == 0

    def test_does_not_affect_total_revenue(self):
        svc.handle_order_cancelled({"OrderId": "1", "Reason": "Test"})
        assert svc.analytics["total_revenue"] == 0.0


# ── _append_event ─────────────────────────────────────────────────────────────
class TestAppendEvent:

    def test_event_has_required_fields(self):
        svc._append_event("order.created", {"OrderId": "x"})
        event = svc.analytics["recent_events"][0]
        assert "event"     in event
        assert "data"      in event
        assert "processed" in event

    def test_most_recent_event_is_first(self):
        svc._append_event("order.created",   {"OrderId": "1"})
        svc._append_event("order.cancelled", {"OrderId": "2"})
        assert svc.analytics["recent_events"][0]["event"] == "order.cancelled"
