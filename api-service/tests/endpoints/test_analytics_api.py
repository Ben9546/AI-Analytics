import pytest
from fastapi.testclient import TestClient
from typing import List, Dict, Any

# Reverted to absolute imports from project root perspective
from api_service.main import app, MOCK_API_KEYS
from api_service.endpoints.analytics import mock_custom_analytics_metrics_db

API_PREFIX = "/api/v1/analytics"

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(): # Using a generic read-write key for these tests
    api_key = "testapikey123" # Assumes this key exists in MOCK_API_KEYS and has needed permissions
    if api_key not in MOCK_API_KEYS:
        # Add it if it's not there, for test robustness, though it should be in main.py
        MOCK_API_KEYS[api_key] = {"client_id": "test_client_analytics", "permissions": ["read", "write"]}
    return {"X-API-KEY": api_key}

@pytest.fixture(autouse=True)
def clear_mock_analytics_db():
    mock_custom_analytics_metrics_db.clear()

# --- Test Analytics Endpoints ---

def test_get_realtime_analytics_no_specific_metrics(client: TestClient, auth_headers):
    response = client.get(f"{API_PREFIX}/realtime", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "realtime_data" in data
    assert "timestamp" in data
    # Check for default metrics if no specific ones are requested
    assert "active_users" in data["realtime_data"]
    assert "conversion_rate" in data["realtime_data"]

def test_get_realtime_analytics_with_specific_metrics(client: TestClient, auth_headers):
    response = client.get(f"{API_PREFIX}/realtime?metrics=sales_volume&metrics=user_engagement", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "realtime_data" in data
    assert "sales_volume" in data["realtime_data"]
    assert "user_engagement" in data["realtime_data"]

def test_get_realtime_analytics_unauthenticated(client: TestClient):
    response = client.get(f"{API_PREFIX}/realtime")
    assert response.status_code == 401

def test_list_analytics_metrics_empty(client: TestClient, auth_headers):
    response = client.get(f"{API_PREFIX}/metrics", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == [] # Relies on clear_mock_analytics_db

def test_create_and_list_custom_analytics_metric(client: TestClient, auth_headers):
    metric_payload = {
        "name": "User Signups per Week",
        "query_definition": "SELECT COUNT(user_id) FROM users WHERE signup_date >= NOW() - INTERVAL '7 days'"
    }
    response_create = client.post(f"{API_PREFIX}/custom-metrics", json=metric_payload, headers=auth_headers)
    assert response_create.status_code == 201
    created_metric = response_create.json()
    assert created_metric["name"] == metric_payload["name"]
    assert "id" in created_metric

    response_list = client.get(f"{API_PREFIX}/metrics", headers=auth_headers)
    assert response_list.status_code == 200
    metrics_list = response_list.json()
    assert len(metrics_list) == 1
    assert metrics_list[0]["id"] == created_metric["id"]
    assert metrics_list[0]["name"] == created_metric["name"]

def test_create_custom_analytics_metric_invalid_payload(client: TestClient, auth_headers):
    invalid_payload = {"name": "Missing Query"} # Missing query_definition
    response = client.post(f"{API_PREFIX}/custom-metrics", json=invalid_payload, headers=auth_headers)
    assert response.status_code == 422 # Unprocessable Entity due to Pydantic validation
