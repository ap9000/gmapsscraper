from __future__ import annotations

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/config")
async def get_config_status(request: Request):
    """Get configuration status."""
    try:
        config = request.app.state.config
        
        status = {
            "scrapingdog": {
                "configured": bool(
                    config.get('apis.scrapingdog.api_key') 
                    and config.get('apis.scrapingdog.api_key') not in (None, '', 'YOUR_SCRAPINGDOG_API_KEY_HERE')
                ),
                "requests_per_second": config.get('apis.scrapingdog.requests_per_second', 10)
            },
            "hunter": {
                "configured": bool(config.get('apis.hunter.api_key')),
                "enabled": bool(config.get('apis.hunter.enabled', False))
            },
            "hubspot": {
                "configured": bool(config.get('hubspot.access_token')),
                "enabled": bool(config.get('hubspot.enabled', False)),
                "batch_size": config.get('hubspot.batch_size', 50)
            },
            "enrichment": {
                "use_scrapling": config.get('enrichment.use_scrapling', True),
                "enable_website_scraping": config.get('enrichment.enable_website_scraping', True),
                "enable_hunter": config.get('enrichment.enable_hunter', False),
                "enable_pattern_generation": config.get('enrichment.enable_pattern_generation', True),
                "email_confidence_threshold": config.get('enrichment.email_confidence_threshold', 0.7)
            }
        }
        
        return {
            "success": True,
            "config": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limits")
async def get_rate_limits(request: Request):
    """Get rate limit configuration and current usage."""
    try:
        config = request.app.state.config
        rate_limiter = request.app.state.rate_limiter
        
        limits = {
            "daily_limit": config.get('settings.daily_limit', 10000),
            "weekly_limit": config.get('settings.weekly_limit', 50000),
            "monthly_limit": config.get('settings.monthly_limit', 200000)
        }
        
        # Get current usage from rate limiter
        current_usage = rate_limiter.check_limits('scrapingdog')
        
        return {
            "success": True,
            "limits": limits,
            "current_usage": current_usage
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database")
async def get_database_stats(request: Request):
    """Get database statistics."""
    try:
        db = request.app.state.db
        
        # Get business statistics
        businesses = db.get_businesses_for_export(limit=None)
        total_businesses = len(businesses) if businesses else 0
        enriched_count = len([b for b in businesses if b.get('email')]) if businesses else 0
        
        stats = {
            "total_businesses": total_businesses,
            "with_email_addresses": enriched_count,
            "enrichment_rate": (enriched_count / total_businesses * 100) if total_businesses > 0 else 0
        }
        
        return {
            "success": True,
            "database": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system")
async def get_system_status(request: Request):
    """Get overall system status."""
    try:
        # Get proxy manager status
        proxy_manager = request.app.state.proxy_manager
        proxy_count = len(proxy_manager.proxies) if hasattr(proxy_manager, 'proxies') else 0
        
        # Basic system info
        import psutil
        import platform
        
        system_info = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        status = {
            "proxy_count": proxy_count,
            "system": system_info,
            "uptime": "Not implemented",  # Would need to track app start time
            "version": "2.0.0"
        }
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        # If psutil is not available, return basic info
        status = {
            "proxy_count": 0,
            "system": {
                "platform": "unknown",
                "python_version": "unknown"
            },
            "version": "2.0.0"
        }
        
        return {
            "success": True,
            "status": status,
            "warning": "System monitoring not fully available"
        }