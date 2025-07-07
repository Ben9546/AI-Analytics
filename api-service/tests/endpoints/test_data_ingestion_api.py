import pytest
from fastapi.testclient import TestClient

# Reverted to absolute imports from project root perspective
from api_service.main import app, MOCK_API_KEYS
from api_service.endpoints.data_ingestion import mock_data_sources_db # To check state

API_PREFIX = "/api/v1/data" # As defined in main.py for this router

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers_read_write():
    # Find a key with read and write permissions from MOCK_API_KEYS
    api_key = None
    for key, details in MOCK_API_KEYS.items():
        if "read" in details["permissions"] and "write" in details["permissions"]:
            api_key = key
            break
    if not api_key:
        raise ValueError("No suitable read-write API key found in MOCK_API_KEYS for testing")
    return {"X-API-KEY": api_key}

@pytest.fixture
def auth_headers_read_only():
    api_key = None
    for key, details in MOCK_API_KEYS.items():
        if "read" in details["permissions"] and "write" not in details["permissions"]: # Find a strictly read-only key
            api_key = key
            break
    if not api_key: # If no strictly read-only, use one that has at least read
         for key, details in MOCK_API_KEYS.items():
            if "read" in details["permissions"]:
                api_key = key
                break
    if not api_key:
        raise ValueError("No suitable read-only API key found in MOCK_API_KEYS for testing")
    return {"X-API-KEY": api_key}

@pytest.fixture(autouse=True)
def clear_mock_db():
    mock_data_sources_db.clear()

# --- Test Data Ingestion Endpoints ---

def test_ingest_data_success(client: TestClient, auth_headers_read_write):
    payload = {"source_name": "Test QB Data", "data_points": 1000}
    response = client.post(f"{API_PREFIX}/ingest", json=payload, headers=auth_headers_read_write)
    assert response.status_code == 200
    assert response.json()["message"] == "Data ingestion request received (mock)."
    assert response.json()["payload_summary"] == "Test QB Data"

def test_ingest_data_unauthenticated(client: TestClient):
    payload = {"source_name": "Test QB Data", "data_points": 1000}
    response = client.post(f"{API_PREFIX}/ingest", json=payload) # No auth header
    assert response.status_code == 401 # Expecting 401 due to missing X-API-KEY
    assert "Not authenticated" in response.json()["detail"]

def test_ingest_data_invalid_key(client: TestClient):
    payload = {"source_name": "Test QB Data", "data_points": 1000}
    response = client.post(f"{API_PREFIX}/ingest", json=payload, headers={"X-API-KEY": "invalidkey"})
    assert response.status_code == 403 # Expecting 403 for invalid API Key
    assert "Invalid API Key" in response.json()["detail"]

# --- Test Data Sources CRUD ---

def test_add_data_source(client: TestClient, auth_headers_read_write):
    source_payload = {
        "name": "My QuickBooks Connection",
        "type": "quickbooks",
        "config": {"client_id": "123", "client_secret": "abc"}
    }
    response = client.post(f"{API_PREFIX}/sources", json=source_payload, headers=auth_headers_read_write)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == source_payload["name"]
    assert data["type"] == source_payload["type"]
    assert "id" in data
    assert len(mock_data_sources_db) == 1
    assert mock_data_sources_db[0].id == data["id"]

def test_list_data_sources_empty(client: TestClient, auth_headers_read_write):
    response = client.get(f"{API_PREFIX}/sources", headers=auth_headers_read_write)
    assert response.status_code == 200
    assert response.json() == []

def test_list_data_sources_with_data(client: TestClient, auth_headers_read_write):
    # Add a source first
    source_payload = {"name": "QB1", "type": "quickbooks", "config": {}}
    client.post(f"{API_PREFIX}/sources", json=source_payload, headers=auth_headers_read_write)

    response = client.get(f"{API_PREFIX}/sources", headers=auth_headers_read_write)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "QB1"

def test_update_data_source(client: TestClient, auth_headers_read_write):
    # Add a source
    add_payload = {"name": "Initial Name", "type": "salesforce", "config": {"user": "test"}}
    add_response = client.post(f"{API_PREFIX}/sources", json=add_payload, headers=auth_headers_read_write)
    source_id = add_response.json()["id"]

    # Update it
    update_payload = {
        "id": source_id, # ID must match for update usually, or be part of path
        "name": "Updated Salesforce Name",
        "type": "salesforce", # Type usually not updatable, but for mock it's fine
        "config": {"user": "test_updated", "token": "new_token"}
    }
    response = client.put(f"{API_PREFIX}/sources/{source_id}", json=update_payload, headers=auth_headers_read_write)
    assert response.status_code == 200
    updated_data = response.json()
    assert updated_data["name"] == "Updated Salesforce Name"
    assert updated_data["config"]["user"] == "test_updated"
    assert updated_data["config"]["token"] == "new_token"

def test_update_data_source_not_found(client: TestClient, auth_headers_read_write):
    update_payload = {"name": "NonExistent", "type": "type", "config": {}}
    response = client.put(f"{API_PREFIX}/sources/nonexistentid", json=update_payload, headers=auth_headers_read_write)
    assert response.status_code == 404

# --- Test Rate Limiting (Conceptual - requires multiple requests) ---
# These tests are harder to make perfectly reliable without fine-grained time control
# or direct access to the rate limiter's state. The current middleware is also simplified.
# For now, a conceptual test structure.

# def test_rate_limiting_on_ingest(client: TestClient, auth_headers_read_write):
#     # This test would need to be adjusted based on the exact rate limit counts in main.py
#     # And potentially use freezegun or similar if time-based limits are very short.
#     # For now, this is a placeholder as the current middleware is basic.
#     payload = {"source_name": "Rate Limit Test", "data_points": 1}
#     # Assuming RATE_LIMIT_MAX_REQUESTS_API is, for example, 2 for this test scenario
#     # And window is short enough for test.
#     # This test would need the rate limiter in api_service/main.py to be more aggressive
#     # for testing (e.g. 2 requests per 10 seconds).
#     # For now, we cannot reliably test it without modifying main.py's limits.
#     # If main.py had limits like 2 requests / 60s:
#     # client.post(f"{API_PREFIX}/ingest", json=payload, headers=auth_headers_read_write) # 1
#     # client.post(f"{API_PREFIX}/ingest", json=payload, headers=auth_headers_read_write) # 2
#     # response = client.post(f"{API_PREFIX}/ingest", json=payload, headers=auth_headers_read_write) # 3 - should be rate limited
#     # assert response.status_code == 429
#     pass # Placeholder - full rate limit testing is complex for this setup.

# Test read-only access for GET endpoints
def test_list_data_sources_read_only_key(client: TestClient, auth_headers_read_only):
    response = client.get(f"{API_PREFIX}/sources", headers=auth_headers_read_only)
    assert response.status_code == 200 # Read operation should be allowed

# Test write access denial for read-only key
def test_add_data_source_read_only_key_denied(client: TestClient, auth_headers_read_only):
    # This test depends on how verify_api_key and endpoint dependencies are set up.
    # If verify_api_key returns permissions and endpoints check them.
    # The current verify_api_key in main.py doesn't enforce permissions beyond key validity.
    # This test is therefore conceptual unless main.py's auth is enhanced.

    # To make this test meaningful, verify_api_key or a further dependency
    # would need to check `key_details["permissions"]`.
    # For now, it will pass if the key is valid, as no permission check is done post-validation.
    # If we add permission checks:
    # source_payload = {"name": "Attempt Write", "type": "type", "config": {}}
    # response = client.post(f"{API_PREFIX}/sources", json=source_payload, headers=auth_headers_read_only)
    # assert response.status_code == 403 # Forbidden due to insufficient permissions
    pass # Placeholder for when permission checks are granularly implemented.
