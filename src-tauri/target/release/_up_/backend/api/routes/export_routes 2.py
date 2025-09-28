from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
import os

router = APIRouter()


class ExportRequest(BaseModel):
    job_id: Optional[str] = Field(None, description="Export specific job results")
    format_type: str = Field(..., description="Export format: csv, json, or hubspot")
    filename: Optional[str] = Field(None, description="Custom filename")
    days: Optional[int] = Field(None, description="Export results from last N days")


class ExportResponse(BaseModel):
    success: bool
    message: str
    file_path: Optional[str] = None
    download_url: Optional[str] = None


@router.post("/businesses", response_model=ExportResponse)
async def export_businesses(request_data: ExportRequest, request: Request):
    """Export businesses to specified format."""
    try:
        db = request.app.state.db
        exporter = request.app.state.exporter
        
        # Get businesses to export
        if request_data.job_id:
            # Export specific job results
            businesses = db.get_businesses_by_job_id(request_data.job_id) if hasattr(db, 'get_businesses_by_job_id') else []
        elif request_data.days:
            # Export recent results
            businesses = db.get_recent_businesses(request_data.days) if hasattr(db, 'get_recent_businesses') else []
        else:
            # Export all businesses
            businesses = db.get_businesses_for_export(limit=None)
        
        if not businesses:
            return ExportResponse(
                success=False,
                message="No businesses found to export"
            )
        
        if request_data.format_type in ['csv', 'json']:
            file_path = exporter.export_businesses(
                businesses,
                format_type=request_data.format_type,
                filename=request_data.filename,
                job_id=request_data.job_id
            )
            
            return ExportResponse(
                success=True,
                message=f"Exported {len(businesses)} businesses to {request_data.format_type.upper()}",
                file_path=file_path,
                download_url=f"/api/export/download/{os.path.basename(file_path)}"
            )
            
        elif request_data.format_type == 'hubspot':
            hubspot = request.app.state.hubspot
            if not hubspot.enabled:
                raise HTTPException(status_code=400, detail="HubSpot integration not enabled")
            
            contacts = exporter.create_hubspot_format(businesses)
            if not contacts:
                return ExportResponse(
                    success=False,
                    message="No valid contacts to upload to HubSpot"
                )
            
            result = hubspot.upload_contacts(contacts)
            if result.get('success'):
                return ExportResponse(
                    success=True,
                    message=f"Successfully uploaded {result.get('uploaded', 0)} contacts to HubSpot"
                )
            else:
                raise HTTPException(status_code=500, detail=f"HubSpot upload failed: {result.get('error')}")
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format_type. Must be 'csv', 'json', or 'hubspot'")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_export_file(filename: str):
    """Download exported file."""
    try:
        # Look for file in data/exports directory
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'exports')
        file_path = os.path.join(export_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_export_files():
    """List available export files."""
    try:
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'exports')
        
        if not os.path.exists(export_dir):
            return {"files": []}
        
        files = []
        for filename in os.listdir(export_dir):
            file_path = os.path.join(export_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "download_url": f"/api/export/download/{filename}"
                })
        
        # Sort by creation time, newest first
        files.sort(key=lambda x: x['created'], reverse=True)
        
        return {"files": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))