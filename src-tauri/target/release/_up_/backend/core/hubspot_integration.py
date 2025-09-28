import httpx
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class HubSpotIntegration:
    def __init__(self, config, db_manager):
        self.config = config
        self.db = db_manager
        
        # HubSpot configuration
        self.enabled = config.get('hubspot.enabled', False)
        self.access_token = config.get('hubspot.access_token')
        self.client_id = config.get('hubspot.client_id')
        self.client_secret = config.get('hubspot.client_secret')
        self.batch_size = config.get('hubspot.batch_size', 50)
        self.rate_limit_per_10s = config.get('hubspot.rate_limit_per_10s', 80)
        
        # API endpoints
        self.base_url = "https://api.hubapi.com"
        self.contacts_endpoint = f"{self.base_url}/crm/v3/objects/contacts"
        self.batch_endpoint = f"{self.base_url}/crm/v3/objects/contacts/batch"
        
        # Rate limiting
        self.last_batch_time = 0
        self.requests_in_window = 0
        self.window_start = time.time()
        
        # Initialize httpx client for reuse
        if self.enabled and self.access_token:
            self.client = httpx.Client(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        else:
            self.client = None
        
        if not self.enabled:
            logger.info("HubSpot integration is disabled")
        elif not self.access_token:
            logger.warning("HubSpot integration enabled but no access token provided")
            self.enabled = False
    
    def upload_contacts(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upload contacts to HubSpot in batches
        
        Args:
            contacts: List of contacts in HubSpot format
        
        Returns:
            Dictionary with upload results
        """
        if not self.enabled:
            logger.warning("HubSpot integration is not enabled")
            return {'success': False, 'error': 'HubSpot integration disabled'}
        
        if not contacts:
            logger.info("No contacts to upload to HubSpot")
            return {'success': True, 'uploaded': 0, 'failed': 0, 'batches': 0}
        
        logger.info(f"Starting HubSpot upload of {len(contacts)} contacts")
        
        # Split contacts into batches
        batches = [contacts[i:i + self.batch_size] for i in range(0, len(contacts), self.batch_size)]
        
        results = {
            'success': True,
            'uploaded': 0,
            'failed': 0,
            'batches': len(batches),
            'errors': []
        }
        
        for batch_num, batch in enumerate(batches, 1):
            try:
                logger.info(f"Uploading batch {batch_num}/{len(batches)} ({len(batch)} contacts)")
                
                # Rate limiting check
                self._rate_limit_check()
                
                batch_result = self._upload_batch(batch)
                
                if batch_result['success']:
                    results['uploaded'] += batch_result.get('created', 0)
                    logger.info(f"Batch {batch_num} uploaded successfully: {batch_result.get('created', 0)} contacts")
                else:
                    results['failed'] += len(batch)
                    results['errors'].append(f"Batch {batch_num}: {batch_result.get('error', 'Unknown error')}")
                    logger.error(f"Batch {batch_num} failed: {batch_result.get('error')}")
                
                # Log API costs (HubSpot API is free, but we track for monitoring)
                self.db.log_api_call('hubspot', 'batch-create-contacts', 0.0, batch_result['success'])
                
                # Small delay between batches
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                results['failed'] += len(batch)
                results['errors'].append(f"Batch {batch_num}: {str(e)}")
                results['success'] = False
        
        logger.info(f"HubSpot upload completed: {results['uploaded']} uploaded, {results['failed']} failed")
        return results
    
    def _upload_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upload a single batch of contacts to HubSpot"""
        if not self.client:
            return {'success': False, 'error': 'HubSpot client not initialized'}
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'inputs': batch
            }
            
            response = self.client.post(
                f"{self.batch_endpoint}/create",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 201:
                result_data = response.json()
                return {
                    'success': True,
                    'created': len(result_data.get('results', [])),
                    'response': result_data
                }
            elif response.status_code == 207:
                # Partial success - some contacts created, some failed
                result_data = response.json()
                created_count = 0
                errors = []
                
                for result in result_data.get('results', []):
                    if 'id' in result:
                        created_count += 1
                    else:
                        errors.append(result.get('error', 'Unknown error'))
                
                return {
                    'success': created_count > 0,
                    'created': created_count,
                    'errors': errors,
                    'response': result_data
                }
            else:
                error_message = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"HubSpot batch upload failed: {error_message}")
                return {
                    'success': False,
                    'error': error_message,
                    'response': response.text
                }
                
        except Exception as e:
            logger.error(f"Exception during HubSpot batch upload: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _rate_limit_check(self):
        """Ensure we don't exceed HubSpot rate limits"""
        current_time = time.time()
        
        # Reset window if 10 seconds have passed
        if current_time - self.window_start >= 10:
            self.requests_in_window = 0
            self.window_start = current_time
        
        # If we're at the limit, wait for the window to reset
        if self.requests_in_window >= self.rate_limit_per_10s:
            wait_time = 10 - (current_time - self.window_start)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                self.requests_in_window = 0
                self.window_start = time.time()
        
        self.requests_in_window += 1
    
    def create_single_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single contact in HubSpot"""
        if not self.enabled or not self.client:
            return {'success': False, 'error': 'HubSpot integration disabled'}
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = self.client.post(
                self.contacts_endpoint,
                headers=headers,
                json=contact
            )
            
            if response.status_code == 201:
                return {
                    'success': True,
                    'contact_id': response.json().get('id'),
                    'response': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'response': response.text
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Search for existing contact by email"""
        if not self.enabled or not self.client:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Use HubSpot's search API
            search_url = f"{self.base_url}/crm/v3/objects/contacts/search"
            search_payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }],
                "properties": ["email", "firstname", "lastname", "company"]
            }
            
            response = self.client.post(
                search_url,
                headers=headers,
                json=search_payload
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                return results[0] if results else None
            else:
                logger.warning(f"Error searching HubSpot contact: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception searching HubSpot contact: {e}")
            return None
    
    def update_contact(self, contact_id: str, properties: Dict[str, str]) -> Dict[str, Any]:
        """Update an existing contact in HubSpot"""
        if not self.enabled:
            return {'success': False, 'error': 'HubSpot integration disabled'}
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {'properties': properties}
            
            response = self.client.patch(
                f"{self.contacts_endpoint}/{contact_id}",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'response': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_connection(self) -> Dict[str, Any]:
        """Test HubSpot connection and credentials"""
        if not self.enabled:
            return {'success': False, 'error': 'HubSpot integration disabled'}
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Test with a simple GET request to contacts endpoint
            response = self.client.get(
                f"{self.contacts_endpoint}?limit=1",
                headers=headers
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'HubSpot connection successful',
                    'account_info': response.headers.get('X-HubSpot-RateLimit-Daily-Remaining')
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_upload_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of recent HubSpot uploads"""
        try:
            # Get HubSpot API calls from database
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_calls,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                        DATE(timestamp) as upload_date
                    FROM api_calls 
                    WHERE provider = 'hubspot' 
                        AND timestamp >= datetime('now', '-{} days')
                    GROUP BY DATE(timestamp)
                    ORDER BY upload_date DESC
                """.format(days))
                
                daily_stats = []
                for row in cursor:
                    daily_stats.append({
                        'date': row[2],
                        'total_calls': row[0],
                        'successful_calls': row[1],
                        'failed_calls': row[0] - row[1]
                    })
                
                return {
                    'success': True,
                    'daily_stats': daily_stats,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error(f"Error getting upload summary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def close(self):
        """Close the HTTP client and cleanup resources"""
        if hasattr(self, 'client') and self.client:
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()