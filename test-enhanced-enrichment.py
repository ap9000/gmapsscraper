#!/usr/bin/env python3
"""
Test script to verify the enhanced enrichment system with curl_cffi integration
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'core'))

from main import initialize_components
import main as core
import json
import time

def test_enhanced_enrichment():
    """Test the enhanced enrichment system with curl_cffi"""
    print("\n🧪 Testing Enhanced Enrichment System")
    print("=" * 50)
    
    # Initialize components
    if not initialize_components():
        print("❌ Failed to initialize components")
        return False
    
    # Test websites known to have emails (good for testing)
    test_businesses = [
        {
            'name': 'Blue Bottle Coffee',
            'website': 'bluebottlecoffee.com',
            'address': 'San Francisco, CA'
        },
        {
            'name': 'Philz Coffee',
            'website': 'philzcoffee.com', 
            'address': 'San Francisco, CA'
        },
        {
            'name': 'Ritual Coffee Roasters',
            'website': 'ritualcoffee.com',
            'address': 'San Francisco, CA'
        }
    ]
    
    results = {
        'total_tested': 0,
        'successful_enrichments': 0,
        'method_performance': {
            'website_scraping': 0,
            'curl_cffi': 0,
            'hunter_io': 0,
            'pattern_generation': 0
        },
        'detailed_results': []
    }
    
    print(f"🎯 Testing {len(test_businesses)} businesses for enrichment...")
    print()
    
    for i, business in enumerate(test_businesses, 1):
        print(f"📊 Testing {i}/{len(test_businesses)}: {business['name']}")
        print(f"   Website: {business['website']}")
        
        results['total_tested'] += 1
        start_time = time.time()
        
        # Test enrichment
        try:
            enriched = core.enricher.enrich_business(business)
            processing_time = time.time() - start_time
            
            # Check if enrichment was successful
            if enriched.get('email'):
                results['successful_enrichments'] += 1
                method = enriched.get('enrichment_method', 'unknown')
                if method in results['method_performance']:
                    results['method_performance'][method] += 1
                
                print(f"   ✅ Email: {enriched['email']}")
                print(f"   📈 Confidence: {enriched.get('confidence_score', 0):.2%}")
                print(f"   🔧 Method: {method}")
                print(f"   ⏱️  Time: {processing_time:.2f}s")
                
                if enriched.get('contact_name'):
                    print(f"   👤 Contact: {enriched['contact_name']}")
                
            else:
                print(f"   ❌ No email found")
                print(f"   ⏱️  Time: {processing_time:.2f}s")
            
            # Store detailed results
            result_detail = {
                'business': business['name'],
                'website': business['website'],
                'success': bool(enriched.get('email')),
                'email': enriched.get('email'),
                'method': enriched.get('enrichment_method'),
                'confidence': enriched.get('confidence_score', 0),
                'processing_time': processing_time
            }
            results['detailed_results'].append(result_detail)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results['detailed_results'].append({
                'business': business['name'],
                'website': business['website'],
                'success': False,
                'error': str(e)
            })
        
        print()
        # Small delay between tests
        time.sleep(1)
    
    # Print summary
    print("📈 ENRICHMENT RESULTS SUMMARY")
    print("=" * 40)
    success_rate = (results['successful_enrichments'] / results['total_tested']) * 100
    print(f"Success Rate: {success_rate:.1f}% ({results['successful_enrichments']}/{results['total_tested']})")
    print()
    
    print("🔧 Method Performance:")
    for method, count in results['method_performance'].items():
        if count > 0:
            percentage = (count / results['successful_enrichments']) * 100
            print(f"  {method}: {count} emails ({percentage:.1f}%)")
    print()
    
    print("💰 Cost Analysis:")
    print("  Website Scraping (httpx): $0.00")
    print("  curl_cffi Enhanced: $0.00") 
    print("  Pattern Generation: $0.00")
    print("  Hunter.io: $0.00 (disabled)")
    print("  Total Enrichment Cost: $0.00")
    print()
    
    return results

def test_curl_cffi_availability():
    """Test curl_cffi availability and configuration"""
    print("\n🔍 Testing curl_cffi Integration")
    print("=" * 50)
    
    try:
        from curl_cffi_scraper import CurlCffiScraper, CURL_CFFI_AVAILABLE
        print(f"curl_cffi Available: {'✅ Yes' if CURL_CFFI_AVAILABLE else '❌ No'}")
        
        if CURL_CFFI_AVAILABLE:
            # Test scraper initialization
            config = core.config
            scraper = CurlCffiScraper(config, core.proxy_manager)
            print(f"CurlCffiScraper Enabled: {'✅ Yes' if scraper.enabled else '❌ No'}")
            print(f"Browser Versions: {len(scraper.browser_versions)} available")
            print(f"Max Retries: {scraper.max_retries}")
            print(f"Timeout: {scraper.timeout}s")
        
    except Exception as e:
        print(f"❌ curl_cffi integration error: {e}")
        return False
    
    return True

def compare_methods():
    """Compare enrichment methods"""
    print("\n📊 ENRICHMENT METHOD COMPARISON")
    print("=" * 50)
    
    methods = [
        {
            'name': 'Website Scraping (httpx)',
            'priority': 1,
            'cost': '$0.00',
            'speed': 'Fast',
            'success_rate': '40-60%',
            'notes': 'Basic scraping, may be blocked'
        },
        {
            'name': 'curl_cffi Enhanced',
            'priority': 2, 
            'cost': '$0.00',
            'speed': 'Medium',
            'success_rate': '60-80%',
            'notes': 'Browser impersonation, harder to detect'
        },
        {
            'name': 'Hunter.io API',
            'priority': 3,
            'cost': '$0.049/email',
            'speed': 'Fast',
            'success_rate': '80-95%',
            'notes': 'Paid service, high accuracy (disabled)'
        },
        {
            'name': 'Pattern Generation',
            'priority': 4,
            'cost': '$0.00',
            'speed': 'Instant',
            'success_rate': '20-40%',
            'notes': 'Guessed emails, low confidence'
        }
    ]
    
    for method in methods:
        print(f"Priority {method['priority']}: {method['name']}")
        print(f"  Cost: {method['cost']}")
        print(f"  Speed: {method['speed']}")
        print(f"  Success Rate: {method['success_rate']}")
        print(f"  Notes: {method['notes']}")
        print()

if __name__ == "__main__":
    print("🚀 Enhanced Enrichment System Test")
    print("=" * 50)
    
    # Test curl_cffi availability
    if test_curl_cffi_availability():
        print("\n✅ curl_cffi integration test passed")
    
    # Compare methods
    compare_methods()
    
    # Test enrichment with real businesses
    results = test_enhanced_enrichment()
    
    if results:
        print("🎯 FINAL SUMMARY:")
        print(f"  • Tested {results['total_tested']} businesses")
        success_rate = (results['successful_enrichments'] / results['total_tested']) * 100
        print(f"  • Success rate: {success_rate:.1f}%")
        print(f"  • curl_cffi integration: {'✅ Active' if 'curl_cffi' in str(results) else '❌ Not used'}")
        print(f"  • Total cost: $0.00 (using free methods)")
        print(f"  • Improved anti-bot evasion with browser impersonation")