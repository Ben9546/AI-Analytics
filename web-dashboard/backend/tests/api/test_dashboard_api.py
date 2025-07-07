import pytest
from fastapi.testclient import TestClient

# Reverted to relative imports for running pytest from web-dashboard/backend
from main import app
from services.auth_service import MOCK_USERS_DB, get_password_hash # To manage test user for auth

API_V1_PREFIX = "/api/v1"
DASHBOARD_PREFIX = f"{API_V1_PREFIX}/dashboard"

@pytest.fixture(scope="module")
def client_with_auth():
    # Ensure a test user exists for authenticated requests
    test_user_username = "dashboardtestuser"
    test_user_password = "dashboardtestpassword"
    if test_user_username not in MOCK_USERS_DB:
        MOCK_USERS_DB[test_user_username] = {
            "username": test_user_username,
            "email": "dashboard@example.com",
            "full_name": "Dashboard Test User",
            "hashed_password": get_password_hash(test_user_password),
            "disabled": False,
        }

    with TestClient(app) as c:
        # Log in to get a token
        login_response = c.post(
            f"{API_V1_PREFIX}/auth/token",
            data={"username": test_user_username, "password": test_user_password}
        )
        assert login_response.status_code == 200, "Failed to log in for dashboard tests"
        token = login_response.json()["access_token"]
        c.headers = {"Authorization": f"Bearer {token}"}
        yield c
    # Teardown: MOCK_USERS_DB.pop(test_user_username, None) if needed

# --- Test Main Dashboard Endpoints (Authenticated) ---

def test_get_executive_summary_data_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/main/executive-summary")
    assert response.status_code == 200
    data = response.json()
    assert "executive_summary_cards" in data
    assert isinstance(data["executive_summary_cards"], list)
    assert "quick_insights" in data
    assert "last_updated" in data

def test_get_realtime_metric_widgets_data_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/main/realtime-metric-widgets")
    assert response.status_code == 200
    data = response.json()
    assert "widgets" in data
    assert isinstance(data["widgets"], list)
    assert "timestamp" in data

def test_get_interactive_charts_data_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/main/interactive-charts?period=last_7_days")
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "last_7_days"
    assert "charts" in data
    assert isinstance(data["charts"], list)
    assert "generated_at" in data

def test_get_alert_notifications_panel_data_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/main/alert-notifications?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)
    assert len(data["alerts"]) <= 3

# --- Test Real-Time Tracking Module Endpoints (Authenticated) ---

def test_get_live_data_stream_config_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/realtime/live-data-stream-config")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "available_streams" in data

def test_crud_custom_metrics_authenticated(client_with_auth: TestClient):
    # POST (Create)
    metric_payload = {
        "name": "Test Custom Metric",
        "formula": "A / B * 100",
        "description": "A test metric for API."
    }
    response_post = client_with_auth.post(f"{DASHBOARD_PREFIX}/realtime/custom-metrics", json=metric_payload)
    assert response_post.status_code == 201 # Created
    created_metric = response_post.json()
    assert created_metric["name"] == metric_payload["name"]
    assert "id" in created_metric

    # GET (List)
    response_get = client_with_auth.get(f"{DASHBOARD_PREFIX}/realtime/custom-metrics")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert "custom_metrics" in data_get
    assert any(m["id"] == created_metric["id"] for m in data_get["custom_metrics"])

def test_get_realtime_trend_analysis_charts_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/realtime/trend-analysis-charts?metric_id=test_metric&period=last_30_minutes")
    assert response.status_code == 200
    data = response.json()
    assert data["metric_id"] == "test_metric"
    assert "labels" in data
    assert "datasets" in data

# --- Test Forecasting Interface Endpoints (Authenticated) ---

@pytest.fixture
def created_forecast_id(client_with_auth: TestClient) -> str:
    forecast_req = {"metric_to_forecast": "monthly_revenue", "periods": 3}
    response = client_with_auth.post(f"{DASHBOARD_PREFIX}/forecasting/generate", json=forecast_req)
    assert response.status_code == 202 or response.status_code == 200 # Mock might complete fast
    return response.json()["forecast_id"]

def test_generate_and_get_forecast_results_authenticated(client_with_auth: TestClient, created_forecast_id: str):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/forecasting/results/{created_forecast_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_forecast_id
    assert data["status"] == "completed" # Mock completes immediately
    assert "results" in data

def test_get_forecast_results_not_found_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/forecasting/results/non_existent_id")
    assert response.status_code == 404

def test_run_what_if_scenario_authenticated(client_with_auth: TestClient, created_forecast_id: str):
    scenario_payload = {"parameter_name": "marketing_spend", "change_percentage": 0.15}
    response = client_with_auth.post(
        f"{DASHBOARD_PREFIX}/forecasting/scenarios?forecast_id={created_forecast_id}",
        json=scenario_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["original_forecast_id"] == created_forecast_id
    assert "adjusted_predictions" in data["scenario_results"]

# --- Test Action Plan Center Endpoints (Authenticated) ---

def test_get_action_plan_recommendations_authenticated(client_with_auth: TestClient):
    response = client_with_auth.get(f"{DASHBOARD_PREFIX}/action-plans/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "action_plans" in data
    assert isinstance(data["action_plans"], list)

def test_update_action_plan_task_authenticated(client_with_auth: TestClient):
    # Assuming plan_id "plan_reduce_churn_q3" and rec_id "rec_churn_1" exist in mock data
    plan_id = "plan_reduce_churn_q3"
    rec_id = "rec_churn_1"
    update_payload = {"progress": 50, "status": "In Progress"}

    response = client_with_auth.put(
        f"{DASHBOARD_PREFIX}/action-plans/{plan_id}/recommendations/{rec_id}",
        json=update_payload
    )
    assert response.status_code == 200
    updated_task = response.json()
    assert updated_task["id"] == rec_id
    assert updated_task["progress"] == 50
    assert updated_task["status"] == "In Progress"

def test_update_action_plan_task_not_found_authenticated(client_with_auth: TestClient):
    update_payload = {"progress": 100}
    response = client_with_auth.put(
        f"{DASHBOARD_PREFIX}/action-plans/non_existent_plan/recommendations/non_existent_rec",
        json=update_payload
    )
    assert response.status_code == 404

# Note: Unauthenticated access to these dashboard routes should be blocked by AuthMiddleware.
# A separate test file or tests could specifically target middleware behavior,
# but the `client_with_auth` fixture implicitly tests that auth works for these.
# If a route was meant to be public, it would need a different test without auth.
# The health check in test_auth_api.py serves as an example of a public route test.
