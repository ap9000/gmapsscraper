#!/usr/bin/env python3
"""
Simple test script to debug the ScrapingDog API response
"""

import httpx
import json
import sys

def test_scrapingdog_api():
    """Test the ScrapingDog Google Maps API directly"""
    
    # API configuration
    api_key = "68d373cbb2c8ad1c3f875812"  # Your API key from config
    base_url = "https://api.scrapingdog.com/google_maps"
    
    # Test parameters
    params = {
        'query': 'law offices',
        'location': 'San Francisco, CA',
        'page': 0,
        'api_key': api_key
    }
    
    print("=== ScrapingDog API Test ===")
    print(f"URL: {base_url}")
    print(f"Parameters: {json.dumps({k: v if k != 'api_key' else '***' for k, v in params.items()}, indent=2)}")
    print()
    
    try:
        # Make the request
        print("Making request...")
        with httpx.Client(timeout=30) as client:
            response = client.get(base_url, params=params)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("=== RESPONSE JSON ===")
                print(json.dumps(data, indent=2))
                print()
                
                # Analyze structure
                print("=== STRUCTURE ANALYSIS ===")
                print(f"Response type: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"Top-level keys: {list(data.keys())}")
                    for key, value in data.items():
                        print(f"  {key}: {type(value)} (length: {len(value) if hasattr(value, '__len__') else 'N/A'})")
                        
                        # If it's a list with items, show first item structure
                        if isinstance(value, list) and len(value) > 0:
                            print(f"    First item type: {type(value[0])}")
                            if isinstance(value[0], dict):
                                print(f"    First item keys: {list(value[0].keys())}")
                elif isinstance(data, list):
                    print(f"Response is a list with {len(data)} items")
                    if len(data) > 0:
                        print(f"First item type: {type(data[0])}")
                        if isinstance(data[0], dict):
                            print(f"First item keys: {list(data[0].keys())}")
                else:
                    print(f"Unexpected response type: {type(data)}")
                    print(f"Content: {data}")
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                print("Raw response:")
                print(response.text[:1000])
        else:
            print(f"Request failed with status {response.status_code}")
            print("Response text:")
            print(response.text)
            
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    test_scrapingdog_api()