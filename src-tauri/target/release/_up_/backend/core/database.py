import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = "./data/cache.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id TEXT PRIMARY KEY,
                    place_id TEXT UNIQUE,
                    name TEXT,
                    address TEXT,
                    phone TEXT,
                    website TEXT,
                    email TEXT,
                    contact_name TEXT,
                    rating REAL,
                    reviews_count INTEGER,
                    categories TEXT,
                    hours TEXT,
                    latitude REAL,
                    longitude REAL,
                    enriched_at TIMESTAMP,
                    confidence_score REAL,
                    source_search TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    cost REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                );
                
                CREATE TABLE IF NOT EXISTS search_jobs (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    location TEXT,
                    status TEXT DEFAULT 'pending',
                    total_results INTEGER DEFAULT 0,
                    processed_results INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    config TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_businesses_place_id ON businesses(place_id);
                CREATE INDEX IF NOT EXISTS idx_api_calls_provider ON api_calls(provider);
                CREATE INDEX IF NOT EXISTS idx_api_calls_timestamp ON api_calls(timestamp);
                CREATE INDEX IF NOT EXISTS idx_search_jobs_status ON search_jobs(status);
            """)
            logger.info("Database initialized successfully")
    
    def insert_business(self, business_data: Dict[str, Any]) -> bool:
        """Insert or update a business record"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Convert lists/dicts to JSON strings
                categories = json.dumps(business_data.get('categories', []))
                hours = json.dumps(business_data.get('hours', {}))
                
                conn.execute("""
                    INSERT OR REPLACE INTO businesses (
                        id, place_id, name, address, phone, website, email,
                        contact_name, rating, reviews_count, categories, hours,
                        latitude, longitude, enriched_at, confidence_score, source_search
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    business_data.get('id'),
                    business_data.get('place_id'),
                    business_data.get('name'),
                    business_data.get('address'),
                    business_data.get('phone'),
                    business_data.get('website'),
                    business_data.get('email'),
                    business_data.get('contact_name'),
                    business_data.get('rating'),
                    business_data.get('reviews_count'),
                    categories,
                    hours,
                    business_data.get('latitude'),
                    business_data.get('longitude'),
                    business_data.get('enriched_at'),
                    business_data.get('confidence_score', 0.0),
                    business_data.get('source_search')
                ))
                return True
        except Exception as e:
            logger.error(f"Error inserting business: {e}")
            return False
    
    def get_business_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get a business by its place_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM businesses WHERE place_id = ?", (place_id,)
                )
                row = cursor.fetchone()
                if row:
                    business = dict(row)
                    # Convert JSON strings back to objects
                    business['categories'] = json.loads(business.get('categories') or '[]')
                    business['hours'] = json.loads(business.get('hours') or '{}')
                    return business
                return None
        except Exception as e:
            logger.error(f"Error getting business: {e}")
            return None
    
    def log_api_call(self, provider: str, endpoint: str, cost: float, success: bool = True, error_message: str = None):
        """Log an API call for cost tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO api_calls (provider, endpoint, cost, success, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """, (provider, endpoint, cost, success, error_message))
        except Exception as e:
            logger.error(f"Error logging API call: {e}")
    
    def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get cost summary for the last N days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        provider,
                        COUNT(*) as call_count,
                        SUM(cost) as total_cost,
                        AVG(cost) as avg_cost
                    FROM api_calls 
                    WHERE timestamp >= datetime('now', '-{} days')
                    GROUP BY provider
                """.format(days))
                
                results = {}
                total_cost = 0
                total_calls = 0
                
                for row in cursor:
                    provider_data = {
                        'call_count': row[1],
                        'total_cost': row[2],
                        'avg_cost': row[3]
                    }
                    results[row[0]] = provider_data
                    total_cost += row[2]
                    total_calls += row[1]
                
                results['summary'] = {
                    'total_cost': total_cost,
                    'total_calls': total_calls,
                    'days': days
                }
                
                return results
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return {}
    
    def create_search_job(self, job_id: str, query: str, location: str = None, config: Dict = None) -> bool:
        """Create a new search job"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO search_jobs (id, query, location, config)
                    VALUES (?, ?, ?, ?)
                """, (job_id, query, location, json.dumps(config or {})))
                return True
        except Exception as e:
            logger.error(f"Error creating search job: {e}")
            return False
    
    def update_search_job(self, job_id: str, **kwargs):
        """Update search job status and progress"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Build dynamic update query
                set_clauses = []
                values = []
                
                for key, value in kwargs.items():
                    if key in ['status', 'total_results', 'processed_results']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if set_clauses:
                    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(job_id)
                    
                    query = f"UPDATE search_jobs SET {', '.join(set_clauses)} WHERE id = ?"
                    conn.execute(query, values)
        except Exception as e:
            logger.error(f"Error updating search job: {e}")
    
    def get_businesses_for_export(self, limit: Optional[int] = None, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get businesses for export"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM businesses"
                params = []
                
                if job_id:
                    query += " WHERE source_search = ?"
                    params.append(job_id)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                businesses = []
                
                for row in cursor:
                    business = dict(row)
                    # Convert JSON strings back to objects
                    business['categories'] = json.loads(business.get('categories') or '[]')
                    business['hours'] = json.loads(business.get('hours') or '{}')
                    businesses.append(business)
                
                return businesses
        except Exception as e:
            logger.error(f"Error getting businesses for export: {e}")
            return []