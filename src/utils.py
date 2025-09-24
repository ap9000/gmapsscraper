import yaml
import os
import logging
import hashlib
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            if not os.path.exists(self.config_path):
                example_path = "./config/config.example.yaml"
                if os.path.exists(example_path):
                    logger.warning(f"Config file not found. Please copy {example_path} to {self.config_path} and update with your API keys")
                    # Load example config as fallback
                    with open(example_path, 'r') as f:
                        return yaml.safe_load(f)
                else:
                    raise FileNotFoundError(f"Neither {self.config_path} nor {example_path} found")
            
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info("Configuration loaded successfully")
                return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'apis.scrapingdog.api_key')"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default


class ProxyManager:
    def __init__(self, proxy_file: str = "./proxies.txt"):
        self.proxy_file = proxy_file
        self.proxies = self.load_proxies()
        self.current_index = 0
    
    def load_proxies(self) -> List[Dict[str, str]]:
        """Load proxies from file in format: ip:port:username:password"""
        proxies = []
        try:
            if not os.path.exists(self.proxy_file):
                logger.warning(f"Proxy file {self.proxy_file} not found")
                return proxies
            
            with open(self.proxy_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            parts = line.split(':')
                            if len(parts) == 4:
                                proxy = {
                                    'ip': parts[0],
                                    'port': parts[1],
                                    'username': parts[2],
                                    'password': parts[3],
                                    'url': f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                                }
                                proxies.append(proxy)
                            else:
                                logger.warning(f"Invalid proxy format on line {line_num}: {line}")
                        except Exception as e:
                            logger.warning(f"Error parsing proxy on line {line_num}: {e}")
            
            logger.info(f"Loaded {len(proxies)} proxies from {self.proxy_file}")
            return proxies
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
            return []
    
    def get_proxy(self, rotate: bool = True) -> Optional[Dict[str, str]]:
        """Get a proxy (with optional rotation)"""
        if not self.proxies:
            return None
        
        if rotate:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
        else:
            proxy = random.choice(self.proxies)
        
        return proxy
    
    def get_requests_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Get proxy in requests library format"""
        proxy = self.get_proxy()
        if proxy:
            return {
                'http': proxy['url'],
                'https': proxy['url']
            }
        return None


class RateLimiter:
    def __init__(self, config: ConfigLoader, db_manager):
        self.config = config
        self.db = db_manager
    
    def check_limits(self, provider: str) -> Dict[str, Any]:
        """Check if we're within rate limits"""
        daily_limit = self.config.get('settings.daily_limit', 10000)
        weekly_limit = self.config.get('settings.weekly_limit', 50000)
        monthly_limit = self.config.get('settings.monthly_limit', 200000)
        
        # Get usage from database
        daily_usage = self._get_usage(provider, 1)
        weekly_usage = self._get_usage(provider, 7)
        monthly_usage = self._get_usage(provider, 30)
        
        return {
            'can_proceed': (
                daily_usage < daily_limit and
                weekly_usage < weekly_limit and
                monthly_usage < monthly_limit
            ),
            'daily': {'used': daily_usage, 'limit': daily_limit, 'remaining': daily_limit - daily_usage},
            'weekly': {'used': weekly_usage, 'limit': weekly_limit, 'remaining': weekly_limit - weekly_usage},
            'monthly': {'used': monthly_usage, 'limit': monthly_limit, 'remaining': monthly_limit - monthly_usage}
        }
    
    def _get_usage(self, provider: str, days: int) -> int:
        """Get API usage count for last N days"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM api_calls 
                    WHERE provider = ? AND timestamp >= datetime('now', '-{} days')
                """.format(days), (provider,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return 0


def generate_job_id(query: str, location: str = None) -> str:
    """Generate a unique job ID based on query and location"""
    content = f"{query}_{location or 'global'}_{datetime.now().isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def ensure_directory(path: str):
    """Ensure directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)


def setup_logging(config: ConfigLoader):
    """Setup logging configuration"""
    log_level = getattr(logging, config.get('logging.level', 'INFO').upper())
    log_file = config.get('logging.file', './logs/gmaps_scraper.log')
    
    # Ensure logs directory exists
    ensure_directory(os.path.dirname(log_file))
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger.info("Logging configured successfully")


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def clean_phone_number(phone: str) -> Optional[str]:
    """Clean and format phone number"""
    if not phone:
        return None
    
    # Remove non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # Basic US phone number formatting
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return phone  # Return original if we can't format it


@lru_cache(maxsize=256)
def geocode_location(location: str) -> Optional[Tuple[float, float]]:
    """
    Convert a location string to coordinates for ScrapingDog pagination.
    Strategy (simple & robust):
    1) Quick fallback map for common cities.
    2) Nominatim (OpenStreetMap) via HTTPX (no system cert issues), 1 result.
    3) As a last resort, try geopy.Nominatim (if installed).

    Returns (lat, lng) or None.
    """
    if not location or not location.strip():
        return None
    
    # Fallback coordinates for major cities
    CITY_COORDINATES = {
        'san francisco': (37.7749, -122.4194),
        'san francisco, ca': (37.7749, -122.4194),
        'san francisco, california': (37.7749, -122.4194),
        'new york': (40.7128, -74.0060),
        'new york, ny': (40.7128, -74.0060),
        'new york city': (40.7128, -74.0060),
        'los angeles': (34.0522, -118.2437),
        'los angeles, ca': (34.0522, -118.2437),
        'chicago': (41.8781, -87.6298),
        'chicago, il': (41.8781, -87.6298),
        'houston': (29.7604, -95.3698),
        'houston, tx': (29.7604, -95.3698),
        'phoenix': (33.4484, -112.0740),
        'phoenix, az': (33.4484, -112.0740),
        'philadelphia': (39.9526, -75.1652),
        'philadelphia, pa': (39.9526, -75.1652),
        'miami': (25.7617, -80.1918),
        'miami, fl': (25.7617, -80.1918),
        'denver': (39.7392, -104.9903),
        'denver, co': (39.7392, -104.9903),
        'seattle': (47.6062, -122.3321),
        'seattle, wa': (47.6062, -122.3321),
        'austin': (30.2672, -97.7431),
        'austin, tx': (30.2672, -97.7431),
        'dallas': (32.7767, -96.7970),
        'dallas, tx': (32.7767, -96.7970),
        'san diego': (32.7157, -117.1611),
        'san diego, ca': (32.7157, -117.1611),
        'san jose': (37.3382, -121.8863),
        'san jose, ca': (37.3382, -121.8863),
    }
    
    # Check fallback coordinates first
    location_key = location.lower().strip()
    if location_key in CITY_COORDINATES:
        coords = CITY_COORDINATES[location_key]
        logger.debug(f"Using fallback coordinates for '{location}': {coords}")
        return coords
    
    # Try Nominatim via HTTPX (usually more robust on macOS)
    try:
        import httpx
        headers = {
            'User-Agent': 'gmaps-scraper/1.0 (contact: local)'
        }
        params = {'q': location, 'format': 'json', 'limit': 1}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    lat = float(data[0]['lat'])
                    lng = float(data[0]['lon'])
                    logger.debug(f"Geocoded '{location}' via HTTPX to: {lat}, {lng}")
                    return (lat, lng)
            logger.debug(f"HTTPX geocoding failed with status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.debug(f"HTTPX geocoding error for '{location}': {e}")

    # Try geopy if available
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
        geolocator = Nominatim(user_agent="gmaps_scraper_lead_generator")
        geocoded_location = geolocator.geocode(location, timeout=10)
        if geocoded_location:
            lat = geocoded_location.latitude
            lng = geocoded_location.longitude
            logger.debug(f"Geocoded '{location}' via geopy to: {lat}, {lng}")
            return (lat, lng)
    except Exception as e:
        logger.debug(f"geopy geocoding error for '{location}': {e}")

    logger.warning(f"Could not geocode location: {location}")
    return None


def format_coordinates_for_scrapingdog(lat: float, lng: float, zoom: int = 12) -> str:
    """
    Format coordinates for ScrapingDog API in the required format: @lat,lng,zoom
    
    Args:
        lat: Latitude
        lng: Longitude  
        zoom: Zoom level (default 12 for city-level search)
        
    Returns:
        Formatted coordinate string like "@37.7749,-122.4194,12z"
    """
    return f"@{lat},{lng},{zoom}z"


def format_business_data(raw_data: Dict[str, Any], source_search: str = None) -> Dict[str, Any]:
    """Format raw business data into our standard format"""
    return {
        'id': raw_data.get('place_id') or generate_job_id(raw_data.get('name', ''), raw_data.get('address', '')),
        'place_id': raw_data.get('place_id'),
        'name': raw_data.get('name', '').strip(),
        'address': raw_data.get('address', '').strip(),
        'phone': clean_phone_number(raw_data.get('phone')),
        'website': raw_data.get('website', '').strip(),
        'email': None,  # Will be filled by enrichment
        'contact_name': None,  # Will be filled by enrichment
        'rating': raw_data.get('rating'),
        'reviews_count': raw_data.get('reviews_count'),
        'categories': raw_data.get('categories', []),
        'hours': raw_data.get('hours', {}),
        'latitude': raw_data.get('latitude'),
        'longitude': raw_data.get('longitude'),
        'enriched_at': None,
        'confidence_score': 0.0,
        'source_search': source_search
    }
