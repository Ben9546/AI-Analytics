from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
import datetime
import random # For generating mock predictions
import asyncio # For background tasks like retraining

app = FastAPI(title="AI Prediction Service / ML Models Service")

# --- Mock Data Store / Model Representation & Accuracy Tracking ---
mock_historical_revenue_data = {
    "monthly": [
        {"date": "2023-01-01", "revenue": 10000}, {"date": "2023-02-01", "revenue": 11000},
        {"date": "2023-03-01", "revenue": 10500}, {"date": "2023-04-01", "revenue": 12000},
        {"date": "2023-05-01", "revenue": 13000}, {"date": "2023-06-01", "revenue": 12500},
        {"date": "2023-07-01", "revenue": 14000}, {"date": "2023-08-01", "revenue": 15000},
        {"date": "2023-09-01", "revenue": 14500}, {"date": "2023-10-01", "revenue": 16000},
        {"date": "2023-11-01", "revenue": 17000}, {"date": "2023-12-01", "revenue": 18000},
    ]
}
mock_customer_data_for_clv = [
    {"customer_id": "cust_001", "total_spent": 500, "purchase_frequency": 5, "age_months": 12, "churn_risk_score": 0.1},
    {"customer_id": "cust_002", "total_spent": 1200, "purchase_frequency": 10, "age_months": 24, "churn_risk_score": 0.05},
    {"customer_id": "cust_003", "total_spent": 200, "purchase_frequency": 2, "age_months": 6, "churn_risk_score": 0.3},
]

# In-memory store for prediction vs actuals (for accuracy measurement)
prediction_log: List[Dict[str, Any]] = []

# Mock model versions and validation scores
model_validation_scores: Dict[str, Dict[str, Any]] = {
    "mock_time_series_v1": {"validation_date": "2023-01-01", "accuracy_mape": 0.15, "last_trained_on_data_until": "2022-12-31"},
    "mock_isolation_forest_v1": {"validation_date": "2023-01-01", "f1_score_anomalies": 0.75},
}

# --- 1. Revenue Forecasting ---
class RevenueForecastRequest(BaseModel):
    historical_data: List[Dict[str, Any]] = None
    future_periods: int = 12
    model_type: str = "mock_time_series_v1"

def mock_time_series_forecast(data: List[Dict[str, Any]], periods: int, model_version: str) -> List[Dict[str, Any]]:
    forecasts = []
    if not data: return forecasts # Should not happen if called after validation
    last_date_str = data[-1]["date"]
    last_revenue = data[-1]["revenue"]
    current_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d")

    for i in range(periods):
        current_date += datetime.timedelta(days=30)
        forecasted_revenue = last_revenue * (1 + random.uniform(0.01, 0.05))
        if current_date.month in [1, 2, 12]: forecasted_revenue *= random.uniform(0.95, 1.05)

        forecast_entry = {
            "date": current_date.strftime("%Y-%m-%d"),
            "predicted_revenue": round(forecasted_revenue, 2),
            "confidence_interval": [round(forecasted_revenue * 0.9, 2), round(forecasted_revenue * 1.1, 2)],
            "model_version": model_version
        }
        forecasts.append(forecast_entry)
        # Log prediction for future accuracy calculation (actuals would be fed later)
        prediction_log.append({
            "type": "revenue_forecast",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "prediction_id": f"rev_fcst_{len(prediction_log)}",
            "details": forecast_entry,
            "actual_value": None # To be filled later
        })
        last_revenue = forecasted_revenue
    return forecasts

@app.post("/forecast/revenue", summary="Forecast future revenue")
async def forecast_revenue(request: RevenueForecastRequest):
    data_to_use = request.historical_data if request.historical_data else mock_historical_revenue_data["monthly"]
    if not data_to_use:
        raise HTTPException(status_code=400, detail="Historical data not provided.")

    if request.model_type in model_validation_scores and "accuracy_mape" in model_validation_scores[request.model_type]:
        forecast = mock_time_series_forecast(data_to_use, request.future_periods, request.model_type)
        return {
            "model_used": request.model_type,
            "model_validation_score_mape": model_validation_scores[request.model_type]["accuracy_mape"],
            "forecast_periods": request.future_periods,
            "forecast": forecast
        }
    else:
        raise HTTPException(status_code=400, detail=f"Model type '{request.model_type}' not supported or validated for revenue forecasting.")

# --- 2. Risk Detection ---
class RiskDetectionRequest(BaseModel):
    data_points: List[Dict[str, Any]]
    model_type: str = "mock_isolation_forest_v1"

def mock_anomaly_detection(data_points: List[Dict[str, Any]], model_version: str) -> List[Dict[str, Any]]:
    results = []
    for i, dp in enumerate(data_points):
        is_anomaly = random.random() < 0.05
        score = random.random()
        result_entry = {
            "data_point_index": i,
            "is_anomaly": is_anomaly,
            "anomaly_score": round(score, 3) if is_anomaly else round(score * 0.1, 3),
            "details": "Mock anomaly detected." if is_anomaly else "Normal.",
            "model_version": model_version
        }
        results.append(result_entry)
        prediction_log.append({
            "type": "risk_detection",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "prediction_id": f"risk_{len(prediction_log)}",
            "details": result_entry,
            "actual_is_anomaly": None # To be filled later if feedback is available
        })
    return results

@app.post("/detect/risk", summary="Detect risks or anomalies in data")
async def detect_risk(request: RiskDetectionRequest):
    if not request.data_points:
        raise HTTPException(status_code=400, detail="No data points provided.")

    if request.model_type in model_validation_scores and "f1_score_anomalies" in model_validation_scores[request.model_type]:
        anomalies = mock_anomaly_detection(request.data_points, request.model_type)
        return {
            "model_used": request.model_type,
            "model_validation_f1_score": model_validation_scores[request.model_type]["f1_score_anomalies"],
            "detected_anomalies": [a for a in anomalies if a["is_anomaly"]],
            "full_results": anomalies
        }
    else:
        raise HTTPException(status_code=400, detail=f"Model type '{request.model_type}' not supported or validated for risk detection.")

# --- 3. Opportunity Identification (Simplified, less focus on accuracy system for this mock) ---
class OpportunityRequest(BaseModel):
    customer_id: str = None
    market_segment: str = None

def mock_predict_clv(customer_id: str) -> Dict[str, Any]:
    customer = next((c for c in mock_customer_data_for_clv if c["customer_id"] == customer_id), None)
    if not customer: return {"error": "Customer not found", "predicted_clv": 0}
    clv = customer["total_spent"] * (1 / customer["churn_risk_score"] if customer["churn_risk_score"] > 0.01 else 100)
    return {
        "customer_id": customer_id,
        "predicted_clv": round(clv * random.uniform(0.8, 1.2), 2),
        "next_best_action": random.choice(["Offer discount", "Personalized email"])
    }

@app.post("/identify/opportunity", summary="Identify potential business opportunities")
async def identify_opportunity(request: OpportunityRequest):
    if request.customer_id:
        clv_prediction = mock_predict_clv(request.customer_id)
        return {"opportunity_type": "CustomerLifetimeValue", "prediction": clv_prediction}
    elif request.market_segment:
        return {
            "opportunity_type": "MarketExpansion", "market_segment": request.market_segment,
            "potential_score": round(random.uniform(0.5, 0.95), 3),
            "recommendation": "Suggest market research."
        }
    else:
        raise HTTPException(status_code=400, detail="Specify opportunity type via parameters.")

# --- 4. Prediction Accuracy System ---
class ActualData(BaseModel):
    prediction_id: str
    actual_value: Any # Can be float for revenue, bool for anomaly, etc.

@app.post("/log-actual", summary="Log actual outcome for a prior prediction")
async def log_actual_value(actual: ActualData):
    found = False
    for log_entry in prediction_log:
        if log_entry["prediction_id"] == actual.prediction_id:
            log_entry["actual_value"] = actual.actual_value
            log_entry["actual_logged_at"] = datetime.datetime.utcnow().isoformat()
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Prediction ID not found.")
    return {"message": "Actual value logged successfully.", "prediction_id": actual.prediction_id}

@app.get("/accuracy-report/{prediction_type}", summary="Get a simple accuracy report")
async def get_accuracy_report(prediction_type: str):
    relevant_predictions = [p for p in prediction_log if p["type"] == prediction_type and p["actual_value"] is not None]
    if not relevant_predictions:
        return {"message": "No predictions with actuals logged for this type.", "accuracy": None}

    if prediction_type == "revenue_forecast":
        errors = []
        for p in relevant_predictions:
            predicted = p["details"]["predicted_revenue"]
            actual = p["actual_value"]
            if actual != 0: # Avoid division by zero for MAPE
                errors.append(abs(predicted - actual) / actual)
        mape = sum(errors) / len(errors) if errors else 0
        return {"prediction_type": prediction_type, "count": len(relevant_predictions), "accuracy_mape": round(mape, 4)}

    elif prediction_type == "risk_detection": # Basic count for mock
        correct_predictions = 0
        for p in relevant_predictions:
            if p["details"]["is_anomaly"] == p["actual_value"]: # Assuming actual_value is boolean for anomaly
                correct_predictions +=1
        accuracy = correct_predictions / len(relevant_predictions) if relevant_predictions else 0
        return {"prediction_type": prediction_type, "count": len(relevant_predictions), "simple_accuracy": round(accuracy, 4)}

    return {"message": f"Accuracy report for type '{prediction_type}' not implemented yet."}

# --- 5. Model Validation & Retraining (Conceptual) ---
@app.post("/models/{model_name}/validate", summary="Simulate model validation")
async def validate_model(model_name: str):
    # In a real system: load model, run against validation dataset, calculate metrics
    if model_name not in model_validation_scores:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found for validation.")

    # Simulate re-validation: slightly change score
    if "accuracy_mape" in model_validation_scores[model_name]:
        model_validation_scores[model_name]["accuracy_mape"] *= random.uniform(0.95, 1.05)
    if "f1_score_anomalies" in model_validation_scores[model_name]:
         model_validation_scores[model_name]["f1_score_anomalies"] *= random.uniform(0.95, 1.05)
    model_validation_scores[model_name]["validation_date"] = datetime.datetime.utcnow().isoformat()

    return {"message": f"Model {model_name} re-validation simulated.", "new_scores": model_validation_scores[model_name]}

async def _retrain_model_background_task(model_name: str):
    print(f"Starting retraining for model: {model_name}...")
    await asyncio.sleep(10) # Simulate time-consuming retraining process

    # Update mock validation scores after "retraining"
    if model_name in model_validation_scores:
        if "accuracy_mape" in model_validation_scores[model_name]:
            model_validation_scores[model_name]["accuracy_mape"] = random.uniform(0.05, 0.15) # Simulate improved/changed score
        if "f1_score_anomalies" in model_validation_scores[model_name]:
            model_validation_scores[model_name]["f1_score_anomalies"] = random.uniform(0.7, 0.9)
        model_validation_scores[model_name]["last_trained_on_data_until"] = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        model_validation_scores[model_name]["validation_date"] = datetime.datetime.utcnow().isoformat()
        print(f"Retraining for model: {model_name} completed. New scores: {model_validation_scores[model_name]}")
    else:
        print(f"Retraining for model: {model_name} failed or model not found for score update.")

@app.post("/models/{model_name}/retrain", summary="Trigger model retraining (mock)")
async def trigger_model_retraining(model_name: str, background_tasks: BackgroundTasks):
    if model_name not in model_validation_scores: # Only allow retraining of "existing" models
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found, cannot retrain.")

    background_tasks.add_task(_retrain_model_background_task, model_name)
    return {"message": f"Retraining process for model {model_name} started in the background."}

@app.get("/models/validation-scores", summary="Get current validation scores for all models")
async def get_all_validation_scores():
    return model_validation_scores

@app.get("/")
async def root():
    return {"message": "AI Prediction Service is running. Use /docs for API details."}

# To run this service (example using uvicorn):
# uvicorn business-ai-analytics.backend.ml-models.main:app --reload --port 8003
# Ensure PYTHONPATH is set, e.g.:
# PYTHONPATH=. uvicorn backend.ml-models.main:app --reload --port 8003 (from business-ai-analytics directory)
