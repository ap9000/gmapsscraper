from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime

router = APIRouter()


class CostSummaryResponse(BaseModel):
    success: bool
    days: int
    summary: Dict[str, Any]
    report_path: Optional[str] = None


@router.get("/summary")
async def get_cost_summary(
    request: Request,
    days: int = 30,
    current_month: bool = False
):
    """Get cost summary for specified period."""
    try:
        db = request.app.state.db
        
        if current_month:
            now = datetime.now()
            days = now.day
        
        summary = db.get_cost_summary(days)
        
        return CostSummaryResponse(
            success=True,
            days=days,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-report")
async def export_cost_report(
    request: Request,
    days: int = 30,
    current_month: bool = False
):
    """Export detailed cost report to CSV."""
    try:
        exporter = request.app.state.exporter
        
        if current_month:
            now = datetime.now()
            days = now.day
        
        report_path = exporter.export_cost_report(days)
        
        return {
            "success": True,
            "days": days,
            "report_path": report_path,
            "message": f"Cost report exported for last {days} days"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/{api_name}")
async def get_api_usage(api_name: str, request: Request, days: int = 7):
    """Get usage statistics for specific API."""
    try:
        db = request.app.state.db
        
        # This would need to be implemented in the database module
        # For now, return placeholder data
        return {
            "api_name": api_name,
            "days": days,
            "total_calls": 0,
            "total_cost": 0.0,
            "daily_breakdown": [],
            "message": "API usage tracking not yet implemented"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))