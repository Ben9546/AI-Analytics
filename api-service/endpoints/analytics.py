from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import random

router = APIRouter()

class CustomMetric(BaseModel):
    id: Optional[str] = None
    name: str
    query_definition: str # e.g., SQL-like query, or DSL

mock_custom_analytics_metrics_db: List[CustomMetric] = []

@router.get("/realtime", summary="Get real-time analytics data (mock)")
async def get_realtime_analytics(metrics: Optional[List[str]] = None):
    # Mock real-time data for requested metrics or general overview
    data = {}
    if metrics:
        for metric in metrics:
            data[metric] = round(random.uniform(10, 1000), 2)
    else:
        data = {
            "active_users": random.randint(100,1000),
            "conversion_rate": round(random.uniform(0.5, 5.0), 2),
            "average_session_duration_sec": random.randint(60, 600)
        }
    return {"realtime_data": data, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}

@router.get("/metrics", response_model=List[CustomMetric], summary="List available custom analytics metrics (mock)")
async def list_analytics_metrics():
    return mock_custom_analytics_metrics_db

@router.post("/custom-metrics", response_model=CustomMetric, status_code=status.HTTP_201_CREATED, summary="Create a custom analytics metric (mock)")
async def create_custom_analytics_metric(metric: CustomMetric):
    import uuid
    new_metric = metric.model_copy(update={"id": str(uuid.uuid4())})
    mock_custom_analytics_metrics_db.append(new_metric)
    return new_metric

import datetime # For timestamp
from datetime import timezone # For timezone.utc
