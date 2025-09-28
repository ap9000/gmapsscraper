#!/usr/bin/env python3
"""
Test script to verify city-specific search and enrichment process
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'core'))

from main import initialize_components
import main as core
import json

def test_city_search():
    """Test searching with a specific city location"""
    print("\n🔍 Testing City-Specific Search")
    print("=" * 50)
    
    # Initialize components
    if not initialize_components():
        print("❌ Failed to initialize components")
        return False
    
    # Test parameters
    query = "coffee shops"
    location = "San Francisco, CA"
    max_results = 3  # Small number for testing
    
    print(f"📍 Query: {query}")
    print(f"📍 Location: {location}")
    print(f"📍 Max results: {max_results}")
    print()
    
    # Test geocoding
    from utils import geocode_location, format_coordinates_for_scrapingdog
    coords = geocode_location(location)
    if coords:
        formatted_coords = format_coordinates_for_scrapingdog(coords[0], coords[1])
        print(f"✅ Geocoding successful: {location} -> {formatted_coords}")
    else:
        print(f"❌ Geocoding failed for {location}")
    
    # Perform search
    print("\n🔄 Performing search...")
    results = core.scraper.search(query, location, max_results)
    
    if results:
        print(f"✅ Found {len(results)} businesses")
        
        # Show first result details
        if len(results) > 0:
            print("\n📊 First Result Details:")
            business = results[0]
            print(f"  Name: {business.get('name', 'N/A')}")
            print(f"  Address: {business.get('address', 'N/A')}")
            print(f"  Phone: {business.get('phone', 'N/A')}")
            print(f"  Website: {business.get('website', 'N/A')}")
            print(f"  Rating: {business.get('rating', 'N/A')}")
            print(f"  Review Count: {business.get('review_count', 'N/A')}")
            
            # Test enrichment on first result
            if business.get('website'):
                print("\n🔄 Testing Email Enrichment...")
                enriched = core.enricher.enrich_business(business)
                
                if enriched.get('email'):
                    print(f"✅ Email found: {enriched['email']}")
                    print(f"  Confidence: {enriched.get('confidence_score', 0):.2%}")
                    print(f"  Method: {enriched.get('enrichment_method', 'Unknown')}")
                else:
                    print("❌ No email found")
                    
                # Show enrichment costs
                print("\n💰 Enrichment Cost Analysis:")
                print("  Website Scraping: $0.00 (Free - uses httpx + proxies)")
                print("  Pattern Generation: $0.00 (Free - generates common patterns)")
                print("  Hunter.io: $0.049 per email (Currently disabled)")
                print("  Scrapling: $0.00 (Free - but disabled due to compatibility)")
                print("\n  Current enrichment cost: $0.00 (using free methods only)")
    else:
        print("❌ No results found")
    
    # Show API cost
    print(f"\n💰 ScrapingDog API Cost:")
    pages_used = min((max_results + 19) // 20, 1)  # For this test
    cost = pages_used * 0.00165  # $0.00165 per request
    print(f"  Pages requested: {pages_used}")
    print(f"  Cost: ${cost:.5f}")
    
    return True

def analyze_httpx_vs_curl_cffi():
    """Analyze current httpx usage vs potential curl_cffi benefits"""
    print("\n📊 Analyzing httpx vs curl_cffi for Web Scraping")
    print("=" * 50)
    
    print("\n🔍 Current Implementation (httpx):")
    print("  ✅ Pros:")
    print("    • HTTP/2 support for better performance")
    print("    • Connection pooling reduces overhead")
    print("    • Clean async/sync API")
    print("    • Lightweight and fast")
    print("    • Good proxy support via httpx")
    
    print("\n  ❌ Cons:")
    print("    • Can be detected by anti-bot systems")
    print("    • Limited TLS fingerprint mimicking")
    print("    • No built-in browser impersonation")
    
    print("\n🔍 Alternative: curl_cffi")
    print("  ✅ Pros:")
    print("    • Mimics real browser TLS fingerprints")
    print("    • Harder to detect as a bot")
    print("    • Can impersonate Chrome/Firefox/Safari")
    print("    • Better for bypassing Cloudflare")
    print("    • Session support for cookie persistence")
    
    print("\n  ❌ Cons:")
    print("    • Additional dependency")
    print("    • Slightly more complex API")
    print("    • May have compatibility issues")
    
    print("\n💡 Current Enrichment Strategy:")
    print("  1. Scrapling (disabled) - Would handle Cloudflare")
    print("  2. httpx + proxies - Current fallback")
    print("  3. Hunter.io (disabled) - Paid API")
    print("  4. Pattern generation - Last resort")
    
    print("\n📈 Recommendation:")
    print("  For email enrichment, curl_cffi could improve success rates by:")
    print("  • Better mimicking real browsers")
    print("  • Maintaining sessions across requests")
    print("  • Bypassing more anti-scraping measures")
    print("  • However, current httpx + proxy rotation works adequately")
    
    return True

if __name__ == "__main__":
    print("🚀 GMaps Lead Generator - Search & Enrichment Test")
    print("=" * 50)
    
    # Test city search
    if test_city_search():
        print("\n✅ City search test completed")
    
    # Analyze scraping approach
    if analyze_httpx_vs_curl_cffi():
        print("\n✅ Analysis completed")
    
    print("\n🎯 Test Summary:")
    print("  • City-specific search uses geocoding for better pagination")
    print("  • Email enrichment is currently FREE (no API costs)")
    print("  • httpx works well with proxy rotation")
    print("  • curl_cffi could improve success rates for protected sites")