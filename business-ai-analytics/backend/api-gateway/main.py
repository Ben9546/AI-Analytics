from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx # For making async requests to other services
from typing import List, Dict, Any, Optional
import asyncio
import datetime # Added for mobile notifications timestamp
import time # For rate limiting

app = FastAPI(title="API Gateway / Dashboard API")

# --- Configuration for internal service URLs ---
ANALYTICS_ENGINE_URL = "http://localhost:8002"
ML_MODELS_URL = "http://localhost:8003"
USER_MANAGEMENT_URL = "http://localhost:8005" # Hypothetical
NOTIFICATION_SERVICE_URL = "http://localhost:8004" # For mobile notifications (conceptual)


# --- Rate Limiting (Simple In-Memory Implementation) ---
# In production, use a distributed solution like Redis with a library like fastapi-limiter.
RATE_LIMIT_MAX_REQUESTS = 100  # Max requests
RATE_LIMIT_WINDOW_SECONDS = 60  # Per minute
request_counts: Dict[str, List[float]] = {} # Stores client_ip: [timestamp1, timestamp2, ...]

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown" # Get client IP

    current_time = time.time()

    # Get timestamps for this IP, remove old ones
    if client_ip not in request_counts:
        request_counts[client_ip] = []

    request_timestamps = request_counts[client_ip]
    # Filter out timestamps older than the window
    request_timestamps = [ts for ts in request_timestamps if ts > current_time - RATE_LIMIT_WINDOW_SECONDS]

    if len(request_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        # Calculate time to wait until the oldest request in the window expires
        time_to_wait = (request_timestamps[0] + RATE_LIMIT_WINDOW_SECONDS) - current_time
        return JSONResponse(
            status_code=429, # Too Many Requests
            content={"detail": f"Rate limit exceeded. Try again in {max(0, round(time_to_wait))} seconds."},
            headers={"Retry-After": str(int(max(0, time_to_wait)))} # Standard header for rate limiting
        )

    request_timestamps.append(current_time)
    request_counts[client_ip] = request_timestamps # Update the list

    response = await call_next(request)
    return response

# --- Helper function for internal API calls ---
async def call_service(client: httpx.AsyncClient, method: str, url: str, json_data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    try:
        if method.upper() == "GET":
            response = await client.get(url, params=params, timeout=10.0)
        elif method.upper() == "POST":
            response = await client.post(url, json=json_data, params=params, timeout=10.0)
        elif method.upper() == "PATCH":
            response = await client.patch(url, json=json_data, params=params, timeout=10.0)
        else:
            raise HTTPException(status_code=500, detail=f"Unsupported method {method}")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as exc:
        error_message = f"RequestError calling {exc.request.url!r}: {type(exc).__name__} - {str(exc)}"
        print(f"API Gateway: {error_message}")
        # Extract service name more robustly
        service_name_parts = url.split('/')
        service_name = service_name_parts[2].split(':')[0] if len(service_name_parts) > 2 else "unknown service"
        raise HTTPException(status_code=503, detail=f"Service unavailable: {service_name}. {error_message}")
    except httpx.HTTPStatusError as exc:
        error_message = f"HTTPStatusError calling {exc.request.url!r}: {exc.response.status_code} - {exc.response.text[:200]}"
        print(f"API Gateway: {error_message}")
        downstream_detail = exc.response.json().get("detail") if exc.response.content else str(exc.response.status_code)
        service_name_parts = url.split('/')
        service_name = service_name_parts[2].split(':')[0] if len(service_name_parts) > 2 else "unknown service"
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error from {service_name}: {downstream_detail}")


# --- User Management Passthrough (existing, mock) ---
class UserLogin(BaseModel): username: str; password: str
class UserRegister(BaseModel): username: str; email: str; password: str

@app.post("/auth/login", summary="User login")
async def login(user_credentials: UserLogin):
    print(f"Mock login attempt for user: {user_credentials.username}")
    if user_credentials.username == "testuser" and user_credentials.password == "testpass":
        return {"token": "mock_jwt_token_for_testuser", "message": "Login successful (mock)"}
    raise HTTPException(status_code=401, detail="Invalid mock credentials")

@app.post("/auth/register", summary="User registration")
async def register(user_details: UserRegister):
    print(f"Mock registration for user: {user_details.username}")
    return {"message": f"User {user_details.username} registered successfully (mock). Please login."}

# --- Dashboard Endpoints (existing, condensed for brevity in diff) ---
@app.get("/dashboard/executive-summary", summary="Data for Executive Summary Dashboard")
async def get_executive_summary():
    async with httpx.AsyncClient() as client:
        try:
            kpis_task = call_service(client, "GET", f"{ANALYTICS_ENGINE_URL}/kpis")
            forecast_task = call_service(client, "POST", f"{ML_MODELS_URL}/forecast/revenue", json_data={"future_periods": 3})
            insights_task = call_service(client, "GET", f"{ANALYTICS_ENGINE_URL}/insights")
            kpis_data, forecast_data, insights_data = await asyncio.gather(kpis_task, forecast_task, insights_task, return_exceptions=True)
            if isinstance(kpis_data, Exception): raise HTTPException(status_code=503, detail=f"KPIs error: {kpis_data}")
            if isinstance(forecast_data, Exception): raise HTTPException(status_code=503, detail=f"Forecast error: {forecast_data}")
            if isinstance(insights_data, Exception): raise HTTPException(status_code=503, detail=f"Insights error: {insights_data}")
            open_critical_insights_count = sum(1 for i in insights_data.get("actionable_insights", []) if i.get("status") == "New")
            return {"current_kpis": kpis_data, "revenue_forecast_next_3_periods": forecast_data.get("forecast", []),
                    "open_critical_insights_count": open_critical_insights_count, "last_updated": datetime.datetime.utcnow().isoformat()}
        except HTTPException as e: raise e
        except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/sales", summary="Data for Sales Dashboard (Placeholder)")
async def get_sales_dashboard_data(): return {"message": "Sales Dashboard Data Placeholder - TBD"}
@app.get("/dashboard/marketing", summary="Data for Marketing Dashboard (Placeholder)")
async def get_marketing_dashboard_data(): return {"message": "Marketing Dashboard Data Placeholder - TBD"}

@app.get("/dashboard/alert-center", summary="Data for Alert Center")
async def get_alert_center_data():
    async with httpx.AsyncClient() as client:
        anomalies_data = await call_service(client, "GET", f"{ANALYTICS_ENGINE_URL}/anomalies")
        alerts = sorted(anomalies_data.get("anomalies", []), key=lambda x: x.get("timestamp", ""), reverse=True)
        return {"alerts": alerts[:20]}

@app.get("/dashboard/action-center", summary="Data for Action Center - Personalized To-Do List")
async def get_action_center_data(user_id: Optional[str] = None):
    async with httpx.AsyncClient() as client:
        insights_data = await call_service(client, "GET", f"{ANALYTICS_ENGINE_URL}/insights")
        actionable_items = []
        if insights_data and "actionable_insights" in insights_data:
            for insight in insights_data["actionable_insights"]:
                if insight.get("status", "").lower() in ["new", "investigating"]:
                    for action in insight.get("recommended_actions", []):
                        if action.get("status","").lower() == "pending":
                            actionable_items.append({
                                "insight_id": insight.get("id"), "insight_summary": insight.get("summary"),
                                "action_id": action.get("action_id"), "action_description": action.get("action"),
                                "priority_score": action.get("priority_score"),
                                "suggested_deadline_days": action.get("suggested_deadline_days"),
                                "category": action.get("category")})
        sorted_actions = sorted(actionable_items, key=lambda x: x.get("priority_score", 0), reverse=True)
        return {"user_id": user_id or "all_users", "pending_actions": sorted_actions[:20]}

@app.post("/dashboard/generate-report", summary="Generate a report (Conceptual)")
async def generate_report(report_request: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        kpis = await call_service(client, "GET", f"{ANALYTICS_ENGINE_URL}/kpis")
        return {"report_title": f"Conceptual Report: {report_request.get('type', 'General Summary')}",
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "data_summary": {"key_kpis": kpis, "notes": "Mock report.", "requested_parameters": report_request}}

# --- Mobile Application Support Endpoints ---

@app.get("/mobile/notifications", summary="Fetch notifications for mobile app")
async def get_mobile_notifications(user_id: Optional[str] = None, count: int = 10):
    """
    Fetches recent critical alerts/notifications.
    Conceptually, this might call the Notification Service or filter Analytics Engine anomalies.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Option 1: Call Notification Service (if it had a /notifications endpoint)
            # notifications = await call_service(client, "GET", f"{NOTIFICATION_SERVICE_URL}/notifications", params={"user_id": user_id, "count": count})
            # return notifications

            # Option 2: For now, use Analytics Engine anomalies as a proxy for critical alerts
            anomalies_data = await call_service(client, "GET", f"{ANALYTICS_ENGINE_URL}/anomalies")
            # Transform anomalies into a simpler notification format
            mobile_notifications = []
            # Ensure insights_data is fetched to link anomalies to insights
            insights_data = {}
            try:
                insights_data = await call_service(client, "GET", f"{ANALYTICS_ENGINE_URL}/insights")
            except HTTPException as e:
                print(f"Could not fetch insights for mobile notifications, proceeding without link: {e.detail}")


            for anomaly in anomalies_data.get("anomalies", []):
                related_insight_id = None
                if insights_data.get("actionable_insights"):
                    for insight in insights_data["actionable_insights"]:
                        # Compare the core anomaly details. This matching might need to be more robust.
                        if insight.get("trigger_event_details") and \
                           insight["trigger_event_details"].get("type") == anomaly.get("type") and \
                           insight["trigger_event_details"].get("order_id") == anomaly.get("order_id") and \
                           insight["trigger_event_details"].get("amount") == anomaly.get("amount"):
                           related_insight_id = insight.get("id")
                           break

                mobile_notifications.append({
                    "id": f"anomaly_{anomaly.get('order_id', anomaly.get('type', 'generic'))}_{hash(str(anomaly.get('timestamp')))}",
                    "type": anomaly.get("type", "GenericAlert"),
                    "title": f"Alert: {anomaly.get('type', 'Issue Detected')}",
                    "message": anomaly.get("message", "Please review system status."),
                    "timestamp": anomaly.get("timestamp", datetime.datetime.utcnow().isoformat()),
                    "urgency": "high" if "High" in anomaly.get("type", "") else "medium",
                    "related_insight_id": related_insight_id
                })

            sorted_notifications = sorted(mobile_notifications, key=lambda x: x["timestamp"], reverse=True)
            return {"user_id": user_id or "all_users", "notifications": sorted_notifications[:count]}

        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"API Gateway Error in /mobile/notifications: {type(e).__name__} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch mobile notifications: {str(e)}")


@app.get("/mobile/key-metrics", summary="Fetch key metrics for mobile app")
async def get_mobile_key_metrics(user_id: Optional[str] = None):
    """Provides a concise set of key metrics, possibly a subset of executive summary."""
    async with httpx.AsyncClient() as client:
        summary_data = await get_executive_summary()

        kpis = {}
        # Check if summary_data['current_kpis'] is a dict and contains 'calculated_kpis'
        if isinstance(summary_data.get("current_kpis"), dict):
            kpis = summary_data["current_kpis"].get("calculated_kpis", {})
        elif isinstance(summary_data.get("current_kpis"), list): # Fallback if structure is different
             print("Warning: /kpis endpoint returned a list, expected a dict. Using empty kpis for mobile.")

        forecast = summary_data.get("revenue_forecast_next_3_periods", [])

        mobile_metrics = {
            "total_revenue_shopify": kpis.get("total_revenue_shopify"),
            "total_salesforce_revenue": kpis.get("total_salesforce_account_revenue"),
            "open_insights_count": summary_data.get("open_critical_insights_count"),
            "revenue_forecast_trend": "up" if forecast and len(forecast) > 0 and forecast[0].get("predicted_revenue",0) > kpis.get("total_revenue_shopify",0) else "stable/down",
            "last_updated": summary_data.get("last_updated")
        }
        return {"user_id": user_id or "all_users", "key_metrics": mobile_metrics}

class QuickActionUpdate(BaseModel):
    new_status: str
    notes: Optional[str] = None

@app.post("/mobile/actions/{action_id}/quick-update", summary="Quickly update status of an action item from mobile")
async def quick_update_action_status(action_id: str, update: QuickActionUpdate):
    async with httpx.AsyncClient() as client:
        payload_to_analytics = {
            "new_status": update.new_status, # This should be the key for ActionPlanProgress in analytics-engine
            "notes": f"[Mobile Update] {update.notes}" if update.notes else "[Mobile Update]"
        }
        try:
            # The endpoint in analytics-engine is POST /actions/{action_id}/track
            updated_action_response = await call_service(
                client,
                "POST",
                f"{ANALYTICS_ENGINE_URL}/actions/{action_id}/track",
                json_data=payload_to_analytics
            )
            return {"message": "Action status updated successfully via mobile.", "action_details": updated_action_response.get("updated_action_details", updated_action_response)}
        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"API Gateway Error in /mobile/actions/{action_id}/quick-update: {type(e).__name__} - {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to quick update action: {str(e)}")


@app.get("/")
async def root():
    return {"message": "API Gateway / Dashboard API is running. Use /docs for API details."}

# To run this API Gateway:
# Ensure other services (Analytics Engine, ML Models, Notification Service) are running.
# PYTHONPATH=. uvicorn backend.api-gateway.main:app --reload --port 8000
