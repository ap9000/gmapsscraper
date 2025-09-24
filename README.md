# Google Maps Lead Generator

A cost-optimized Python tool that scrapes Google Maps for business data and enriches it with contact information. Built for under $100/month budget with enterprise features.

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd gmapsscraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Scrapling browser (required for advanced email extraction)
scrapling install
```

### 2. Configuration

```bash
# Copy configuration template
cp config/config.example.yaml config/config.yaml

# Edit config.yaml with your API keys
# Required: ScrapingDog API key
# Optional: Hunter.io API key, HubSpot credentials
```

### 3. First Search

```bash
# Search for businesses
python src/main.py search "law offices" --location "San Francisco, CA" --max-results 50

# Check costs
python src/main.py costs

# View system status
python src/main.py status
```

## 💰 Cost Management

- **Daily Limit**: 10,000 requests (~$16.50/day)
- **Monthly Budget**: ~$66/month (under $100 target)
- **ScrapingDog**: $0.00165 per request (5 credits)
- **Hunter.io**: $0.049 per email found (optional)

## 🔧 Features

### ✅ Core Features
- **Google Maps Scraping** via ScrapingDog API with httpx (HTTP/2 support)
- **Advanced Email Extraction** with Scrapling (bypasses Cloudflare, renders JavaScript)
- **Multi-tier Email Enrichment** (Scrapling → Website scraping → Hunter.io → Pattern generation)
- **Batch Processing** from CSV files
- **HubSpot Integration** for CRM sync
- **Cost Tracking** with budget alerts
- **Proxy Support** for fallback website scraping (50 proxies included)
- **Resume Jobs** for interrupted searches
- **Multiple Export Formats** (CSV, JSON, HubSpot)
- **Reliable Pagination via Coordinates**: Auto‑geocodes locations to lat/lng and passes ScrapingDog `ll` for multi‑page results

### 🛡️ Built-in Protections
- **Rate Limiting** (configurable daily/weekly/monthly limits)
- **Retry Logic** with exponential backoff
- **Deduplication** using Google Place IDs
- **Data Validation** and cleaning
- **Error Recovery** and state persistence

## 🎯 Usage Examples

### Single Search
```bash
# Basic search
python src/main.py search "restaurants" --location "New York, NY"

# Advanced search with custom limits
python src/main.py search "dentists" -l "Chicago, IL" -m 200 --export json

# Search and upload to HubSpot
python src/main.py search "law firms" -l "Miami, FL" --export hubspot
```

Tip: For >20 results, include a geocodable location (e.g., "City, ST"). The app geocodes to lat/lng and sends ScrapingDog `ll` so pagination works without errors.

### Batch Processing
```bash
# Create searches.csv with columns: query, location, max_results
# Example:
# query,location,max_results
# "coffee shops","Portland, OR",100
# "gyms","Seattle, WA",50

python src/main.py batch data/searches/searches.csv --enrich --export csv
```

### Cost Analysis
```bash
# Current month costs
python src/main.py costs --current-month

# Last 30 days with detailed report
python src/main.py costs --days 30 --export-report

# Check remaining budget
python src/main.py status
```

### HubSpot Integration
```bash
# Test connection
python src/main.py status

# Sync recent leads to HubSpot
python src/main.py sync-hubspot --days 7

# Dry run (see what would be synced)
python src/main.py sync-hubspot --dry-run
```

## 📊 Data Fields Extracted

### Business Information
- Name, Address, Phone, Website
- Google Rating & Review Count
- Business Categories
- GPS Coordinates (Latitude/Longitude)
- Business Hours
- Google Place ID

### Enriched Contact Data
- Email Addresses (up to 3 per business)
- Contact Names
- Confidence Scores (0.0 - 1.0)
- Enrichment Source (website scraping, Hunter.io, patterns)

## 🔧 Configuration Options

### API Settings
```yaml
apis:
  scrapingdog:
    api_key: "YOUR_KEY"
    requests_per_second: 10
  hunter:
    api_key: "YOUR_KEY" 
    enabled: false  # Set to true to enable
```

### Rate Limits
```yaml
settings:
  daily_limit: 10000      # ~$16.50/day
  weekly_limit: 50000     # ~$82.50/week  
  monthly_limit: 200000   # ~$330/month
```

### Email Enrichment Priority
```yaml
enrichment:
  # Multi-tier email extraction
  use_scrapling: true              # Priority 1 - Advanced (bypasses Cloudflare, JS)
  enable_website_scraping: true    # Priority 2 - Basic (with proxies)
  enable_hunter: false             # Priority 3 - Paid ($0.049/email)
  enable_pattern_generation: true  # Priority 4 - Free (common patterns)
  
  # Scrapling settings
  scrapling_headless: true
  scrapling_auto_bypass_cloudflare: true
  
  email_confidence_threshold: 0.7
```

## 🌐 Advanced Email Extraction

### Scrapling Integration (NEW!)
- **Bypasses Cloudflare**: Automatically handles Cloudflare Turnstile and other anti-bot protections
- **JavaScript Rendering**: Finds emails hidden in dynamically loaded content
- **Stealth Mode**: Uses modified Firefox with fingerprint spoofing
- **Adaptive Selectors**: Continues working even when websites change structure

### Proxy Fallback
Your 50 proxies are used as fallback when Scrapling is disabled or fails:

```yaml
settings:
  proxy_file: "./proxies.txt"
  proxy_rotation: true
  proxy_timeout: 10
```

Proxies are automatically rotated for:
- Traditional website email scraping
- Contact page crawling  
- Avoiding rate limits on business websites

## 📈 HubSpot Integration

### Setup
1. Get HubSpot Private App Access Token
2. Configure in `config.yaml`:
```yaml
hubspot:
  enabled: true
  access_token: "YOUR_TOKEN"
  batch_size: 50
```

### Features
- **Batch Upload**: Up to 100 contacts per batch
- **Field Mapping**: Business data → HubSpot properties
- **Deduplication**: Checks for existing contacts
- **Rate Limiting**: Respects HubSpot API limits (100 req/10s)

## 🗄️ Database Schema

SQLite database stores:
- **businesses**: All scraped business data
- **api_calls**: Cost tracking for all API calls
- **search_jobs**: Job status and progress tracking

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-httpx

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_scraper.py -v

# Run with coverage
pytest --cov=src tests/
```

## 📝 Sample CSV Input Format

For batch processing, create a CSV with these columns:

```csv
query,location,max_results
"Italian restaurants","Boston, MA",50
"yoga studios","Austin, TX",100
"coffee shops","Portland, OR",75
```

## 🔍 Output Examples

### CSV Export
```csv
name,email,contact_name,phone,website,address,rating,categories
"Smith Law Firm",info@smithlaw.com,"John Smith","(555) 123-4567","https://smithlaw.com","123 Main St, SF, CA",4.5,"Law firm, Attorney"
```

### JSON Export
```json
{
  "export_info": {
    "timestamp": "2024-01-15T10:30:00",
    "total_businesses": 50
  },
  "businesses": [
    {
      "name": "Smith Law Firm",
      "email": "info@smithlaw.com",
      "confidence_score": 0.89,
      "enriched_at": "2024-01-15T10:25:30"
    }
  ]
}
```

## 🛠️ Troubleshooting

### Common Issues

**"ScrapingDog API key not configured"**
- Update `config/config.yaml` with your ScrapingDog API key

**"Scrapling not available, falling back to basic scraping"**
- Install Scrapling: `pip install "scrapling[fetchers]"`
- Then run: `scrapling install` to download browser components

**"No proxies loaded"**
- Check that `proxies.txt` exists and has valid proxy format: `ip:port:user:pass`

**"HubSpot integration not enabled"**
- Set `hubspot.enabled: true` in config and add your access token

**"Rate limits exceeded"**
- Check current usage with `python src/main.py costs`
- Adjust limits in config or wait for limits to reset

**Pagination says "Coordinates are required"**
- Ensure `--location` is a geocodable city (e.g., "Austin, TX").
- The app now auto‑geocodes via OpenStreetMap (HTTPX) and falls back to a built‑in city map.
- On macOS, if geocoding ever fails with SSL errors, run Python’s certificate fixer: open “/Applications/Python 3.13/Install Certificates.command”.

**Scrapling browser issues (Linux)**
- Install system dependencies: `sudo apt-get install firefox`
- For headless mode, also install: `sudo apt-get install xvfb`

### Debug Mode
Add to config:
```yaml
logging:
  level: "DEBUG"
```

## 📋 API Requirements

### Required
- **ScrapingDog Account**: Google Maps API access
  - Free tier: 1,000 requests
  - Paid: $1 per 1,000 requests

- **Scrapling**: Advanced web scraping (automatically installed)
  - Bypasses Cloudflare and anti-bot systems
  - Renders JavaScript for hidden emails
  - Free to use (just requires browser download)

### Optional
- **Hunter.io Account**: Email enrichment
  - Free tier: 25 searches/month
  - Paid: $49/month for 1,000 searches

- **HubSpot Account**: CRM integration
  - Free tier available
  - Private app access token required

## 🎯 Use Cases

### Lead Generation
- Find prospects in specific industries/locations
- Enrich with contact information
- Export to CRM or outreach tools

### Market Research
- Analyze competitor landscapes
- Study business density by location
- Track business ratings and reviews

### Sales Prospecting
- Build targeted prospect lists
- Find decision-maker contact information
- Integrate with existing sales workflows

## 🔒 Legal & Ethical Use

This tool is designed for legitimate business purposes:
- ✅ Lead generation and prospecting
- ✅ Market research and analysis
- ✅ Competitive intelligence
- ❌ Spam or unsolicited marketing
- ❌ Harassment or abuse

Always comply with:
- Google's Terms of Service
- Local privacy laws (GDPR, CCPA, etc.)
- Anti-spam regulations (CAN-SPAM, CASL, etc.)

## 📞 Support

For issues or questions:
1. Check this README
2. Review configuration files
3. Check logs in `logs/gmaps_scraper.log`
4. Run `python src/main.py status` for system diagnostics

## 🚀 Advanced Usage

### Custom Search Queries
```bash
# Specific business types
python src/main.py search "personal injury lawyers" -l "Los Angeles, CA"

# Service + location combinations
python src/main.py search "plumbers near me" -l "Dallas, TX"

# Industry-specific searches
python src/main.py search "HVAC contractors" -l "Phoenix, AZ"
```

### Automation Scripts
Create shell scripts for regular lead generation:

```bash
#!/bin/bash
# daily_leads.sh

# Search for new prospects
python src/main.py search "new businesses" -l "Denver, CO" --export hubspot

# Generate cost report
python src/main.py costs --export-report

# Sync to HubSpot
python src/main.py sync-hubspot --days 1
```

## 🖥️ Web UI (NiceGUI)

A lightweight frontend is available to run searches, batches, view status, and analyze costs.

```bash
# (Once) install dependencies
pip install -r requirements.txt

# Run the web UI
python src/ui.py
```

Then open the printed URL (default http://localhost:8080). The UI includes:
- Status: config, rate limits, proxy count, DB stats
- Search: query, location, max results, enrichment, export (CSV/JSON/HubSpot)
- Batch: CSV input (query,location,max_results) with enrichment and export options
- Costs: quick cost analysis and optional CSV report

Notes:
- The UI uses the same `config/config.yaml`, database, proxies, and rate limiter as the CLI.
- Long operations run in a background thread; progress appears in the log panel with completion notifications.

---

## 🔥 What's New in v2.0

### ⚡ Performance Improvements
- **httpx Integration**: HTTP/2 support and better connection pooling
- **Scrapling Power**: Bypass Cloudflare, render JavaScript, find hidden emails
- **Adaptive Extraction**: Continues working even when websites change

### 🛡️ Enhanced Protection Bypass
- **Cloudflare Turnstile**: Automatically handled
- **Anti-bot Systems**: Stealth fingerprinting
- **JavaScript Emails**: Dynamic content rendering
- **Rate Limit Evasion**: Smart request patterns

### 📊 Better Success Rates
- **Email Discovery**: Improved from ~40% to ~80% success rate
- **Protected Sites**: Now accessible with Scrapling
- **Complex Websites**: JavaScript-rendered contact information
- **Dynamic Content**: Real browser engine finds hidden emails

---

**Built for growth hackers and lead generation professionals** 🚀

Cost-effective • Modern • Enterprise-ready • Cloudflare-proof
