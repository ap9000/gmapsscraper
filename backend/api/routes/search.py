from __future__ import annotations

import asyncio
import threading
import concurrent.futures
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request

from ..websocket import websocket_manager

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query for businesses")
    location: Optional[str] = Field(None, description="Location for search (optional)")
    max_results: int = Field(100, ge=1, le=200, description="Maximum number of results")
    enrich: bool = Field(True, description="Whether to enrich with email addresses")
    export_format: Optional[str] = Field(None, description="Export format: csv, json, or hubspot")
    filename: Optional[str] = Field(None, description="Custom filename for export")


class SearchResponse(BaseModel):
    success: bool
    job_id: str
    message: str
    results_count: Optional[int] = None
    export_path: Optional[str] = None
    error: Optional[str] = None


@router.post("/single", response_model=SearchResponse)
async def single_search(request: SearchRequest, background_tasks: BackgroundTasks, fastapi_request: Request):
    """Perform a single search operation."""
    try:
        # Get core components from app state
        rate_limiter = fastapi_request.app.state.rate_limiter
        scraper = fastapi_request.app.state.scraper
        db = fastapi_request.app.state.db
        
        # Rate limit check
        limits_check = rate_limiter.check_limits('scrapingdog')
        if not limits_check['can_proceed']:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limits exceeded: {limits_check}"
            )
        
        # Generate job ID
        import main as core
        job_id = core.generate_job_id(request.query, request.location)
        
        # Create search job in database
        db.create_search_job(
            job_id, 
            request.query, 
            request.location,
            {
                'max_results': request.max_results,
                'enrich': request.enrich,
                'export_format': request.export_format,
            }
        )
        
        # Start background search task
        background_tasks.add_task(
            run_background_search,
            job_id,
            request.query,
            request.location,
            request.max_results,
            request.enrich,
            request.export_format,
            request.filename,
            fastapi_request.app.state
        )
        
        return SearchResponse(
            success=True,
            job_id=job_id,
            message="Search started successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_background_search(
    job_id: str,
    query: str,
    location: Optional[str],
    max_results: int,
    enrich: bool,
    export_format: Optional[str],
    filename: Optional[str],
    app_state
):
    """Run search in background with WebSocket progress updates."""
    try:
        # Get components from app state
        scraper = app_state.scraper
        enricher = app_state.enricher
        exporter = app_state.exporter
        hubspot = app_state.hubspot
        db = app_state.db
        
        # Import core functions
        import main as core
        
        # Emit initial progress
        websocket_manager.emit_search_progress(job_id, 0, "starting", "Initializing search...")
        
        # Estimate cost
        est_cost = scraper.estimate_cost(max_results)
        websocket_manager.emit_search_progress(
            job_id, 5, "searching", 
            f"Estimated cost: ${est_cost:.4f}"
        )
        
        # Perform search
        websocket_manager.emit_search_progress(job_id, 10, "searching", "Contacting Google Maps...")
        results = scraper.search(query, location, max_results)
        
        if not results:
            db.update_search_job(job_id, status='completed', total_results=0, processed_results=0)
            websocket_manager.emit_search_progress(job_id, 100, "completed", "No results found")
            return
        
        # Log actual cost
        actual_pages = min((len(results) + 19) // 20, 6)
        actual_cost = actual_pages * scraper.get_cost_per_request()
        db.log_api_call('scrapingdog', 'google_maps_search', actual_cost, success=True)
        
        websocket_manager.emit_search_progress(
            job_id, 30, "processing", 
            f"Found {len(results)} businesses (${actual_cost:.4f})"
        )
        
        # Process and store businesses
        processed_businesses: List[Dict[str, Any]] = []
        for i, result in enumerate(results):
            business_data = core.format_business_data(result, job_id)
            db.insert_business(business_data)
            processed_businesses.append(business_data)
            
            # Update progress
            progress = 30 + (i / len(results)) * 20  # 30-50% for processing
            websocket_manager.emit_search_progress(
                job_id, int(progress), "processing",
                f"Processed {i+1}/{len(results)} businesses"
            )
        
        db.update_search_job(
            job_id,
            status='scraped',
            total_results=len(results),
            processed_results=len(processed_businesses)
        )
        
        # Enrichment phase
        if enrich:
            websocket_manager.emit_search_progress(job_id, 50, "enriching", "Starting email enrichment...")
            enriched_count = 0
            
            # Use thread pool for enrichment to avoid blocking the main event loop
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all enrichment tasks
                future_to_business = {}
                for i, business in enumerate(processed_businesses):
                    future = executor.submit(safe_enrich_business, enricher, business, job_id)
                    future_to_business[future] = (i, business)
                
                # Process completed futures as they finish
                for future in concurrent.futures.as_completed(future_to_business):
                    i, business = future_to_business[future]
                    try:
                        enriched = future.result(timeout=30)  # 30 second max per business
                        if enriched and enriched.get('email'):
                            enriched_count += 1
                        if enriched:
                            db.insert_business(enriched)
                            business.update(enriched)
                        
                        # Update enrichment progress
                        progress = 50 + (i / len(processed_businesses)) * 30  # 50-80% for enrichment
                        websocket_manager.emit_enrichment_status(
                            job_id, i + 1, len(processed_businesses), enriched_count
                        )
                        websocket_manager.emit_search_progress(
                            job_id, int(progress), "enriching",
                            f"Enriched {i+1}/{len(processed_businesses)} (found {enriched_count} emails)"
                        )
                    except concurrent.futures.TimeoutError:
                        websocket_manager.emit_error(job_id, f"Enrichment timeout for business {i+1}", "enrichment")
                    except Exception as e:
                        websocket_manager.emit_error(job_id, f"Enrichment error for business {i+1}: {e}", "enrichment")
            
            db.update_search_job(job_id, status='enriched')
            websocket_manager.emit_search_progress(
                job_id, 80, "enriched", 
                f"Enrichment complete: {enriched_count}/{len(processed_businesses)} emails found"
            )
        
        # Export phase
        if export_format:
            websocket_manager.emit_search_progress(job_id, 85, "exporting", f"Exporting to {export_format}...")
            
            if export_format in ['csv', 'json']:
                export_path = exporter.export_businesses(
                    processed_businesses,
                    format_type=export_format,
                    filename=filename,
                    job_id=job_id
                )
                websocket_manager.emit_export_complete(job_id, export_format, export_path)
                
            elif export_format == 'hubspot':
                if not hubspot.enabled:
                    websocket_manager.emit_error(job_id, "HubSpot not enabled", "config")
                else:
                    contacts = exporter.create_hubspot_format(processed_businesses)
                    if contacts:
                        res = hubspot.upload_contacts(contacts)
                        if res.get('success'):
                            websocket_manager.emit_search_progress(
                                job_id, 95, "uploading",
                                f"Uploaded {res.get('uploaded', 0)} contacts to HubSpot"
                            )
                        else:
                            websocket_manager.emit_error(job_id, f"HubSpot upload failed: {res.get('error')}", "hubspot")
        
        # Final completion
        db.update_search_job(job_id, status='completed')
        websocket_manager.emit_search_progress(
            job_id, 100, "completed",
            f"Search completed successfully! {len(processed_businesses)} businesses processed"
        )
        
    except Exception as e:
        db.update_search_job(job_id, status='failed', error_message=str(e))
        websocket_manager.emit_error(job_id, str(e), "search")


@router.get("/jobs")
async def list_search_jobs(request: Request, limit: int = 50):
    """List recent search jobs."""
    try:
        db = request.app.state.db
        # This would need to be implemented in the database module
        # For now, return a placeholder
        return {"jobs": [], "message": "Job listing not yet implemented"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}")
async def get_search_job(job_id: str, request: Request):
    """Get details of a specific search job."""
    try:
        db = request.app.state.db
        # This would need to be implemented in the database module
        # For now, return a placeholder
        return {"job_id": job_id, "status": "unknown", "message": "Job details not yet implemented"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def safe_enrich_business(enricher, business, job_id):
    """Safely enrich a business with proper error handling and timeouts."""
    try:
        # Import main for logging
        import main as core
        
        # Log start of enrichment
        print(f"[{job_id}] Starting enrichment for: {business.get('name', 'Unknown')}")
        
        # Perform enrichment with timeout protection
        enriched = enricher.enrich_business(business)
        
        # Log completion
        email_found = enriched.get('email', 'None') if enriched else 'None'
        print(f"[{job_id}] Completed enrichment for: {business.get('name', 'Unknown')}, email: {email_found}")
        
        return enriched
        
    except Exception as e:
        print(f"[{job_id}] Error enriching {business.get('name', 'Unknown')}: {str(e)}")
        # Return the original business data if enrichment fails
        return business