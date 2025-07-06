from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import asyncio # For simulating scheduled tasks
from typing import Dict, Any, List
import json # For sending data to a "queue"

# Assuming connectors are relatively located
from .connectors.quickbooks_connector import QuickBooksConnector
from .connectors.salesforce_connector import SalesforceConnector
from .connectors.shopify_connector import ShopifyConnector
# We'll use a simple in-memory "Redis" for this example
# In a real app, you'd use the redis library: import redis

# Mock Redis client
class MockRedis:
    def __init__(self):
        self.queue = []
        print("MockRedis initialized.")

    def rpush(self, queue_name: str, data: str):
        print(f"MockRedis: Pushing to {queue_name}: {data[:100]}...") # Log snippet
        self.queue.append({queue_name: json.loads(data)}) # Store as dict for inspection if needed
        return len(self.queue)

    def lpop(self, queue_name: str):
        for item in self.queue:
            if queue_name in item:
                data = item.pop(queue_name)
                if not item: # if dict becomes empty
                    self.queue.remove({}) # clean up empty dicts, not ideal but works for mock
                print(f"MockRedis: Popping from {queue_name}: {str(data)[:100]}...")
                return json.dumps(data)
        return None

    defllen(self, queue_name: str):
        count = 0
        for item in self.queue:
            if queue_name in item:
                count += 1
        return count

mock_redis_client = MockRedis()
RAW_DATA_QUEUE = "raw_data_queue"
NORMALIZED_DATA_QUEUE = "normalized_data_queue" # For Analytics Engine

app = FastAPI(title="Data Ingestion Service")

# --- Configuration Store (Mock) ---
# In a real system, this would come from a database or a secure config service
CONFIGURED_SOURCES = {
    "quickbooks_main": {
        "type": "quickbooks",
        "credentials": {"client_id": "QB_ID_1", "client_secret": "QB_SECRET_1", "refresh_token": "QB_REFRESH_1", "realm_id": "QB_REALM_1"},
        "data_to_fetch": ["financial_summary"] # Example: what to fetch
    },
    "salesforce_primary": {
        "type": "salesforce",
        "credentials": {"username": "SF_USER_1", "password": "SF_PASSWORD_1", "security_token": "SF_TOKEN_1", "instance_url": "sf_instance_1"},
        "data_to_fetch": [{"object_name": "Account", "fields": ["Id", "Name", "AnnualRevenue"]}, {"object_name": "Opportunity"}]
    },
    "shopify_store_A": {
        "type": "shopify",
        "credentials": {"shop_url": "store-a.myshopify.com", "api_key": "SHOPIFY_KEY_A", "password": "SHOPIFY_PASSWORD_A"},
        "data_to_fetch": ["products", "orders"]
    }
}

# --- Data Normalization ---
def normalize_data(source_type: str, data_type: str, data: Any) -> Dict[str, Any]:
    """
    Transforms data from various sources into a standardized format.
    This is a crucial and complex step in a real system.
    """
    normalized_event = {
        "source_system": source_type,
        "data_category": data_type,
        "original_payload": data,
        "processed_at": asyncio.to_thread(lambda: __import__('datetime').datetime.utcnow().isoformat()), # Ensure datetime is accessible
        "normalized_fields": {} # Standardized fields go here
    }
    # Example normalization (very basic)
    if source_type == "shopify" and data_type == "products":
        # Assuming data is a list of product dicts
        normalized_event["normalized_fields"]["items"] = []
        for item in data: # data is expected to be a list
            normalized_item = {
                "id": f"shopify-{item.get('id')}",
                "name": item.get('title'),
                "type": "product"
            }
            normalized_event["normalized_fields"]["items"].append(normalized_item)
    elif source_type == "salesforce" and data_type == "Account":
        normalized_event["normalized_fields"]["items"] = []
        for item in data: # data is expected to be a list
            normalized_item = {
                "id": f"sf-{item.get('Id')}",
                "name": item.get('Name'),
                "revenue": item.get('AnnualRevenue'),
                "type": "account"
            }
            normalized_event["normalized_fields"]["items"].append(normalized_item)
    # Add more normalization rules for other sources and data types
    else:
        # Generic pass-through if no specific normalization
        normalized_event["normalized_fields"]["items"] = data if isinstance(data, list) else [data]


    print(f"Normalized {data_type} from {source_type}: {str(normalized_event)[:200]}...")
    return normalized_event

# --- Ingestion Logic ---
async def ingest_from_source(source_id: str, config: Dict[str, Any]):
    print(f"Starting ingestion for source: {source_id} of type {config['type']}")
    connector = None
    try:
        if config["type"] == "quickbooks":
            connector = QuickBooksConnector(**config["credentials"])
        elif config["type"] == "salesforce":
            connector = SalesforceConnector(**config["credentials"])
        elif config["type"] == "shopify":
            connector = ShopifyConnector(**config["credentials"])
        else:
            print(f"Unknown connector type: {config['type']}")
            return

        if connector:
            await asyncio.to_thread(connector.connect) # Run sync connect in thread
            for item_to_fetch in config.get("data_to_fetch", []):
                raw_data = None
                data_type_label = ""

                if isinstance(item_to_fetch, str): # e.g., for QuickBooks, Shopify
                    data_type_label = item_to_fetch
                    raw_data = await asyncio.to_thread(connector.get_all_data, item_to_fetch)
                elif isinstance(item_to_fetch, dict) and config["type"] == "salesforce": # e.g., for Salesforce
                    data_type_label = item_to_fetch["object_name"]
                    raw_data = await asyncio.to_thread(connector.get_all_data, item_to_fetch["object_name"], item_to_fetch.get("fields"))

                if raw_data:
                    print(f"Fetched {data_type_label} data from {source_id}: {str(raw_data)[:100]}...")
                    # Send raw data to a "raw_data_queue" (optional, for auditing/backup)
                    # mock_redis_client.rpush(RAW_DATA_QUEUE, json.dumps({"source": source_id, "type": data_type_label, "data": raw_data}))

                    # Normalize data
                    normalized_data = await asyncio.to_thread(normalize_data, config["type"], data_type_label, raw_data)

                    # Send normalized data to a queue for the Analytics Engine
                    mock_redis_client.rpush(NORMALIZED_DATA_QUEUE, json.dumps(normalized_data))
                else:
                    print(f"No data fetched for {item_to_fetch} from {source_id}")

    except Exception as e:
        print(f"Error during ingestion for {source_id}: {e}")
    finally:
        if connector:
            await asyncio.to_thread(connector.close)
    print(f"Finished ingestion for source: {source_id}")


async def periodic_ingestion_engine():
    """Simulates a periodic data pull every X minutes."""
    ingestion_interval_seconds = 5 * 60 # 5 minutes
    print(f"Periodic Ingestion Engine started. Will run every {ingestion_interval_seconds / 60} minutes.")
    while True:
        print(f"--- Running periodic ingestion cycle at {asyncio.to_thread(lambda: __import__('datetime').datetime.utcnow().isoformat())} ---")
        tasks = []
        for source_id, config in CONFIGURED_SOURCES.items():
            tasks.append(ingest_from_source(source_id, config))
        await asyncio.gather(*tasks)
        print(f"--- Finished periodic ingestion cycle. Waiting for {ingestion_interval_seconds / 60} minutes. ---")
        await asyncio.sleep(ingestion_interval_seconds)

# --- API Endpoints ---
class IngestionTriggerRequest(BaseModel):
    source_id: str

@app.post("/trigger-ingestion")
async def trigger_ingestion_endpoint(request: IngestionTriggerRequest, background_tasks: BackgroundTasks):
    """Manually triggers ingestion for a specific configured source."""
    source_id = request.source_id
    if source_id not in CONFIGURED_SOURCES:
        raise HTTPException(status_code=404, detail=f"Source ID '{source_id}' not found in configuration.")

    config = CONFIGURED_SOURCES[source_id]
    background_tasks.add_task(ingest_from_source, source_id, config)
    return {"message": f"Ingestion triggered for source: {source_id} in the background."}

@app.get("/configured-sources")
async def get_configured_sources():
    """Lists all configured data sources."""
    return {"sources": list(CONFIGURED_SOURCES.keys())}

@app.get("/queue-status/{queue_name}")
async def get_queue_status(queue_name: str):
    """Checks the status (length) of a mock Redis queue."""
    length = mock_redis_client.llen(queue_name)
    return {"queue_name": queue_name, "length": length}

@app.on_event("startup")
async def startup_event():
    # Start the periodic ingestion engine in the background
    # For a real deployment, this would be a separate worker process or managed by something like Celery Beat
    print("Starting background ingestion engine...")
    asyncio.create_task(periodic_ingestion_engine())

@app.get("/")
async def root():
    return {"message": "Data Ingestion Service is running. Use /docs for API details."}

# To run this service (example using uvicorn):
# uvicorn business-ai-analytics.backend.data-ingestion.main:app --reload --port 8001
# Remember to adjust PYTHONPATH or run from the correct directory.
# Example: PYTHONPATH=. uvicorn backend.data-ingestion.main:app --reload --port 8001 (from business-ai-analytics directory)
