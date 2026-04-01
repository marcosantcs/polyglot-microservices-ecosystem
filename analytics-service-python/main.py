"""
AnalyticsService — consumes order events from RabbitMQ and exposes metrics via FastAPI.
"""
import json
import logging
import os
import threading
from datetime import datetime
from collections import defaultdict

import pika
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# ── Configuration ─────────────────────────────────────────────────────────────
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
EXCHANGE      = "orders.exchange"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
log = logging.getLogger("analytics-service")

# ── In-memory analytics store ─────────────────────────────────────────────────
analytics: dict = {
    "total_orders":    0,
    "total_revenue":   0.0,
    "cancelled_orders": 0,
    "orders_by_customer": defaultdict(int),
    "recent_events":   []          # last 20 events
}

app = FastAPI(title="AnalyticsService", version="1.0.0")

# ── Event handlers ─────────────────────────────────────────────────────────────
def handle_order_created(data: dict) -> None:
    analytics["total_orders"]  += 1
    analytics["total_revenue"] += data.get("Total", 0)
    cid = data.get("CustomerId", "unknown")
    analytics["orders_by_customer"][cid] += 1
    log.info(
        "✅ ORDER CREATED | id=%s | customer=%s | total=R$%.2f | items=%d",
        data.get("OrderId"),
        cid,
        data.get("Total", 0),
        len(data.get("Items", []))
    )
    _append_event("order.created", data)


def handle_order_cancelled(data: dict) -> None:
    analytics["cancelled_orders"] += 1
    log.warning(
        "❌ ORDER CANCELLED | id=%s | reason=%s",
        data.get("OrderId"),
        data.get("Reason", "N/A")
    )
    _append_event("order.cancelled", data)


def _append_event(event_type: str, data: dict) -> None:
    analytics["recent_events"].insert(0, {
        "event":     event_type,
        "data":      data,
        "processed": datetime.utcnow().isoformat()
    })
    analytics["recent_events"] = analytics["recent_events"][:20]


HANDLERS = {
    "order.created":   handle_order_created,
    "order.cancelled": handle_order_cancelled,
}

# ── RabbitMQ consumer ─────────────────────────────────────────────────────────
def on_message(ch, method, properties, body):
    try:
        routing_key = method.routing_key
        data        = json.loads(body)
        handler     = HANDLERS.get(routing_key)

        if handler:
            handler(data)
        else:
            log.warning("No handler for routing key: %s", routing_key)

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        log.error("Failed to process message: %s", exc)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer() -> None:
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params      = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )

    while True:
        try:
            connection = pika.BlockingConnection(params)
            channel    = connection.channel()

            channel.exchange_declare(
                exchange=EXCHANGE, exchange_type="topic",
                durable=True, auto_delete=False
            )

            # Bind to all order events
            result = channel.queue_declare(
                queue="analytics.orders",
                durable=True,
                arguments={"x-dead-letter-exchange": f"{EXCHANGE}.dlx"}
            )
            channel.queue_bind(result.method.queue, EXCHANGE, "order.*")
            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=result.method.queue, on_message_callback=on_message)

            log.info("🐇 RabbitMQ consumer started — waiting for events on '%s'", EXCHANGE)
            channel.start_consuming()

        except Exception as exc:
            log.error("RabbitMQ connection lost: %s — retrying in 5s…", exc)
            import time; time.sleep(5)


# ── FastAPI endpoints ─────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "analytics-service"}

@app.get("/metrics")
def metrics():
    return JSONResponse({
        "total_orders":     analytics["total_orders"],
        "total_revenue":    round(analytics["total_revenue"], 2),
        "cancelled_orders": analytics["cancelled_orders"],
        "top_customers":    dict(
            sorted(analytics["orders_by_customer"].items(), key=lambda x: -x[1])[:5]
        )
    })

@app.get("/events/recent")
def recent_events():
    return analytics["recent_events"]


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
