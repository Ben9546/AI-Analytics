from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid

# Import connector classes - adjusted to be absolute from 'backend' perspective
from services.connectors.quickbooks_connector import QuickBooksConnector
from services.connectors.salesforce_connector import SalesforceConnector
from services.connectors.shopify_connector import ShopifyConnector
from services.connectors import BaseConnector # For type hinting

router = APIRouter()

# --- Mock In-Memory Store for Configured Integrations ---
# In a real app, this would be stored in a database (e.g., PostgreSQL)
# and linked to a user or organization.
configured_integrations_db: Dict[str, BaseConnector] = {} # Store instances of connectors

# --- Available Connector Types (Conceptual) ---
AVAILABLE_CONNECTOR_TYPES = {
    "quickbooks": {"name": "QuickBooks Online", "handler": QuickBooksConnector, "required_config_fields": ["client_id", "client_secret", "realm_id", "refresh_token"]},
    "salesforce": {"name": "Salesforce CRM", "handler": SalesforceConnector, "required_config_fields": ["username", "password", "security_token", "instance_url"]},
    "shopify": {"name": "Shopify E-commerce", "handler": ShopifyConnector, "required_config_fields": ["shop_url", "api_key", "password"]},
    # Add more types here: Xero, Stripe, PayPal, Plaid, HubSpot, etc.
}

# --- Pydantic Models for API ---
class IntegrationConfigBase(BaseModel):
    name: str # User-defined name for this specific integration instance
    type: str # e.g., "quickbooks", "salesforce"
    credentials: Dict[str, Any] # Store encrypted in real app

class IntegrationConfigCreate(IntegrationConfigBase):
    pass

class IntegrationStatus(BaseModel):
    id: str
    name: str
    type: str
    connected: bool
    last_synced: Optional[str] = "N/A"
    details: Optional[Dict[str, Any]] = None


# --- API Endpoints ---

@router.get("/types", summary="List available integration connector types")
async def list_integration_types():
    return [{"type_key": key, "name": value["name"], "required_config": value["required_config_fields"]} for key, value in AVAILABLE_CONNECTOR_TYPES.items()]

@router.post("", response_model=IntegrationStatus, status_code=status.HTTP_201_CREATED, summary="Add and configure a new data source integration")
async def add_integration(config: IntegrationConfigCreate):
    connector_info = AVAILABLE_CONNECTOR_TYPES.get(config.type.lower())
    if not connector_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported integration type: {config.type}")

    # Validate required credential fields (basic check)
    for field in connector_info["required_config_fields"]:
        if field not in config.credentials:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required credential field '{field}' for {config.type}")

    integration_id = str(uuid.uuid4())

    # In a real app, credentials should be encrypted before storing/using.
    # For mock, we pass them directly.
    connector_config = {
        "id": integration_id,
        "name": config.name,
        "type": config.type,
        **config.credentials # Spread credentials into the config for the connector instance
    }

    try:
        connector_instance = connector_info["handler"](config=connector_config)
        # Attempt to connect conceptually
        await connector_instance.connect()
        configured_integrations_db[integration_id] = connector_instance
        status_info = await connector_instance.get_status()
        return IntegrationStatus(id=integration_id, **status_info)
    except Exception as e:
        # Catch potential errors during connector instantiation or initial connection
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initialize or connect integration: {str(e)}")


@router.get("", response_model=List[IntegrationStatus], summary="List all configured integrations")
async def list_configured_integrations():
    statuses = []
    for integration_id, connector_instance in configured_integrations_db.items():
        status_info = await connector_instance.get_status()
        statuses.append(IntegrationStatus(id=integration_id, **status_info))
    return statuses

@router.get("/{integration_id}/status", response_model=IntegrationStatus, summary="Get the status of a specific integration")
async def get_integration_status(integration_id: str):
    connector = configured_integrations_db.get(integration_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    status_info = await connector.get_status()
    return IntegrationStatus(id=integration_id, **status_info)

@router.post("/{integration_id}/connect", response_model=IntegrationStatus, summary="Attempt to connect a configured integration")
async def connect_integration(integration_id: str):
    connector = configured_integrations_db.get(integration_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    await connector.connect()
    status_info = await connector.get_status()
    return IntegrationStatus(id=integration_id, **status_info)

@router.post("/{integration_id}/disconnect", response_model=IntegrationStatus, summary="Disconnect an integration")
async def disconnect_integration(integration_id: str):
    connector = configured_integrations_db.get(integration_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    await connector.disconnect()
    status_info = await connector.get_status()
    return IntegrationStatus(id=integration_id, **status_info)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a configured integration")
async def delete_integration(integration_id: str):
    if integration_id in configured_integrations_db:
        connector = configured_integrations_db.pop(integration_id)
        await connector.disconnect() # Ensure it's disconnected
        print(f"Integration deleted: {integration_id}")
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

class FetchDataRequest(BaseModel):
    data_type: str
    params: Optional[Dict[str, Any]] = None

@router.post("/{integration_id}/fetch-data", summary="Fetch data from a specific integration (mock)")
async def fetch_data_from_integration(integration_id: str, request_body: FetchDataRequest):
    connector = configured_integrations_db.get(integration_id)
    if not connector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    if not connector.connected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Integration '{connector.config.get('name')}' is not connected.")

    data = await connector.fetch_data(data_type=request_body.data_type, params=request_body.params)
    return data

# Note: The current_user dependency from auth middleware is not explicitly added to these routes yet.
# For a production app, these endpoints (especially POST, DELETE) should be protected.
# The AuthMiddleware added in main.py will protect all routes not in PUBLIC_PATHS.
# These integration routes are not in PUBLIC_PATHS by default, so they will be protected.
# The user information would be available via `request.state.current_user` if needed for multi-tenancy.
