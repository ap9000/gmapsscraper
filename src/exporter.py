import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DataExporter:
    def __init__(self, config, db_manager):
        self.config = config
        self.db = db_manager
        self.exports_dir = config.get('paths.exports_dir', './data/exports')
        self._ensure_exports_dir()
    
    def _ensure_exports_dir(self):
        """Ensure exports directory exists"""
        os.makedirs(self.exports_dir, exist_ok=True)
    
    def export_businesses(self, businesses: List[Dict[str, Any]], 
                         format_type: str = 'csv',
                         filename: Optional[str] = None,
                         job_id: Optional[str] = None) -> str:
        """
        Export businesses to CSV or JSON
        
        Args:
            businesses: List of business dictionaries
            format_type: 'csv' or 'json'
            filename: Custom filename (optional)
            job_id: Job ID for naming (optional)
        
        Returns:
            Path to exported file
        """
        if not businesses:
            logger.warning("No businesses to export")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not filename:
            if job_id:
                filename = f"gmaps_leads_{job_id}_{timestamp}"
            else:
                filename = f"gmaps_leads_{timestamp}"
        
        if format_type.lower() == 'csv':
            return self._export_csv(businesses, filename)
        elif format_type.lower() == 'json':
            return self._export_json(businesses, filename)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_csv(self, businesses: List[Dict[str, Any]], filename: str) -> str:
        """Export businesses to CSV format"""
        filepath = os.path.join(self.exports_dir, f"{filename}.csv")
        
        try:
            # Define CSV columns in logical order
            csv_columns = [
                'name', 'email', 'contact_name', 'phone', 'website',
                'address', 'rating', 'reviews_count', 'categories',
                'confidence_score', 'latitude', 'longitude',
                'hours', 'enriched_at', 'source_search', 'place_id'
            ]
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                
                for business in businesses:
                    # Prepare row data
                    row = {}
                    for col in csv_columns:
                        value = business.get(col, '')
                        
                        # Handle special formatting
                        if col == 'categories' and isinstance(value, list):
                            row[col] = ', '.join(value) if value else ''
                        elif col == 'hours' and isinstance(value, dict):
                            row[col] = json.dumps(value) if value else ''
                        elif col == 'rating' and value:
                            row[col] = f"{value:.1f}"
                        elif col == 'confidence_score' and value:
                            row[col] = f"{value:.2f}"
                        else:
                            row[col] = str(value) if value is not None else ''
                    
                    writer.writerow(row)
            
            logger.info(f"Exported {len(businesses)} businesses to CSV: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            raise
    
    def _export_json(self, businesses: List[Dict[str, Any]], filename: str) -> str:
        """Export businesses to JSON format"""
        filepath = os.path.join(self.exports_dir, f"{filename}.json")
        
        try:
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'total_businesses': len(businesses),
                    'format': 'json'
                },
                'businesses': businesses
            }
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported {len(businesses)} businesses to JSON: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            raise
    
    def create_hubspot_format(self, businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert businesses to HubSpot contact format
        
        Returns:
            List of contacts in HubSpot format
        """
        hubspot_contacts = []
        
        for business in businesses:
            # Map to HubSpot standard properties
            contact = {
                'properties': {
                    'email': business.get('email', ''),
                    'company': business.get('name', ''),
                    'phone': business.get('phone', ''),
                    'website': business.get('website', ''),
                    'address': business.get('address', ''),
                    'city': self._extract_city(business.get('address', '')),
                    'state': self._extract_state(business.get('address', '')),
                    'zip': self._extract_zip(business.get('address', '')),
                }
            }
            
            # Add contact name if available
            contact_name = business.get('contact_name', '')
            if contact_name:
                name_parts = contact_name.split(' ', 1)
                contact['properties']['firstname'] = name_parts[0]
                if len(name_parts) > 1:
                    contact['properties']['lastname'] = name_parts[1]
            
            # Add custom properties
            contact['properties'].update({
                'hs_lead_status': 'NEW',
                'leadtype': 'Google Maps Lead',
                'lead_source': 'Google Maps Scraper',
                'google_rating': str(business.get('rating', '')),
                'google_reviews_count': str(business.get('reviews_count', '')),
                'business_categories': ', '.join(business.get('categories', [])),
                'confidence_score': str(business.get('confidence_score', '')),
                'google_place_id': business.get('place_id', ''),
                'enriched_date': business.get('enriched_at', ''),
                'source_search_query': business.get('source_search', '')
            })
            
            # Remove empty properties
            contact['properties'] = {k: v for k, v in contact['properties'].items() if v}
            
            # Only add contacts with email addresses for HubSpot
            if contact['properties'].get('email'):
                hubspot_contacts.append(contact)
        
        logger.info(f"Prepared {len(hubspot_contacts)} contacts for HubSpot import")
        return hubspot_contacts
    
    def _extract_city(self, address: str) -> str:
        """Extract city from address string"""
        if not address:
            return ""
        
        # Simple extraction - assumes "City, State ZIP" format
        try:
            parts = address.split(',')
            if len(parts) >= 2:
                # Get the part before the last comma (state/zip)
                city_part = parts[-2].strip()
                # Remove any leading street information
                city_words = city_part.split()
                if len(city_words) > 0:
                    return city_words[-1] if len(city_words) == 1 else ' '.join(city_words[-2:])
        except:
            pass
        
        return ""
    
    def _extract_state(self, address: str) -> str:
        """Extract state from address string"""
        if not address:
            return ""
        
        try:
            # Look for 2-letter state codes
            import re
            state_match = re.search(r'\b([A-Z]{2})\b', address)
            if state_match:
                return state_match.group(1)
        except:
            pass
        
        return ""
    
    def _extract_zip(self, address: str) -> str:
        """Extract ZIP code from address string"""
        if not address:
            return ""
        
        try:
            # Look for ZIP codes (5 digits, optionally followed by -4 digits)
            import re
            zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
            if zip_match:
                return zip_match.group(1)
        except:
            pass
        
        return ""
    
    def export_cost_report(self, days: int = 30) -> str:
        """Export cost analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cost_report_{days}days_{timestamp}.csv"
        filepath = os.path.join(self.exports_dir, filename)
        
        try:
            cost_data = self.db.get_cost_summary(days)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(['Cost Report - Last {} Days'.format(days)])
                writer.writerow(['Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([])  # Empty row
                
                # Write summary
                summary = cost_data.get('summary', {})
                writer.writerow(['Summary'])
                writer.writerow(['Total Cost:', f"${summary.get('total_cost', 0):.4f}"])
                writer.writerow(['Total API Calls:', summary.get('total_calls', 0)])
                writer.writerow(['Period:', f"{days} days"])
                writer.writerow([])  # Empty row
                
                # Write by provider
                writer.writerow(['Provider', 'API Calls', 'Total Cost', 'Average Cost'])
                for provider, data in cost_data.items():
                    if provider != 'summary':
                        writer.writerow([
                            provider,
                            data.get('call_count', 0),
                            f"${data.get('total_cost', 0):.4f}",
                            f"${data.get('avg_cost', 0):.4f}"
                        ])
            
            logger.info(f"Exported cost report: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting cost report: {e}")
            raise