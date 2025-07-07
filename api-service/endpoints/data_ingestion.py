from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Assuming verify_api_key is in main or a shared auth module
# For simplicity here, if main.py defines it, tests will mock or use it via app.
# from ..main import verify_api_key (if main.py is one level up and a package)
# If running tests from root, and api_service is a package:
# from api_service.main import verify_api_key

router = APIRouter()

class DataSource(BaseModel):
    id: Optional[str] = None
    name: str
    type: str # e.g., "quickbooks", "salesforce"
    config: Dict[str, Any] # Connection details, encrypted in real app

mock_data_sources_db: List[DataSource] = []

@router.post("/ingest", summary="Ingest data from a configured source (mock)")
async def ingest_data(payload: Dict[str, Any] = Body(...)): #, key_details: dict = Depends(verify_api_key)):
    # Mock ingestion - in reality, this would trigger a data pipeline
    # based on source_id or type in payload.
    # verify_api_key dependency will be added at router inclusion in main.py
    return {"message": "Data ingestion request received (mock).", "payload_summary": payload.get("source_name", "Unknown source")}

@router.get("/sources", response_model=List[DataSource], summary="List configured data sources (mock)")
async def list_data_sources(): #key_details: dict = Depends(verify_api_key)):
    return mock_data_sources_db

@router.put("/sources/{source_id}", response_model=DataSource, summary="Update a data source configuration (mock)")
async def update_data_source(source_id: str, source_update: DataSource): #, key_details: dict = Depends(verify_api_key)):
    for i, source in enumerate(mock_data_sources_db):
        if source.id == source_id:
            # In a real app, ensure all fields of source_update are applied carefully
            updated_source_data = source_update.model_dump(exclude_unset=True)
            mock_data_sources_db[i] = DataSource(**{**source.model_dump(), **updated_source_data})
            return mock_data_sources_db[i]
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

@router.post("/sources", response_model=DataSource, status_code=status.HTTP_201_CREATED, summary="Add a new data source (mock)")
async def add_data_source(source: DataSource): #, key_details: dict = Depends(verify_api_key)):
    import uuid
    new_source = source.model_copy(update={"id": str(uuid.uuid4())})
    mock_data_sources_db.append(new_source)
    return new_source
