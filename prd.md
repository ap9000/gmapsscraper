# Google Maps Lead Generator - Implementation Guide

## Project Overview
Build a cost-optimized Python tool that scrapes Google Maps for business data and enriches it with contact information. This tool prioritizes low cost over convenience, using the cheapest available APIs.

## Core Objective
Create a CLI tool that can:
1. Search Google Maps for businesses (e.g., "law offices in San Francisco")
2. Extract comprehensive business data
3. Find email addresses and contact names
4. Export to CSV for CRM/outreach tools
5. Process batch searches from a queue
6. Track API costs to stay under $100/month

## Implementation Priority
Build in this order:
1. ScrapingDog API integration for Google Maps
2. CSV export functionality
3. Basic email extraction from websites
4. Batch processing from CSV input
5. Hunter.io integration for email enrichment
6. Deduplication and caching
7. Cost tracking and reporting

## Project Structure
```
google-maps-leads/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── scraper.py           # ScrapingDog API wrapper
│   ├── enricher.py          # Email/contact enrichment
│   ├── database.py          # SQLite operations
│   ├── exporter.py          # CSV/JSON export
│   ├── deduplicator.py      # Dedup logic
│   └── utils.py             # Helper functions
├── config/
│   ├── config.yaml          # API keys and settings
│   └── config.example.yaml  # Template for users
├── data/
│   ├── cache.db             # SQLite cache
│   ├── searches/            # Input CSV files
│   └── exports/             # Output files
├── tests/
│   ├── test_scraper.py
│   ├── test_enricher.py
│   └── fixtures/            # Mock API responses
├── requirements.txt
├── README.md
└── .env.example
```

## Key Implementation Details

### 1. ScrapingDog Integration
```python
# Core function structure for scraper.py
class GoogleMapsScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.scrapingdog.com/google_maps"
        
    def search(self, query: str, location: str, max_results: int = 100):
        # Implementation notes:
        # - Handle pagination (20 results per page)
        # - Add retry logic with exponential backoff
        # - Parse all available fields from response
        # - Cache results in SQLite to avoid duplicate API calls
```

The ScrapingDog API returns paginated results. Implement proper pagination handling to get all results up to max_results.

### 2. Email Enrichment Waterfall
```python
# enricher.py structure
class EmailEnricher:
    def enrich(self, business_data: dict) -> dict:
        # Try these methods in order:
        # 1. Scrape website if URL exists (free)
        # 2. Hunter.io domain search (paid)
        # 3. Common patterns (firstname.lastname@domain.com)
        # Return first valid email found
```

Prioritize free methods (website scraping) before paid APIs. Validate emails before accepting them.

### 3. Database Schema
```sql
-- SQLite schema for cache.db
CREATE TABLE businesses (
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
    categories JSON,
    hours JSON,
    latitude REAL,
    longitude REAL,
    enriched_at TIMESTAMP,
    confidence_score REAL,
    source_search TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT,
    endpoint TEXT,
    cost REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. CLI Interface
```python
# main.py using Click or argparse
# Commands to implement:

# Single search
python main.py search "law offices" --location "San Francisco" --max 100 --enrich

# Batch processing
python main.py batch input.csv --enrich --export

# Check costs
python main.py costs --current-month

# Resume interrupted job
python main.py resume <job_id>
```

### 5. Configuration File
```yaml
# config/config.yaml structure
apis:
  scrapingdog:
    api_key: "YOUR_KEY_HERE"
    requests_per_second: 10
  hunter:
    api_key: "YOUR_KEY_HERE"  # Optional
    enabled: false

settings:
  max_results_per_search: 200
  enable_caching: true
  cache_ttl_days: 30
  export_format: "csv"  # csv or json
  
enrichment:
  enable_website_scraping: true
  enable_hunter: false
  email_confidence_threshold: 0.7
  timeout_seconds: 10

paths:
  exports_dir: "./data/exports"
  cache_db: "./data/cache.db"
```

### 6. Cost Tracking
Keep accurate cost tracking:
- ScrapingDog: $0.00033 per request
- Hunter.io: $0.049 per successful email find
- Log every API call with its cost
- Provide daily/monthly summaries
- Alert when approaching limits

### 7. Error Handling
```python
# Implement robust error handling:
- API rate limits: Use exponential backoff
- Network failures: Retry 3 times
- Invalid data: Log and continue
- Save state frequently for resume capability
```

### 8. Testing Approach
Create tests with mocked API responses:
```python
# tests/test_scraper.py
def test_google_maps_search_parsing():
    # Use mock response from tests/fixtures/
    # Verify all fields are extracted correctly
    
def test_pagination_handling():
    # Test that pagination works for >20 results
    
def test_retry_logic():
    # Test exponential backoff on failures
```

## Key Dependencies
```txt
# requirements.txt