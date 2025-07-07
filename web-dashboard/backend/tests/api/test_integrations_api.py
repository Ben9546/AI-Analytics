import pytest
from fastapi.testclient import TestClient

# Reverted to relative imports for running pytest from web-dashboard/backend
from main import app
from services.auth_service import MOCK_USERS_DB, get_password_hash
from api.integrations_api import configured_integrations_db # To check state

API_V1_PREFIX = "/api/v1"
INTEGRATIONS_PREFIX = f"{API_V1_PREFIX}/integrations"

@pytest.fixture(scope="module")
def client(): # Basic client without auth for unauthenticated tests
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def client_with_auth_integrations():
    test_user_username = "integrationstestuser"
    test_user_password = "integrationstestpassword"
    if test_user_username not in MOCK_USERS_DB:
        MOCK_USERS_DB[test_user_username] = {
            "username": test_user_username,
            "email": "integrations@example.com",
            "full_name": "Integrations Test User",
            "hashed_password": get_password_hash(test_user_password),
            "disabled": False,
        }

    with TestClient(app) as c:
        login_response = c.post(
            f"{API_V1_PREFIX}/auth/token",
            data={"username": test_user_username, "password": test_user_password}
        )
        assert login_response.status_code == 200, "Failed to log in for integrations tests"
        token = login_response.json()["access_token"]
        c.headers = {"Authorization": f"Bearer {token}"}

        # Clean up any integrations from previous test runs if necessary
        # configured_integrations_db.clear() # This might be too aggressive if tests run in parallel or depend on prior state.
                                          # For sequential tests in a module, it's okay.
        yield c
        # Optional: configured_integrations_db.clear() # Clean up after tests in this module

@pytest.fixture(autouse=True)
def clear_integrations_db_after_each_test():
    """Clears the mock integrations DB after each test in this module."""
    # This runs before each test (due to yield) and after each test (code after yield)
    # However, for a simple clear, just doing it after is fine.
    # For more complex setup/teardown per test, this fixture would be more involved.
    # Using yield means the code before yield is setup, after is teardown.
    # If no setup needed, just the teardown part:
    yield
    configured_integrations_db.clear()


def test_list_integration_types(client_with_auth_integrations: TestClient):
    response = client_with_auth_integrations.get(f"{INTEGRATIONS_PREFIX}/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0 # Assuming we have some defined types
    assert any(item["type_key"] == "quickbooks" for item in data)
    assert any(item["type_key"] == "salesforce" for item in data)
    assert any(item["type_key"] == "shopify" for item in data)

def test_add_and_list_integration_quickbooks_success(client_with_auth_integrations: TestClient):
    payload = {
        "name": "My QB Integration",
        "type": "quickbooks",
        "credentials": {
            "client_id": "qb_client_123",
            "client_secret": "qb_secret_xyz",
            "realm_id": "qb_realm_abc",
            "refresh_token": "qb_refresh_token_123"
        }
    }
    response_add = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    assert response_add.status_code == 201
    added_integration = response_add.json()
    assert added_integration["name"] == "My QB Integration"
    assert added_integration["type"] == "quickbooks"
    assert added_integration["connected"] is True # Mock connector connects on init
    integration_id = added_integration["id"]

    response_list = client_with_auth_integrations.get(INTEGRATIONS_PREFIX)
    assert response_list.status_code == 200
    integrations = response_list.json()
    assert len(integrations) == 1
    assert integrations[0]["id"] == integration_id
    assert integrations[0]["name"] == "My QB Integration"

def test_add_integration_unsupported_type(client_with_auth_integrations: TestClient):
    payload = {
        "name": "Unsupported Int",
        "type": "mythical_crm",
        "credentials": {"api_key": "123"}
    }
    response = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    assert response.status_code == 400
    assert "Unsupported integration type" in response.json()["detail"]

def test_add_integration_missing_credentials(client_with_auth_integrations: TestClient):
    payload = {
        "name": "QB Missing Creds",
        "type": "quickbooks",
        "credentials": {"client_id": "123"} # Missing other required fields
    }
    response = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    assert response.status_code == 400
    assert "Missing required credential field" in response.json()["detail"]

def test_get_integration_status(client_with_auth_integrations: TestClient):
    # Add an integration first
    payload = {"name": "Test Shopify", "type": "shopify", "credentials": {"shop_url": "test.myshopify.com", "api_key": "key", "password": "pass"}}
    add_response = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    integration_id = add_response.json()["id"]

    status_response = client_with_auth_integrations.get(f"{INTEGRATIONS_PREFIX}/{integration_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["id"] == integration_id
    assert status_data["name"] == "Test Shopify"
    assert status_data["connected"] is True

def test_get_integration_status_not_found(client_with_auth_integrations: TestClient):
    response = client_with_auth_integrations.get(f"{INTEGRATIONS_PREFIX}/nonexistentid/status")
    assert response.status_code == 404

def test_connect_disconnect_integration(client_with_auth_integrations: TestClient):
    payload = {"name": "Connect-Disconnect Test", "type": "salesforce", "credentials": {"username":"u", "password":"p", "security_token":"t", "instance_url":"url"}}
    add_response = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    integration_id = add_response.json()["id"]

    # Disconnect
    disconnect_response = client_with_auth_integrations.post(f"{INTEGRATIONS_PREFIX}/{integration_id}/disconnect")
    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["connected"] is False

    # Connect
    connect_response = client_with_auth_integrations.post(f"{INTEGRATIONS_PREFIX}/{integration_id}/connect")
    assert connect_response.status_code == 200
    assert connect_response.json()["connected"] is True

def test_delete_integration(client_with_auth_integrations: TestClient):
    payload = {"name": "To Be Deleted", "type": "shopify", "credentials": {"shop_url": "delete.myshopify.com", "api_key": "key", "password": "pass"}}
    add_response = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    integration_id = add_response.json()["id"]
    assert integration_id in configured_integrations_db # Check it's in our mock DB

    delete_response = client_with_auth_integrations.delete(f"{INTEGRATIONS_PREFIX}/{integration_id}")
    assert delete_response.status_code == 204
    assert integration_id not in configured_integrations_db # Check it's removed

    # Verify it's gone
    status_response = client_with_auth_integrations.get(f"{INTEGRATIONS_PREFIX}/{integration_id}/status")
    assert status_response.status_code == 404

def test_delete_integration_not_found(client_with_auth_integrations: TestClient):
    response = client_with_auth_integrations.delete(f"{INTEGRATIONS_PREFIX}/nonexistentid")
    assert response.status_code == 404


def test_fetch_data_from_integration(client_with_auth_integrations: TestClient):
    payload = {"name": "FetchData QB", "type": "quickbooks", "credentials": {"client_id":"id","client_secret":"s","realm_id":"r","refresh_token":"rt"}}
    add_response = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    integration_id = add_response.json()["id"]

    fetch_payload = {"data_type": "financial_summary"}
    fetch_response = client_with_auth_integrations.post(f"{INTEGRATIONS_PREFIX}/{integration_id}/fetch-data", json=fetch_payload)
    assert fetch_response.status_code == 200
    data = fetch_response.json()
    assert data["source"] == "QuickBooks"
    assert data["report_type"] == "FinancialSummary"
    assert "total_revenue" in data["data"]

    fetch_invoices_payload = {"data_type": "invoices", "params": {"status": "pending"}}
    fetch_invoices_response = client_with_auth_integrations.post(f"{INTEGRATIONS_PREFIX}/{integration_id}/fetch-data", json=fetch_invoices_payload)
    assert fetch_invoices_response.status_code == 200
    invoices_data = fetch_invoices_response.json()
    assert invoices_data["source"] == "QuickBooks"
    assert invoices_data["data_type"] == "Invoices"
    assert invoices_data["filter_status"] == "pending"

def test_fetch_data_integration_not_connected(client_with_auth_integrations: TestClient):
    payload = {"name": "FetchData Not Connected", "type": "shopify", "credentials": {"shop_url":"s","api_key":"k","password":"p"}}
    add_response = client_with_auth_integrations.post(INTEGRATIONS_PREFIX, json=payload)
    integration_id = add_response.json()["id"]

    # Disconnect it first
    client_with_auth_integrations.post(f"{INTEGRATIONS_PREFIX}/{integration_id}/disconnect")

    fetch_payload = {"data_type": "products"}
    fetch_response = client_with_auth_integrations.post(f"{INTEGRATIONS_PREFIX}/{integration_id}/fetch-data", json=fetch_payload)
    assert fetch_response.status_code == 400 # Bad Request
    assert "is not connected" in fetch_response.json()["detail"]

# Add a test for the root /integrations endpoint to ensure it's protected if no auth
def test_list_integrations_unauthenticated(client: TestClient): # Using non-authed client
    response = client.get(INTEGRATIONS_PREFIX)
    assert response.status_code == 401 # Should be protected by AuthMiddleware
    # The specific error message might come from AuthMiddleware
    assert "Not authenticated" in response.json().get("detail", "") or "Not authenticated" in response.text
