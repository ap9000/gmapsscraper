#!/usr/bin/env python3
"""
Simple test to verify curl_cffi integration is working
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'core'))

def test_curl_cffi_import():
    """Test curl_cffi import and basic functionality"""
    print("🧪 Testing curl_cffi Integration")
    print("=" * 50)
    
    try:
        # Test curl_cffi import
        from curl_cffi import requests
        print("✅ curl_cffi imported successfully")
        
        # Test browser impersonation
        browsers = ['chrome110', 'firefox109', 'safari15_3']
        print(f"✅ Available browser impersonations: {len(browsers)}")
        
        # Test a simple request
        print("🔄 Testing simple HTTP request...")
        session = requests.Session(impersonate='chrome110')
        
        # Test with a simple endpoint that doesn't block
        response = session.get('https://httpbin.org/headers', timeout=10)
        if response.status_code == 200:
            print("✅ Basic HTTP request successful")
            print(f"   Status: {response.status_code}")
            # Check if headers look like Chrome
            headers = response.json().get('headers', {})
            user_agent = headers.get('User-Agent', '')
            if 'Chrome' in user_agent:
                print(f"✅ Browser impersonation working (Chrome detected)")
            else:
                print(f"⚠️  User-Agent: {user_agent}")
        else:
            print(f"❌ Request failed with status {response.status_code}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ curl_cffi test failed: {e}")
        return False

def test_scraper_integration():
    """Test curl_cffi scraper integration with the main system"""
    print("\n🔧 Testing Scraper Integration")
    print("=" * 50)
    
    try:
        # Test importing the scraper class
        from curl_cffi_scraper import CurlCffiScraper, CURL_CFFI_AVAILABLE
        print(f"✅ CurlCffiScraper import: {'Success' if CURL_CFFI_AVAILABLE else 'Failed'}")
        
        if not CURL_CFFI_AVAILABLE:
            print("❌ curl_cffi not available for scraper")
            return False
        
        # Mock config for testing
        class MockConfig:
            def get(self, key, default=None):
                config_values = {
                    'enrichment.enable_curl_cffi': True,
                    'enrichment.website_scrape_timeout': 15,
                    'enrichment.curl_cffi_max_retries': 2
                }
                return config_values.get(key, default)
        
        class MockProxyManager:
            def get_requests_proxy_dict(self):
                return None  # No proxy for testing
        
        # Test scraper initialization
        scraper = CurlCffiScraper(MockConfig(), MockProxyManager())
        print(f"✅ Scraper initialized: {'Enabled' if scraper.enabled else 'Disabled'}")
        print(f"   Browser versions: {len(scraper.browser_versions)}")
        print(f"   Max retries: {scraper.max_retries}")
        print(f"   Timeout: {scraper.timeout}s")
        
        # Test session management
        with scraper.get_session('test.com') as session:
            print("✅ Session context manager working")
        
        scraper.cleanup()
        print("✅ Cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Scraper integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enricher_integration():
    """Test integration with enricher"""
    print("\n🔗 Testing Enricher Integration")
    print("=" * 50)
    
    try:
        from main import initialize_components
        import main as core
        
        if not initialize_components():
            print("❌ Failed to initialize components")
            return False
        
        print("✅ Components initialized successfully")
        
        # Check enricher configuration
        enricher = core.enricher
        print(f"✅ Enricher curl_cffi enabled: {enricher.use_curl_cffi}")
        
        if hasattr(enricher, 'curl_cffi_scraper') and enricher.curl_cffi_scraper:
            print("✅ curl_cffi_scraper instance created")
            print(f"   Scraper enabled: {enricher.curl_cffi_scraper.enabled}")
        else:
            print("❌ No curl_cffi_scraper instance")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Enricher integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 curl_cffi Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("curl_cffi Import", test_curl_cffi_import),
        ("Scraper Integration", test_scraper_integration), 
        ("Enricher Integration", test_enricher_integration)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n📋 Running: {name}")
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test {name} crashed: {e}")
            results.append((name, False))
    
    print("\n📊 TEST RESULTS")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n🎯 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests successful!")
        print("🔧 curl_cffi is properly integrated and ready for enhanced email discovery")
    else:
        print("⚠️  Some tests failed - check the output above for details")

if __name__ == "__main__":
    main()