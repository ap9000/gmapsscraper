from __future__ import annotations

import csv
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, File, UploadFile

from ..websocket import websocket_manager
from .search import run_background_search

router = APIRouter()


class BatchSearchRequest(BaseModel):
    enrich: bool = Field(True, description="Whether to enrich with email addresses")
    export_format: Optional[str] = Field(None, description="Export format: csv, json, or hubspot")


class BatchResponse(BaseModel):
    success: bool
    batch_id: str
    message: str
    searches_count: int
    error: Optional[str] = None


@router.post("/upload", response_model=BatchResponse)
async def batch_upload(
    file: UploadFile = File(...),
    enrich: bool = True,
    export_format: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    request: Request = None
):
    """Upload CSV file and start batch processing."""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read CSV content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV
        searches: List[Dict[str, Any]] = []
        try:
            reader = csv.DictReader(csv_content.splitlines())
            for row in reader:
                if 'query' in row and row['query'].strip():
                    searches.append({
                        'query': row['query'].strip(),
                        'location': row.get('location', '').strip() or None,
                        'max_results': int(row.get('max_results', 100) or 100)
                    })
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {e}")
        
        if not searches:
            raise HTTPException(status_code=400, detail="No valid searches found in CSV")
        
        # Generate batch ID
        import uuid
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        
        # Start batch processing
        background_tasks.add_task(
            run_batch_searches,
            batch_id,
            searches,
            enrich,
            export_format,
            request.app.state
        )
        
        return BatchResponse(
            success=True,
            batch_id=batch_id,
            message=f"Batch processing started for {len(searches)} searches",
            searches_count=len(searches)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_batch_searches(
    batch_id: str,
    searches: List[Dict[str, Any]],
    enrich: bool,
    export_format: Optional[str],
    app_state
):
    """Run batch searches in background."""
    try:
        total_searches = len(searches)
        total_businesses = 0
        
        websocket_manager.emit_search_progress(
            batch_id, 0, "starting", 
            f"Starting batch processing of {total_searches} searches"
        )
        
        for i, search_config in enumerate(searches, 1):
            try:
                # Create individual job ID for each search
                import main as core
                job_id = core.generate_job_id(search_config['query'], search_config.get('location'))
                
                websocket_manager.emit_search_progress(
                    batch_id, int((i-1) / total_searches * 100), "processing",
                    f"Processing search {i}/{total_searches}: {search_config['query']}"
                )
                
                # Run individual search
                await run_background_search(
                    job_id,
                    search_config['query'],
                    search_config.get('location'),
                    search_config['max_results'],
                    enrich,
                    export_format,
                    None,  # filename
                    app_state
                )
                
                # Get results count for this search
                db = app_state.db
                businesses = db.get_businesses_by_job_id(job_id) if hasattr(db, 'get_businesses_by_job_id') else []
                search_count = len(businesses) if businesses else 0
                total_businesses += search_count
                
                websocket_manager.emit_search_progress(
                    batch_id, int(i / total_searches * 100), "processing",
                    f"Completed {i}/{total_searches} searches. Found {search_count} businesses this search, {total_businesses} total."
                )
                
            except Exception as e:
                websocket_manager.emit_error(
                    batch_id,
                    f"Error in search {i}: {e}",
                    "batch_search"
                )
        
        websocket_manager.emit_search_progress(
            batch_id, 100, "completed",
            f"Batch completed! Processed {total_searches} searches, found {total_businesses} total businesses"
        )
        
    except Exception as e:
        websocket_manager.emit_error(batch_id, f"Batch processing failed: {e}", "batch")


@router.get("/{batch_id}")
async def get_batch_status(batch_id: str, request: Request):
    """Get status of a batch processing job."""
    try:
        # This would need to be implemented with proper batch tracking
        return {
            "batch_id": batch_id,
            "status": "unknown",
            "message": "Batch status tracking not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))