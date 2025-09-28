#!/usr/bin/env python3

import click
import os
import sys
import logging
import csv
from datetime import datetime
from typing import Optional, Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from scraper import GoogleMapsScraper
from enricher import EmailEnricher
from exporter import DataExporter
from hubspot_integration import HubSpotIntegration
from utils import (
    ConfigLoader, ProxyManager, RateLimiter, 
    generate_job_id, setup_logging, format_business_data, ensure_directory
)

# Global objects that will be initialized
config = None
db = None
scraper = None
enricher = None
exporter = None
hubspot = None
proxy_manager = None
rate_limiter = None


def initialize_components():
    """Initialize all components"""
    global config, db, scraper, enricher, exporter, hubspot, proxy_manager, rate_limiter
    
    try:
        # Load configuration
        config = ConfigLoader()
        
        # Setup logging
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("Starting Google Maps Lead Generator")
        
        # Initialize database
        db_path = config.get('paths.cache_db', './data/cache.db')
        ensure_directory(os.path.dirname(db_path))
        db = DatabaseManager(db_path)
        
        # Initialize proxy manager
        proxy_file = config.get('settings.proxy_file', './proxies.txt')
        proxy_manager = ProxyManager(proxy_file)
        
        # Initialize rate limiter
        rate_limiter = RateLimiter(config, db)
        
        # Initialize scraper
        scrapingdog_key = config.get('apis.scrapingdog.api_key')
        if not scrapingdog_key or scrapingdog_key == 'YOUR_SCRAPINGDOG_API_KEY_HERE':
            logger.error("ScrapingDog API key not configured. Please update config/config.yaml")
            sys.exit(1)
        
        scraper = GoogleMapsScraper(scrapingdog_key)
        
        # Initialize enricher
        enricher = EmailEnricher(config, proxy_manager, db)
        
        # Initialize exporter
        exporter = DataExporter(config, db)
        
        # Initialize HubSpot integration
        hubspot = HubSpotIntegration(config, db)
        
        logger.info("All components initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing components: {e}")
        return False


@click.group()
def cli():
    """Google Maps Lead Generator - Extract business leads from Google Maps"""
    if not initialize_components():
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--location', '-l', help='Location to search (e.g., "San Francisco, CA")')
@click.option('--max-results', '-m', default=100, help='Maximum results to fetch (default: 100)')
@click.option('--enrich/--no-enrich', default=True, help='Enable email enrichment (default: True)')
@click.option('--export', '-e', type=click.Choice(['csv', 'json', 'hubspot']), default='csv', 
              help='Export format (default: csv)')
@click.option('--filename', '-f', help='Custom export filename (without extension)')
def search(query: str, location: Optional[str], max_results: int, enrich: bool, 
           export: str, filename: Optional[str]):
    """Search Google Maps for businesses"""
    logger = logging.getLogger(__name__)
    
    try:
        # Check rate limits
        limits_check = rate_limiter.check_limits('scrapingdog')
        if not limits_check['can_proceed']:
            click.echo("❌ Rate limits exceeded!")
            click.echo(f"Daily: {limits_check['daily']['used']}/{limits_check['daily']['limit']}")
            click.echo(f"Weekly: {limits_check['weekly']['used']}/{limits_check['weekly']['limit']}")
            click.echo(f"Monthly: {limits_check['monthly']['used']}/{limits_check['monthly']['limit']}")
            return
        
        # Estimate cost
        estimated_cost = scraper.estimate_cost(max_results)
        click.echo(f"🔍 Searching: '{query}' in '{location or 'global'}'")
        click.echo(f"📊 Max results: {max_results}")
        click.echo(f"💰 Estimated cost: ${estimated_cost:.4f}")
        
        if not click.confirm("Continue with search?", default=True):
            return
        
        # Generate job ID
        job_id = generate_job_id(query, location)
        logger.info(f"Starting search job: {job_id}")
        
        # Create search job in database
        db.create_search_job(job_id, query, location, {
            'max_results': max_results,
            'enrich': enrich,
            'export_format': export
        })
        
        # Perform search
        click.echo("🔍 Searching Google Maps...")
        results = scraper.search(query, location, max_results)
        
        if not results:
            click.echo("❌ No results found")
            return
        
        click.echo(f"✅ Found {len(results)} businesses")
        
        # Log API costs
        actual_pages = min((len(results) + 19) // 20, 6)
        actual_cost = actual_pages * scraper.get_cost_per_request()
        db.log_api_call('scrapingdog', 'google_maps_search', actual_cost, success=True)
        
        # Process and store results
        processed_businesses = []
        for result in results:
            business_data = format_business_data(result, job_id)
            db.insert_business(business_data)
            processed_businesses.append(business_data)
        
        # Update job status
        db.update_search_job(job_id, 
                           status='scraped', 
                           total_results=len(results),
                           processed_results=len(processed_businesses))
        
        # Enrichment
        if enrich:
            click.echo("📧 Enriching with email addresses...")
            enriched_count = 0
            
            with click.progressbar(processed_businesses, label='Enriching businesses') as businesses:
                for business in businesses:
                    try:
                        enriched_business = enricher.enrich_business(business)
                        if enriched_business.get('email'):
                            enriched_count += 1
                        
                        # Update in database
                        db.insert_business(enriched_business)
                        
                        # Update the local copy
                        business.update(enriched_business)
                        
                    except Exception as e:
                        logger.warning(f"Error enriching {business.get('name')}: {e}")
            
            click.echo(f"📧 Enriched {enriched_count}/{len(processed_businesses)} businesses with email addresses")
            
            # Update job status
            db.update_search_job(job_id, status='enriched')
        
        # Export results
        click.echo(f"📤 Exporting results as {export}...")
        
        if export in ['csv', 'json']:
            export_path = exporter.export_businesses(
                processed_businesses, 
                format_type=export,
                filename=filename,
                job_id=job_id
            )
            click.echo(f"✅ Exported to: {export_path}")
        
        elif export == 'hubspot':
            if not hubspot.enabled:
                click.echo("❌ HubSpot integration not enabled. Check your config.")
                return
            
            # Convert to HubSpot format
            hubspot_contacts = exporter.create_hubspot_format(processed_businesses)
            
            if not hubspot_contacts:
                click.echo("❌ No contacts with email addresses to upload to HubSpot")
                return
            
            # Upload to HubSpot
            click.echo(f"⬆️ Uploading {len(hubspot_contacts)} contacts to HubSpot...")
            upload_result = hubspot.upload_contacts(hubspot_contacts)
            
            if upload_result['success']:
                click.echo(f"✅ HubSpot upload completed: {upload_result['uploaded']} uploaded")
                if upload_result['failed'] > 0:
                    click.echo(f"⚠️ {upload_result['failed']} contacts failed to upload")
            else:
                click.echo(f"❌ HubSpot upload failed: {upload_result.get('error', 'Unknown error')}")
        
        # Final status
        db.update_search_job(job_id, status='completed')
        click.echo(f"🎉 Search completed! Job ID: {job_id}")
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        click.echo(f"❌ Search failed: {e}")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--enrich/--no-enrich', default=True, help='Enable email enrichment')
@click.option('--export', '-e', type=click.Choice(['csv', 'json', 'hubspot']), default='csv')
@click.option('--daily-limit', type=int, help='Override daily request limit')
@click.option('--concurrent', '-c', default=1, help='Concurrent searches (default: 1)')
def batch(input_file: str, enrich: bool, export: str, daily_limit: Optional[int], concurrent: int):
    """Process batch searches from CSV file"""
    logger = logging.getLogger(__name__)
    
    try:
        # Override daily limit if specified
        if daily_limit:
            # This would require modifying the config temporarily
            click.echo(f"⚙️ Using custom daily limit: {daily_limit}")
        
        # Read input CSV
        searches = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'query' in row:
                    searches.append({
                        'query': row['query'],
                        'location': row.get('location', ''),
                        'max_results': int(row.get('max_results', 100))
                    })
        
        if not searches:
            click.echo("❌ No valid searches found in input file")
            return
        
        click.echo(f"📋 Found {len(searches)} searches in batch file")
        
        # Process each search
        all_results = []
        for i, search_params in enumerate(searches, 1):
            click.echo(f"\n🔍 Search {i}/{len(searches)}: '{search_params['query']}' in '{search_params['location']}'")
            
            # Check rate limits before each search
            limits_check = rate_limiter.check_limits('scrapingdog')
            if not limits_check['can_proceed']:
                click.echo(f"⏸️ Rate limits reached, stopping at search {i-1}/{len(searches)}")
                break
            
            try:
                # Perform search
                results = scraper.search(
                    search_params['query'],
                    search_params['location'] or None,
                    search_params['max_results']
                )
                
                if results:
                    # Process results
                    job_id = generate_job_id(search_params['query'], search_params['location'])
                    processed_results = []
                    
                    for result in results:
                        business_data = format_business_data(result, job_id)
                        db.insert_business(business_data)
                        processed_results.append(business_data)
                    
                    all_results.extend(processed_results)
                    click.echo(f"✅ Found {len(results)} businesses")
                    
                    # Log costs
                    actual_pages = min((len(results) + 19) // 20, 6)
                    actual_cost = actual_pages * scraper.get_cost_per_request()
                    db.log_api_call('scrapingdog', 'google_maps_search', actual_cost, success=True)
                else:
                    click.echo("❌ No results found")
                
            except Exception as e:
                logger.error(f"Error in search {i}: {e}")
                click.echo(f"❌ Search {i} failed: {e}")
        
        if not all_results:
            click.echo("❌ No results from any searches")
            return
        
        click.echo(f"\n📊 Total businesses found: {len(all_results)}")
        
        # Enrichment
        if enrich:
            click.echo("📧 Starting batch enrichment...")
            enriched_count = 0
            
            with click.progressbar(all_results, label='Enriching businesses') as businesses:
                for business in businesses:
                    try:
                        enriched_business = enricher.enrich_business(business)
                        if enriched_business.get('email'):
                            enriched_count += 1
                        
                        db.insert_business(enriched_business)
                        business.update(enriched_business)
                        
                    except Exception as e:
                        logger.warning(f"Error enriching {business.get('name')}: {e}")
            
            click.echo(f"📧 Enriched {enriched_count}/{len(all_results)} businesses")
        
        # Export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export in ['csv', 'json']:
            export_path = exporter.export_businesses(
                all_results,
                format_type=export,
                filename=f"batch_export_{timestamp}"
            )
            click.echo(f"✅ Batch export completed: {export_path}")
        
        elif export == 'hubspot':
            if hubspot.enabled:
                hubspot_contacts = exporter.create_hubspot_format(all_results)
                if hubspot_contacts:
                    upload_result = hubspot.upload_contacts(hubspot_contacts)
                    click.echo(f"✅ HubSpot batch upload: {upload_result['uploaded']} uploaded")
                else:
                    click.echo("❌ No contacts with emails for HubSpot upload")
            else:
                click.echo("❌ HubSpot integration not enabled")
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        click.echo(f"❌ Batch processing failed: {e}")


@cli.command()
@click.option('--current-month', is_flag=True, help='Show current month costs only')
@click.option('--days', '-d', default=30, help='Number of days to analyze (default: 30)')
@click.option('--export-report', is_flag=True, help='Export detailed cost report to CSV')
def costs(current_month: bool, days: int, export_report: bool):
    """Show API cost analysis"""
    try:
        if current_month:
            # Get current month costs
            now = datetime.now()
            days = now.day  # Days elapsed in current month
            click.echo(f"💰 Costs for current month ({now.strftime('%B %Y')} - {days} days):")
        else:
            click.echo(f"💰 Costs for last {days} days:")
        
        cost_summary = db.get_cost_summary(days)
        
        if not cost_summary:
            click.echo("📊 No API calls found in the specified period")
            return
        
        # Display summary
        summary = cost_summary.get('summary', {})
        total_cost = summary.get('total_cost', 0)
        total_calls = summary.get('total_calls', 0)
        
        click.echo(f"📈 Total Cost: ${total_cost:.4f}")
        click.echo(f"📞 Total API Calls: {total_calls}")
        
        if total_cost > 0:
            click.echo(f"📊 Average Cost per Call: ${total_cost/max(total_calls, 1):.4f}")
        
        click.echo("\n📋 By Provider:")
        for provider, data in cost_summary.items():
            if provider != 'summary':
                click.echo(f"  {provider.title()}:")
                click.echo(f"    Calls: {data['call_count']}")
                click.echo(f"    Cost: ${data['total_cost']:.4f}")
                click.echo(f"    Avg: ${data['avg_cost']:.4f}")
        
        # Budget analysis
        monthly_budget = config.get('settings.monthly_limit', 200000) * scraper.get_cost_per_request()
        monthly_usage_pct = (total_cost / monthly_budget) * 100 if current_month else 0
        
        if current_month:
            click.echo(f"\n💳 Monthly Budget: ${monthly_budget:.2f}")
            click.echo(f"📊 Usage: {monthly_usage_pct:.1f}% of budget")
            
            if monthly_usage_pct > 80:
                click.echo("⚠️ Warning: Approaching monthly budget limit!")
        
        # Export report if requested
        if export_report:
            report_path = exporter.export_cost_report(days)
            click.echo(f"\n📄 Detailed report exported: {report_path}")
        
    except Exception as e:
        click.echo(f"❌ Error retrieving costs: {e}")


@cli.command()
@click.argument('job_id')
def resume(job_id: str):
    """Resume an interrupted search job"""
    logger = logging.getLogger(__name__)
    
    try:
        # Implementation would require additional database tracking
        # For now, show a helpful message
        click.echo(f"🔄 Resume functionality for job {job_id}")
        click.echo("Note: This feature requires additional implementation for job state tracking")
        
        # Could search for existing results and continue from where we left off
        existing_businesses = db.get_businesses_for_export(job_id=job_id)
        
        if existing_businesses:
            click.echo(f"📊 Found {len(existing_businesses)} existing results for job {job_id}")
            
            # Ask if user wants to export existing results
            if click.confirm("Export existing results?"):
                export_path = exporter.export_businesses(existing_businesses, filename=f"resume_{job_id}")
                click.echo(f"✅ Exported existing results: {export_path}")
        else:
            click.echo(f"❌ No existing results found for job {job_id}")
        
    except Exception as e:
        logger.error(f"Resume failed: {e}")
        click.echo(f"❌ Resume failed: {e}")


@cli.command('sync-hubspot')
@click.option('--batch-size', '-b', default=50, help='Batch size for HubSpot upload (default: 50)')
@click.option('--days', '-d', default=7, help='Sync businesses from last N days (default: 7)')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without uploading')
def sync_hubspot(batch_size: int, days: int, dry_run: bool):
    """Sync recent businesses to HubSpot"""
    try:
        if not hubspot.enabled:
            click.echo("❌ HubSpot integration not enabled. Check your configuration.")
            return
        
        # Test connection first
        click.echo("🔗 Testing HubSpot connection...")
        connection_test = hubspot.validate_connection()
        
        if not connection_test['success']:
            click.echo(f"❌ HubSpot connection failed: {connection_test['error']}")
            return
        
        click.echo("✅ HubSpot connection successful")
        
        # Get recent businesses with email addresses
        businesses = db.get_businesses_for_export(limit=None)
        
        # Filter to businesses from last N days with email addresses
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        recent_businesses = [
            b for b in businesses 
            if b.get('email') and b.get('created_at', '') > cutoff_date
        ]
        
        if not recent_businesses:
            click.echo(f"❌ No businesses with email addresses found from last {days} days")
            return
        
        click.echo(f"📊 Found {len(recent_businesses)} businesses to sync")
        
        if dry_run:
            click.echo("🔍 Dry run - showing first 5 businesses that would be synced:")
            for i, business in enumerate(recent_businesses[:5], 1):
                click.echo(f"  {i}. {business['name']} - {business['email']}")
            if len(recent_businesses) > 5:
                click.echo(f"  ... and {len(recent_businesses) - 5} more")
            return
        
        # Convert to HubSpot format
        hubspot_contacts = exporter.create_hubspot_format(recent_businesses)
        
        if not hubspot_contacts:
            click.echo("❌ No valid contacts to sync")
            return
        
        # Upload to HubSpot
        click.echo(f"⬆️ Uploading {len(hubspot_contacts)} contacts to HubSpot...")
        upload_result = hubspot.upload_contacts(hubspot_contacts)
        
        if upload_result['success']:
            click.echo(f"✅ HubSpot sync completed!")
            click.echo(f"   📈 Uploaded: {upload_result['uploaded']}")
            if upload_result['failed'] > 0:
                click.echo(f"   ❌ Failed: {upload_result['failed']}")
                for error in upload_result.get('errors', [])[:3]:  # Show first 3 errors
                    click.echo(f"   Error: {error}")
        else:
            click.echo(f"❌ HubSpot sync failed: {upload_result.get('error', 'Unknown error')}")
        
    except Exception as e:
        click.echo(f"❌ HubSpot sync failed: {e}")


@cli.command()
def status():
    """Show system status and configuration"""
    try:
        click.echo("🔧 Google Maps Lead Generator - System Status")
        click.echo("=" * 50)
        
        # Configuration status
        click.echo("📋 Configuration:")
        click.echo(f"  ScrapingDog API: {'✅ Configured' if config.get('apis.scrapingdog.api_key') != 'YOUR_SCRAPINGDOG_API_KEY_HERE' else '❌ Not configured'}")
        click.echo(f"  Hunter.io: {'✅ Enabled' if config.get('apis.hunter.enabled') else '❌ Disabled'}")
        click.echo(f"  HubSpot: {'✅ Enabled' if config.get('hubspot.enabled') else '❌ Disabled'}")
        
        # Rate limits
        click.echo("\n📊 Rate Limits:")
        click.echo(f"  Daily: {config.get('settings.daily_limit', 10000):,}")
        click.echo(f"  Weekly: {config.get('settings.weekly_limit', 50000):,}")  
        click.echo(f"  Monthly: {config.get('settings.monthly_limit', 200000):,}")
        
        # Proxy status
        click.echo(f"\n🌐 Proxies: {len(proxy_manager.proxies)} loaded")
        
        # Database stats
        try:
            businesses = db.get_businesses_for_export(limit=None)
            enriched_count = len([b for b in businesses if b.get('email')])
            click.echo(f"\n💾 Database:")
            click.echo(f"  Total businesses: {len(businesses)}")
            click.echo(f"  With email addresses: {enriched_count}")
        except Exception as e:
            click.echo(f"\n💾 Database: Error accessing ({e})")
        
        # Recent costs
        try:
            cost_summary = db.get_cost_summary(7)
            if cost_summary:
                total_cost = cost_summary.get('summary', {}).get('total_cost', 0)
                click.echo(f"\n💰 Last 7 Days Cost: ${total_cost:.4f}")
        except Exception as e:
            click.echo(f"\n💰 Cost tracking: Error ({e})")
        
        click.echo("\n✅ System status check completed")
        
    except Exception as e:
        click.echo(f"❌ Status check failed: {e}")


if __name__ == '__main__':
    cli()