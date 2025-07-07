from fastapi import APIRouter, Depends, Request, HTTPException, Body, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import datetime
from datetime import timezone # Import timezone
import random
import uuid # For generating unique IDs for mock entities

# Conceptual: Placeholder for a dependency that would get the current user
async def get_current_user_from_state(request: Request) -> Optional[Dict[str, Any]]:
    if hasattr(request.state, "current_user") and request.state.current_user:
        return request.state.current_user
    # For most dashboard endpoints, we'll assume authentication is enforced by middleware.
    # If an endpoint could be public, it should handle current_user being None.
    # For now, if middleware didn't block, we assume user is present or endpoint is fine with Guest.
    # To enforce strictly on an endpoint:
    # if not request.state.current_user:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")
    return None

router = APIRouter()

# --- Mock Data Stores (Conceptual - would be in a database) ---
mock_custom_metrics_db: List[Dict[str, Any]] = [
    {"id": "metric_sales_growth", "name": "Monthly Sales Growth", "formula": "(current_month_sales - previous_month_sales) / previous_month_sales", "user_created": False},
    {"id": "metric_churn_rate", "name": "Customer Churn Rate", "formula": "lost_customers / total_customers_start_period", "user_created": False}
]
mock_forecasts_db: Dict[str, Dict[str, Any]] = {}
mock_action_plans_db: List[Dict[str, Any]] = [
    {
        "id": "plan_reduce_churn_q3", "title": "Q3 Churn Reduction Initiative", "status": "In Progress",
        "recommendations": [
            {"id": "rec_churn_1", "description": "Launch re-engagement email campaign for at-risk customers.", "priority": "High", "assigned_to": "marketing_team", "due_date": (datetime.date.today() + datetime.timedelta(days=30)).isoformat(), "progress": 30, "status": "In Progress"},
            {"id": "rec_churn_2", "description": "Offer loyalty discount to customers nearing renewal.", "priority": "Medium", "assigned_to": "sales_team", "due_date": (datetime.date.today() + datetime.timedelta(days=45)).isoformat(), "progress": 0, "status": "Pending"}
        ]
    }
]

# --- Main Dashboard Endpoints ---
@router.get("/main/executive-summary", summary="Data for Executive Summary Cards")
async def get_executive_summary_data(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    total_revenue = random.randint(50000, 200000)
    return {
        "executive_summary_cards": [
            {"title": "Total Revenue (Last 30d)", "value": f"${total_revenue:,.2f}", "trend": random.choice(["+5%", "-2%"])},
            {"title": "New Customers (Last 30d)", "value": str(random.randint(50, 200)), "trend": random.choice(["+10", "-3"])},
            {"title": "Active Integrations", "value": str(random.randint(1, 10)), "status": "healthy"},
            {"title": "Open Critical Alerts", "value": str(random.randint(0, 5)), "status": "warning" if random.randint(0,5) > 2 else "ok"},
        ],
        "quick_insights": {"revenue_forecast_trend_short_term": random.choice(["up", "stable", "down"])},
        "last_updated": datetime.datetime.now(timezone.utc).isoformat()
    }

@router.get("/main/realtime-metric-widgets", summary="Data for Real-time Metric Widgets")
async def get_realtime_metric_widgets_data(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    return {
        "widgets": [
            {"id": "widget_sales_per_min", "title": "Sales/min (Live)", "value": random.randint(0, 10), "unit": "transactions"},
            {"id": "widget_website_visitors", "title": "Live Website Visitors", "value": random.randint(50, 500), "unit": "users"},
        ], "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }

@router.get("/main/interactive-charts", summary="Data for Interactive Charts and Graphs")
async def get_interactive_charts_data(period: str = "last_30_days", current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    num_points = 30 if period == "last_30_days" else 7
    dates = [(datetime.datetime.now(timezone.utc) - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_points)][::-1]
    revenue_data = [random.randint(1000, 5000) + (i*50) for i in range(num_points)]
    return {
        "period": period, "charts": [{
            "id": "chart_revenue_trends", "title": "Revenue Trends", "type": "line", "labels": dates,
            "datasets": [{"label": "Total Revenue", "data": revenue_data, "borderColor": "rgb(75, 192, 192)"}]
        }], "generated_at": datetime.datetime.now(timezone.utc).isoformat()
    }

@router.get("/main/alert-notifications", summary="Data for Alert Notifications Panel")
async def get_alert_notifications_panel_data(limit: int = 5, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    alert_types = ["High Churn Risk", "Ad Spend Spike", "Low Inventory"]
    alerts = [{"id": f"alert_{uuid.uuid4()}", "type": random.choice(alert_types), "message": f"Mock Alert: {random.choice(alert_types)}.",
               "timestamp": (datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=random.randint(1,1440))).isoformat(),
               "severity": random.choice(["critical", "warning", "info"])} for _ in range(limit)]
    return {"alerts": sorted(alerts, key=lambda x: x["timestamp"], reverse=True)}

# --- Real-Time Tracking Module Endpoints ---
@router.get("/realtime/live-data-stream-config", summary="Configuration for live data streams (WebSocket)")
async def get_live_data_stream_config(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    # This endpoint might provide info on available streams or auth tokens for WS.
    # Actual data flows over WebSocket (/ws/realtime/{client_id} in main.py)
    return {"message": "WebSocket connection for live data is available at /ws/realtime/{client_id}.",
            "available_streams": ["sales_stream", "visitor_stream", "system_health_stream"]} # Mock

class CustomMetricCreate(BaseModel):
    name: str
    formula: str # Or a more structured definition
    description: Optional[str] = None

@router.post("/realtime/custom-metrics", status_code=status.HTTP_201_CREATED, summary="Create a new custom metric definition")
async def create_custom_metric(metric: CustomMetricCreate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    new_metric = metric.model_dump()
    new_metric["id"] = f"metric_{uuid.uuid4()}"
    new_metric["user_created"] = True
    mock_custom_metrics_db.append(new_metric)
    return new_metric

@router.get("/realtime/custom-metrics", summary="List custom metric definitions")
async def list_custom_metrics(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    return {"custom_metrics": mock_custom_metrics_db}

@router.get("/realtime/trend-analysis-charts", summary="Data for Trend Analysis Charts in Real-Time Module")
async def get_realtime_trend_analysis_charts(metric_id: str, period: str = "last_hour", current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    # Mock data for a specific metric's trend
    num_points = 60 # e.g., per minute for last hour
    labels = [(datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=i*1)).strftime("%H:%M") for i in range(num_points)][::-1]
    data = [random.randint(50, 150) + random.uniform(-10,10) for _ in range(num_points)]
    return {
        "metric_id": metric_id, "period": period, "title": f"Trend for {metric_id}", "type": "line",
        "labels": labels, "datasets": [{"label": metric_id, "data": data, "borderColor": "rgb(255, 159, 64)"}]
    }

# --- Forecasting Interface Endpoints ---
class ForecastRequest(BaseModel):
    metric_to_forecast: str
    periods: int = 12 # e.g., 12 months
    historical_data_override: Optional[List[Dict[str, Any]]] = None # Allow providing data

@router.post("/forecasting/generate", status_code=status.HTTP_202_ACCEPTED, summary="Generate a new forecast")
async def generate_forecast(request: ForecastRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    forecast_id = f"forecast_{uuid.uuid4()}"
    # Mock: Simulate starting a forecast generation
    mock_forecasts_db[forecast_id] = {
        "id": forecast_id, "metric": request.metric_to_forecast, "periods": request.periods,
        "status": "processing", "requested_at": datetime.datetime.now(timezone.utc).isoformat(), "results": None # Corrected
    }
    # In a real app, this would trigger a background task.
    # Simulate completion after a delay for mock purposes:
    async def _simulate_forecast_completion():
        await asyncio.sleep(2) # Simulate processing time
        if forecast_id in mock_forecasts_db:
            num_points = mock_forecasts_db[forecast_id]["periods"]
            dates = [(datetime.date.today() + datetime.timedelta(days=i*30)).strftime("%Y-%m-%d") for i in range(1, num_points + 1)] # Using today for future dates
            predictions = [random.randint(1000,5000) * (1 + i*0.05) for i in range(num_points)]
            ci_lower = [p * 0.8 for p in predictions]
            ci_upper = [p * 1.2 for p in predictions]
            mock_forecasts_db[forecast_id].update({
                "status": "completed",
                "results": {"dates": dates, "predictions": predictions, "confidence_interval_lower": ci_lower, "confidence_interval_upper": ci_upper},
                "completed_at": datetime.datetime.now(timezone.utc).isoformat()
            })
    # This background task is for mock only; real systems use Celery/etc.
    # For a simple test, you might run this directly or not at all and update status manually for GET.
    # Not using FastAPI BackgroundTasks here as it's tied to request lifecycle.
    # asyncio.create_task(_simulate_forecast_completion()) # This would run it truly async

    # For simpler immediate mock:
    num_points = request.periods
    dates = [(datetime.date.today() + datetime.timedelta(days=i*30)).strftime("%Y-%m-%d") for i in range(1, num_points + 1)] # Using today for future dates
    predictions = [random.randint(1000,5000) * (1 + i*0.05) for i in range(num_points)]
    mock_forecasts_db[forecast_id].update({
        "status": "completed",
        "results": {"dates": dates, "predictions": predictions},
        "completed_at": datetime.datetime.now(timezone.utc).isoformat()  # Corrected
    })
    # Also update the requested_at in the initial mock_forecasts_db entry
    mock_forecasts_db[forecast_id]["requested_at"] = datetime.datetime.now(timezone.utc).isoformat()


    return {"message": "Forecast generation started (mocked as completed).", "forecast_id": forecast_id, "details": mock_forecasts_db[forecast_id]}


@router.get("/forecasting/results/{forecast_id}", summary="Get results of a specific forecast")
async def get_forecast_results(forecast_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    forecast = mock_forecasts_db.get(forecast_id)
    if not forecast:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast not found")
    return forecast

class ScenarioInput(BaseModel):
    parameter_name: str
    change_percentage: float # e.g., 0.10 for +10%, -0.05 for -5%

@router.post("/forecasting/scenarios", summary="Run a what-if scenario on a forecast (conceptual)")
async def run_what_if_scenario(forecast_id: str, scenario: ScenarioInput, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    original_forecast = mock_forecasts_db.get(forecast_id)
    if not original_forecast or original_forecast["status"] != "completed":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Completed forecast not found to run scenario.")

    # Mock: Adjust predictions based on scenario
    adjusted_predictions = [p * (1 + scenario.change_percentage) for p in original_forecast["results"]["predictions"]]
    return {
        "scenario_applied": scenario.model_dump(),
        "original_forecast_id": forecast_id,
        "scenario_results": {
            "dates": original_forecast["results"]["dates"],
            "adjusted_predictions": adjusted_predictions
        }
    }

# --- Action Plan Center Endpoints ---
@router.get("/action-plans/recommendations", summary="List prioritized recommendations/action plans")
async def get_action_plan_recommendations(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    # This data would come from a more sophisticated insights/recommendation engine
    return {"action_plans": mock_action_plans_db}

class TaskUpdate(BaseModel):
    progress: Optional[int] = None
    status: Optional[str] = None # e.g., "Pending", "In Progress", "Completed", "Blocked"
    assigned_to: Optional[str] = None

@router.put("/action-plans/{plan_id}/recommendations/{recommendation_id}", summary="Update a task/recommendation")
async def update_action_plan_task(plan_id: str, recommendation_id: str, update: TaskUpdate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_from_state)):
    for plan in mock_action_plans_db:
        if plan["id"] == plan_id:
            for rec in plan.get("recommendations", []):
                if rec["id"] == recommendation_id:
                    if update.progress is not None: rec["progress"] = update.progress
                    if update.status is not None: rec["status"] = update.status
                    if update.assigned_to is not None: rec["assigned_to"] = update.assigned_to
                    rec["last_updated"] = datetime.datetime.now(timezone.utc).isoformat() # Corrected
                    return rec # Correctly indented
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action plan or recommendation not found.")
