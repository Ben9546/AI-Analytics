from fastapi import FastAPI
import asyncio
import json
from typing import List, Dict, Any

# Attempt to use the shared mock Redis client from data-ingestion
# This highlights the need for a proper shared Redis client/library in a real setup.
try:
    from ..data_ingestion.main import mock_redis_client as shared_mock_redis
    print("NotificationService: Successfully accessed shared MockRedis from data-ingestion.")
except ImportError:
    print("NotificationService: Failed to import shared MockRedis. Using a local instance (alerts won't be received from Analytics Engine unless it also uses a local/different mock).")
    # Fallback to a local mock if direct import fails
    class LocalMockRedis:
        def __init__(self): self.queues = {}
        def lpop(self, queue_name): return self.queues.get(queue_name, []).pop(0) if self.queues.get(queue_name) else None
        def rpush(self, queue_name, data): self.queues.setdefault(queue_name, []).append(data)
        def llen(self, queue_name): return len(self.queues.get(queue_name, []))
    shared_mock_redis = LocalMockRedis()


ALERT_QUEUE = "alerts_queue" # Consumes from this queue
processed_alerts_log: List[Dict[str, Any]] = [] # In-memory log of processed alerts

app = FastAPI(title="Notification Service")

async def alert_consumer():
    """
    Continuously polls the ALERT_QUEUE and processes alerts.
    In a real system, this would trigger actual notifications (email, SMS, etc.).
    """
    print("NotificationService: Alert Consumer started. Waiting for alerts...")
    while True:
        try:
            alert_json = shared_mock_redis.lpop(ALERT_QUEUE)
            if alert_json:
                alert_data = json.loads(alert_json)
                print(f"NotificationService: Received alert: {alert_data}")

                # --- Actual Notification Logic Would Go Here ---
                # Example: Send an email, push notification, log to a dedicated system.
                # For now, we just log it to our in-memory list.
                processed_alerts_log.append({
                    "received_at": asyncio.to_thread(lambda: __import__('datetime').datetime.utcnow().isoformat()),
                    "alert_content": alert_data
                })
                print(f"NotificationService: Alert processed and logged. Alert type: {alert_data.get('type')}")
                # ---------------------------------------------
            else:
                # Sleep briefly if queue is empty
                await asyncio.sleep(2) # Poll every 2 seconds
        except Exception as e:
            print(f"NotificationService: Error in alert_consumer: {e}")
            await asyncio.sleep(5) # Wait longer on error


@app.on_event("startup")
async def startup_event():
    # Start the alert consumer in the background
    print("NotificationService: Starting background alert consumer...")
    asyncio.create_task(alert_consumer())

@app.get("/")
async def root():
    return {"message": "Notification Service is running. Consuming alerts. Use /docs for API details."}

@app.get("/processed-alerts")
async def get_processed_alerts():
    """Returns a log of alerts processed by this service instance."""
    return {"processed_alerts": processed_alerts_log}

@app.get("/alert-queue-status")
async def get_alert_queue_status():
    """Checks the status (length) of the ALERT_QUEUE."""
    length = shared_mock_redis.llen(ALERT_QUEUE)
    return {"queue_name": ALERT_QUEUE, "length": length}

# To run this service (example using uvicorn):
# uvicorn business-ai-analytics.backend.notification-service.main:app --reload --port 8004
# Ensure PYTHONPATH is set, e.g.:
# PYTHONPATH=. uvicorn backend.notification-service.main:app --reload --port 8004 (from business-ai-analytics directory)
