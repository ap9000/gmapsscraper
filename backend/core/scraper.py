import httpx
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
try:
    from .utils import geocode_location, format_coordinates_for_scrapingdog
except ImportError:
    from utils import geocode_location, format_coordinates_for_scrapingdog

logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    def __init__(self, api_key: str, base_url: str = "https://api.scrapingdog.com/google_maps"):
        self.api_key = api_key
        self.base_url = base_url
        
        # Create httpx client with connection pooling
        self.client = httpx.Client(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # ScrapingDog costs 5 credits per request, at $0.00033 per request
        self.cost_per_request = 0.00033 * 5  # $0.00165 per request
        
        # Rate limiting
        self.requests_per_second = 10
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict[str, Any], retry_count: int = 3) -> Optional[Dict[str, Any]]:
        """Make a request to ScrapingDog API with retry logic"""
        self._rate_limit()
        
        params['api_key'] = self.api_key
        
        # Log the full request details
        logger.debug(f"Making request to: {self.base_url}")
        logger.debug(f"Request parameters: {json.dumps({k: v if k != 'api_key' else '***' for k, v in params.items()}, indent=2)}")
        
        for attempt in range(retry_count):
            try:
                logger.debug(f"Making request attempt {attempt + 1}/{retry_count}")
                start_time = time.time()
                response = self.client.get(self.base_url, params=params)
                response_time = time.time() - start_time
                
                logger.debug(f"Response received in {response_time:.2f} seconds")
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.debug(f"Response JSON keys: {list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)}")
                        logger.debug(f"Full response data: {json.dumps(response_data, indent=2)}")
                        return response_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.error(f"Raw response text: {response.text[:1000]}...")
                        return None
                elif response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = (2 ** attempt) * 2
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Request failed with status {response.status_code}")
                    logger.error(f"Response text: {response.text}")
                    if attempt == retry_count - 1:
                        return None
                    time.sleep(2 ** attempt)
                    
            except httpx.RequestError as e:
                logger.error(f"Request exception on attempt {attempt + 1}: {e}")
                if attempt == retry_count - 1:
                    return None
                time.sleep(2 ** attempt)
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP status error on attempt {attempt + 1}: {e}")
                if attempt == retry_count - 1:
                    return None
                time.sleep(2 ** attempt)
        
        return None
    
    def search(self, query: str, location: str = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search Google Maps for businesses
        
        Args:
            query: Search query (e.g., "law offices")
            location: Location filter (e.g., "San Francisco, CA")
            max_results: Maximum results to return (ScrapingDog returns ~20 per page)
        
        Returns:
            List of business data dictionaries
        """
        all_results = []
        page = 0
        coordinates = None
        
        # Calculate how many pages we need (ScrapingDog returns ~20 results per page)
        max_pages = min((max_results + 19) // 20, 6)  # Max 6 pages (offset 100) as recommended
        
        logger.info(f"Starting search: '{query}' in '{location}' (max {max_results} results)")
        
        # Try to geocode location for better targeting and pagination support
        if location:
            coords = geocode_location(location)
            if coords:
                coordinates = format_coordinates_for_scrapingdog(coords[0], coords[1])
                logger.info(f"Geocoded '{location}' to coordinates: {coordinates}")
            else:
                logger.warning(f"Could not geocode '{location}', using text-based search")
        
        while len(all_results) < max_results and page < max_pages:
            params = {
                'query': query,
                'page': page
            }
            
            # Use coordinates if available (required for pagination beyond page 0)
            # ScrapingDog uses 'll' parameter, not 'coordinates'
            if coordinates:
                params['ll'] = coordinates
            elif location:
                params['location'] = location
            
            try:
                logger.debug(f"Fetching page {page} with params: {params}")
                response_data = self._make_request(params)
                
                if not response_data:
                    logger.error(f"Failed to get data for page {page}")
                    break
                
                # Extract results from response
                results = self._parse_results(response_data)
                
                if not results:
                    logger.info(f"No more results found on page {page}")
                    break
                
                all_results.extend(results)
                logger.info(f"Page {page}: Got {len(results)} results (total: {len(all_results)})")
                
                # If we got fewer than 20 results, likely no more pages
                if len(results) < 20:
                    logger.info("Got partial page, likely no more results")
                    break
                
                page += 1
                
                # Small delay between pages
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing page {page}: {e}")
                # If coordinates failed, try without coordinates on the next attempt
                if coordinates and ("coordinates" in str(e).lower() or "ll" in str(e).lower()):
                    logger.warning("Coordinates parameter may be causing issues, falling back to location")
                    coordinates = None
                break
        
        # Trim to max_results if we got more
        final_results = all_results[:max_results]
        logger.info(f"Search completed: {len(final_results)} results for '{query}'")
        
        return final_results
    
    def _parse_results(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse ScrapingDog response into standardized business data"""
        results = []
        
        try:
            logger.debug(f"=== RESPONSE ANALYSIS ===")
            logger.debug(f"Response data type: {type(response_data)}")
            
            if isinstance(response_data, dict):
                logger.debug(f"Response keys: {list(response_data.keys())}")
                for key, value in response_data.items():
                    logger.debug(f"Key '{key}': type={type(value)}, length={len(value) if hasattr(value, '__len__') else 'N/A'}")
                    if isinstance(value, list) and len(value) > 0:
                        logger.debug(f"First item in '{key}': {json.dumps(value[0], indent=2) if isinstance(value[0], dict) else value[0]}")
            elif isinstance(response_data, list):
                logger.debug(f"Response is list with {len(response_data)} items")
                if len(response_data) > 0:
                    logger.debug(f"First item: {json.dumps(response_data[0], indent=2) if isinstance(response_data[0], dict) else response_data[0]}")
            else:
                logger.debug(f"Unexpected response type: {type(response_data)}")
                logger.debug(f"Response content: {response_data}")
            
            # ScrapingDog response structure may vary, handle different formats
            businesses = []
            businesses_key_found = None
            
            if 'results' in response_data:
                businesses = response_data['results']
                businesses_key_found = 'results'
            elif 'data' in response_data:
                businesses = response_data['data']
                businesses_key_found = 'data'
            elif isinstance(response_data, list):
                businesses = response_data
                businesses_key_found = 'root_list'
            else:
                # Look for businesses in various possible keys
                for key in ['search_results', 'places', 'listings', 'businesses', 'local_results', 'organic_results']:
                    if key in response_data:
                        businesses = response_data[key]
                        businesses_key_found = key
                        break
            
            logger.debug(f"Businesses found in key: '{businesses_key_found}'")
            logger.debug(f"Number of businesses: {len(businesses) if hasattr(businesses, '__len__') else 'N/A'}")
            
            if not businesses:
                logger.warning(f"No businesses found in response. Available keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Response is not a dict'}")
                # Save the full response for debugging
                debug_filename = f"debug_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    with open(f"./logs/{debug_filename}", 'w') as f:
                        json.dump(response_data, f, indent=2)
                    logger.debug(f"Full response saved to ./logs/{debug_filename} for debugging")
                except Exception as save_error:
                    logger.error(f"Failed to save debug response: {save_error}")
                return []
            
            for i, business in enumerate(businesses):
                try:
                    logger.debug(f"Processing business {i+1}/{len(businesses)}")
                    if isinstance(business, dict):
                        logger.debug(f"Business keys: {list(business.keys())}")
                    else:
                        logger.debug(f"Business is not a dict, type: {type(business)}")
                    
                    parsed_business = self._parse_business(business)
                    if parsed_business:
                        results.append(parsed_business)
                        logger.debug(f"Successfully parsed business: {parsed_business.get('name', 'unnamed')}")
                    else:
                        logger.warning(f"Failed to parse business {i+1}")
                except Exception as e:
                    logger.warning(f"Error parsing business {i+1}: {e}")
                    logger.debug(f"Raw business data: {json.dumps(business, indent=2) if isinstance(business, dict) else business}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing results: {e}")
            logger.error(f"Response data: {json.dumps(response_data, indent=2) if isinstance(response_data, dict) else response_data}")
        
        logger.debug(f"=== PARSING COMPLETE: {len(results)} businesses parsed ===")
        return results
    
    def _parse_business(self, business_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse individual business data from ScrapingDog format"""
        try:
            # Handle different possible field names from ScrapingDog
            name = (business_data.get('title') or 
                   business_data.get('name') or 
                   business_data.get('business_name', ''))
            
            if not name:
                return None
            
            # Extract GPS coordinates
            gps = business_data.get('gps', {})
            if isinstance(gps, str):
                try:
                    # Sometimes GPS comes as "lat,lng" string
                    lat, lng = gps.split(',')
                    latitude = float(lat)
                    longitude = float(lng)
                except:
                    latitude = longitude = None
            else:
                latitude = gps.get('latitude') or gps.get('lat')
                longitude = gps.get('longitude') or gps.get('lng')
            
            # Extract rating
            rating = business_data.get('rating')
            if rating:
                try:
                    rating = float(rating)
                except:
                    rating = None
            
            # Extract reviews count
            reviews = business_data.get('reviews')
            if reviews and isinstance(reviews, str):
                # Extract number from strings like "123 reviews"
                import re
                match = re.search(r'(\d+)', reviews)
                reviews = int(match.group(1)) if match else None
            elif reviews:
                try:
                    reviews = int(reviews)
                except:
                    reviews = None
            
            # Parse categories/types
            categories = []
            category_fields = ['type', 'category', 'categories', 'business_type']
            for field in category_fields:
                if field in business_data:
                    cat_data = business_data[field]
                    if isinstance(cat_data, list):
                        categories.extend(cat_data)
                    elif isinstance(cat_data, str) and cat_data:
                        categories.append(cat_data)
            
            # Parse hours
            hours = business_data.get('hours', {})
            if isinstance(hours, str):
                # Sometimes hours come as a string, try to parse
                hours = {'raw': hours}
            elif not isinstance(hours, dict):
                hours = {}
            
            return {
                'name': name.strip(),
                'place_id': business_data.get('place_id') or business_data.get('id'),
                'address': (business_data.get('address') or 
                           business_data.get('full_address') or 
                           business_data.get('location', '')).strip(),
                'phone': (business_data.get('phone') or 
                         business_data.get('phone_number') or 
                         business_data.get('contact', {}).get('phone', '')).strip(),
                'website': (business_data.get('website') or 
                           business_data.get('url') or 
                           business_data.get('link', '')).strip(),
                'rating': rating,
                'reviews_count': reviews,
                'categories': categories,
                'hours': hours,
                'latitude': latitude,
                'longitude': longitude,
                # Additional fields that might be useful
                'description': business_data.get('description', ''),
                'price_level': business_data.get('price_level'),
                'thumbnail': business_data.get('thumbnail'),
                'raw_data': business_data  # Keep original for debugging
            }
            
        except Exception as e:
            logger.warning(f"Error parsing business: {e}")
            return None
    
    def get_cost_per_request(self) -> float:
        """Get the cost per API request"""
        return self.cost_per_request
    
    def estimate_cost(self, max_results: int) -> float:
        """Estimate the cost for a search with given max_results"""
        # Each page request costs the same, regardless of results returned
        pages_needed = min((max_results + 19) // 20, 6)  # Max 6 pages
        return pages_needed * self.cost_per_request
    
    def close(self):
        """Close the HTTP client and cleanup resources"""
        if hasattr(self, 'client'):
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()