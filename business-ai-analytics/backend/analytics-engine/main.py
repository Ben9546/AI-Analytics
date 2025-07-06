from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import asyncio
import json
from typing import Dict, Any, List, Optional
import datetime # For timestamping KPIs
import random # For mock recommendations

# Mock Redis client (shared access assumption)
try:
    from ..data_ingestion.main import mock_redis_client as shared_mock_redis
    print("AnalyticsEngine: Successfully accessed shared MockRedis from data-ingestion.")
except ImportError:
    print("AnalyticsEngine: Failed to import shared MockRedis. Using a local instance.")
    class LocalMockRedis: # Basic fallback
        def __init__(self): self.queues = {}
        def lpop(self, queue_name): return self.queues.get(queue_name, []).pop(0) if self.queues.get(queue_name) else None
        def rpush(self, queue_name, data): self.queues.setdefault(queue_name, []).append(data)
        def llen(self, queue_name): return len(self.queues.get(queue_name, []))
    shared_mock_redis = LocalMockRedis()

redis_client = shared_mock_redis # Use the (potentially local) mock_redis_client

# --- Global State for KPIs & Insights (In-memory) ---
calculated_kpis: Dict[str, Any] = {
    "total_revenue_shopify": 0.0, "total_salesforce_account_revenue": 0.0,
    "product_counts_shopify": {}, "last_processed_timestamp": None,
    "anomalies_detected": [], "actionable_insights": []
}

ALERT_QUEUE = "alerts_queue"
NORMALIZED_DATA_QUEUE = "normalized_data_queue"

app = FastAPI(title="Analytics Engine Service (with BI Layer & Action Plan Generator)")

# --- KPI Calculation Logic ---
def update_kpis_from_event(normalized_data_event: Dict[str, Any]):
    global calculated_kpis
    source_system = normalized_data_event.get("source_system")
    data_category = normalized_data_event.get("data_category")
    items = normalized_data_event.get("normalized_fields", {}).get("items", [])
    if not items: return

    if source_system == "shopify":
        if data_category == "orders":
            for order_item_norm in items: # Normalized items
                 # Attempt to find corresponding original payload for richer data if needed
                original_order = None
                if "original_payload" in normalized_data_event and isinstance(normalized_data_event["original_payload"], list):
                    original_order_id_part = str(order_item_norm.get("id","")).replace("shopify-","") # get original id part
                    original_order = next((op for op in normalized_data_event["original_payload"] if str(op.get("id")) == original_order_id_part), None)

                price = 0.0
                if original_order and "total_price" in original_order:
                    price = float(original_order.get("total_price", 0.0))
                elif "price" in order_item_norm: # Fallback to normalized field if available
                    price = float(order_item_norm.get("price", 0.0))

                if price > 0:
                    calculated_kpis["total_revenue_shopify"] += price

        elif data_category == "products":
            for product in items:
                prod_id = product.get("id")
                if prod_id: calculated_kpis["product_counts_shopify"][prod_id] = calculated_kpis["product_counts_shopify"].get(prod_id, 0) + 1
    elif source_system == "salesforce" and data_category == "Account":
        for account in items:
            revenue = account.get("revenue", 0.0)
            if revenue:
                try: calculated_kpis["total_salesforce_account_revenue"] += float(revenue)
                except (ValueError, TypeError): pass

    calculated_kpis["last_processed_timestamp"] = datetime.datetime.utcnow().isoformat()
    newly_detected_anomalies = run_anomaly_detection_rules(normalized_data_event)
    for anomaly in newly_detected_anomalies:
        calculated_kpis["anomalies_detected"].append(anomaly)
        generate_insights_from_anomaly(anomaly)
        try: redis_client.rpush(ALERT_QUEUE, json.dumps(anomaly))
        except Exception as e: print(f"AnalyticsEngine: Failed to push alert to queue: {e}")

# --- Anomaly Detection Rules ---
def run_anomaly_detection_rules(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    detected = []
    if event.get("source_system") == "shopify" and event.get("data_category") == "orders":
        # Use original_payload for richer data if available for anomaly detection
        payload_to_check = event.get("original_payload", [])
        if not isinstance(payload_to_check, list): payload_to_check = [] # ensure iterable

        for item_payload in payload_to_check:
            if isinstance(item_payload, dict) and float(item_payload.get("total_price", 0)) > 1000:
                anomaly = {
                    "type": "HighValueOrder", "source": "Shopify", "order_id": item_payload.get("id"),
                    "amount": float(item_payload.get("total_price")), "timestamp": datetime.datetime.utcnow().isoformat(),
                    "message": f"High value Shopify order: ID {item_payload.get('id')}, Amount {item_payload.get('total_price')}"}
                detected.append(anomaly)
    return detected

# --- Business Intelligence Layer & Action Plan Generator ---
def mock_root_cause_analysis(problem_description: str, related_data: Optional[Dict] = None) -> List[str]:
    causes = ["External factors", "Data quality issue", "Seasonal trend"]
    if "HighValueOrder" in problem_description: causes.extend(["VIP customer", "Bulk order", "Potential fraud"])
    elif "revenue drop" in problem_description.lower(): causes.extend(["Campaign ended", "Competitor action", "Product issue"])
    return random.sample(causes, min(len(causes), random.randint(1,2)))

def mock_solution_recommendation(problem_type: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
    recommendations = []
    now_iso = datetime.datetime.utcnow().isoformat()
    base_action_id = random.randint(10000, 99999)

    common_fields = lambda i: {
        "action_id": f"act_{base_action_id + i}",
        "created_at": now_iso,
        "status": "Pending" # Pending, In Progress, Completed, Cancelled
    }

    if problem_type == "HighValueOrder":
        recommendations.append({
            **common_fields(1), "action": "Review order for fraud", "impact": 8, "effort": 3, "category": "Risk Mitigation",
            "suggested_deadline_days": 1, "resource_requirements": "Fraud Review Team (1hr), Verification tools",
            "expected_outcome": "Confirm legitimacy or cancel fraudulent order, preventing loss.",
            "success_metrics": ["Fraudulent Order Rate", "Loss Prevention Amount ($)"],
            "implementation_guide_summary": "1. Check customer history & IP. 2. Verify payment details via provider. 3. Contact customer if suspicious using template XYZ."
        })
        recommendations.append({
            **common_fields(2), "action": "Assign VIP account manager if legitimate & high value", "impact": 7, "effort": 4, "category": "Customer Relations",
            "suggested_deadline_days": 3, "resource_requirements": "VIP Account Manager (0.5 FTE initial), CRM update",
            "expected_outcome": "Increased customer loyalty, potential for future high-value purchases, gather feedback.",
            "success_metrics": ["Repeat Purchase Rate (VIP)", "Avg Order Value (VIP)", "Customer Satisfaction Score (VIP)"],
            "implementation_guide_summary": "1. Qualify customer as VIP based on order value/history. 2. Assign dedicated manager. 3. Schedule introductory call with script ABC."
        })
    elif problem_type == "LowSalesPerformance":
        recommendations.append({
            **common_fields(3), "action": "Launch targeted promotion for underperforming segments/products", "impact": 7, "effort": 5, "category": "Sales Growth",
            "suggested_deadline_days": 14, "resource_requirements": "Marketing Team (10hrs), Promotion Budget ($500), Email marketing tool",
            "expected_outcome": "10-15% lift in sales from targeted segments/products within 30 days.",
            "success_metrics": ["Sales Volume (Targeted)", "Promotion ROI", "Website Conversion Rate (Targeted)"],
            "implementation_guide_summary": "1. Analyze sales data to identify specific underperforming areas. 2. Design promotion (e.g., discount, bundle). 3. Launch via email/ads and monitor results daily."
        })
        recommendations.append({
            **common_fields(4), "action": "Conduct sales team training on value proposition & objection handling", "impact": 6, "effort": 6, "category": "Operational Improvement",
            "suggested_deadline_days": 30, "resource_requirements": "Sales Training Manager (20hrs), Training Materials, Meeting rooms",
            "expected_outcome": "Improved sales team confidence, product knowledge, and conversion rates by 5%.",
            "success_metrics": ["Product Demo Conversion Rate", "Sales per Rep", "Average Deal Size"],
            "implementation_guide_summary": "1. Develop/update training materials focusing on value. 2. Schedule interactive training sessions. 3. Conduct post-training assessment and role-playing."
        })

    if not recommendations:
        recommendations.append({
            **common_fields(5), "action": "Monitor situation closely and gather more specific data", "impact": 3, "effort": 1, "category": "General",
            "suggested_deadline_days": 7, "resource_requirements": "Analyst (2hrs), Monitoring dashboard setup",
            "expected_outcome": "Better understanding of the situation to inform more targeted future actions.",
            "success_metrics": ["Key Data Points Collected", "Clarity of Issue (documented)", "Trend identification"],
            "implementation_guide_summary": "1. Define key metrics to track related to the issue. 2. Set up or use existing monitoring dashboard. 3. Review data daily and document findings."
        })

    for rec in recommendations:
        rec["priority_score"] = round(rec["impact"] / (rec["effort"] + 0.01) * 10, 1)
    return sorted(recommendations, key=lambda x: x["priority_score"], reverse=True)

def generate_insights_from_anomaly(anomaly: Dict[str, Any]):
    global calculated_kpis
    insight_id = f"insight_{len(calculated_kpis['actionable_insights']) + random.randint(100,999)}" # More unique ID
    root_causes = mock_root_cause_analysis(anomaly["type"], anomaly)
    recommendations = mock_solution_recommendation(anomaly["type"], anomaly)
    insight = {
        "id": insight_id, "type": "AnomalyResponse", "trigger_event_type": anomaly["type"],
        "trigger_event_details": anomaly, "generated_at": datetime.datetime.utcnow().isoformat(),
        "summary": f"Detected {anomaly['type']} (e.g., {anomaly.get('message', 'No message')}). Investigation suggested.",
        "potential_root_causes": root_causes, "recommended_actions": recommendations, "status": "New"
    }
    calculated_kpis["actionable_insights"].append(insight)

def proactively_generate_insights():
    global calculated_kpis
    if calculated_kpis["total_revenue_shopify"] < 100 and calculated_kpis["total_revenue_shopify"] > 0: # Arbitrary low revenue for testing
        if not any(i['trigger_event_type'] == 'LowShopifyRevenue' and i['status'] == 'New' for i in calculated_kpis['actionable_insights']):
            problem_desc = "Low Shopify Revenue Trend"
            insight_id = f"insight_{len(calculated_kpis['actionable_insights']) + random.randint(1000,9999)}"
            root_causes = mock_root_cause_analysis(problem_desc)
            recommendations = mock_solution_recommendation("LowSalesPerformance")
            insight = {
                "id": insight_id, "type": "ProactiveKPIMonitoring", "trigger_event_type": "LowShopifyRevenue",
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "summary": "Shopify revenue appears significantly lower than expected benchmarks. Suggest review.",
                "potential_root_causes": root_causes, "recommended_actions": recommendations, "status": "New"
            }
            calculated_kpis["actionable_insights"].append(insight)

# --- Real-time Processing Worker ---
async def real_time_processor():
    print("AnalyticsEngine: Real-time Processor started...")
    processed_event_count = 0
    while True:
        try:
            data_json = redis_client.lpop(NORMALIZED_DATA_QUEUE)
            if data_json:
                event = json.loads(data_json)
                update_kpis_from_event(event)
                processed_event_count+=1
                if processed_event_count % 2 == 0: # Check for proactive insights more frequently for testing
                    proactively_generate_insights()
            else: await asyncio.sleep(0.5) # Poll a bit faster
        except Exception as e:
            print(f"AnalyticsEngine: Error in real_time_processor: {e}")
            await asyncio.sleep(5)

# --- API Endpoints ---
@app.get("/kpis")
async def get_kpis_endpoint(): return calculated_kpis

@app.get("/anomalies")
async def get_anomalies_endpoint(): return {"anomalies": calculated_kpis["anomalies_detected"]}

@app.get("/insights", summary="Get all actionable insights with detailed action plans")
async def get_actionable_insights():
    return {"actionable_insights": calculated_kpis["actionable_insights"]}

class InsightStatusUpdate(BaseModel):
    status: str

@app.patch("/insights/{insight_id}/status", summary="Update the status of an insight")
async def update_insight_status(insight_id: str, update: InsightStatusUpdate):
    for insight in calculated_kpis["actionable_insights"]:
        if insight["id"] == insight_id:
            insight["status"] = update.status
            insight["last_updated_at"] = datetime.datetime.utcnow().isoformat()
            return {"message": "Insight status updated", "insight": insight}
    raise HTTPException(status_code=404, detail="Insight not found")

class ActionPlanProgress(BaseModel):
    action_id: str # This should match action_id within an insight's recommended_actions
    progress_percentage: Optional[int] = None
    notes: Optional[str] = None
    new_status: Optional[str] = None # e.g. "In Progress", "Completed", "Blocked"

@app.post("/actions/{action_id}/track", summary="Track progress or update status of a specific action") # Changed from /track-action
async def track_action_item_progress(action_id: str, progress: ActionPlanProgress): # action_id from path
    action_found_and_updated = False
    for insight in calculated_kpis["actionable_insights"]:
        for action in insight.get("recommended_actions", []):
            if action.get("action_id") == action_id: # Match action_id from path
                if progress.progress_percentage is not None: # Check for None before assigning
                    action["progress_percentage"] = progress.progress_percentage
                if progress.notes:
                    action["notes"] = action.get("notes", "") + f"\n{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')}: {progress.notes}"
                if progress.new_status:
                    action["status"] = progress.new_status
                action["last_updated_at"] = datetime.datetime.utcnow().isoformat()
                action_found_and_updated = True
                return {"message": "Action item progress updated", "action_id": action_id, "updated_action_details": action}

    if not action_found_and_updated:
        raise HTTPException(status_code=404, detail=f"Action ID '{action_id}' not found in any insight.")


@app.get("/queue-status/{queue_name}")
async def get_analytics_queue_status(queue_name: str):
    length = redis_client.llen(queue_name)
    return {"queue_name": queue_name, "length": length}

@app.on_event("startup")
async def startup_event():
    print("AnalyticsEngine: Starting background real-time processor and BI tasks...")
    asyncio.create_task(real_time_processor())

@app.get("/")
async def root():
    return {"message": "Analytics Engine Service with BI Layer & Action Plan Generator is running. Use /docs for API details."}
