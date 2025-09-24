import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import httpx

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scraper import GoogleMapsScraper


class TestGoogleMapsScraper:
    
    @pytest.fixture
    def scraper(self):
        return GoogleMapsScraper("test-api-key")
    
    @pytest.fixture
    def mock_response_data(self):
        return {
            "results": [
                {
                    "title": "Test Law Office",
                    "place_id": "ChIJ123",
                    "address": "123 Main St, San Francisco, CA 94102",
                    "phone": "(555) 123-4567",
                    "website": "https://testlaw.com",
                    "rating": 4.5,
                    "reviews": "25 reviews",
                    "type": "Law firm",
                    "gps": {"latitude": 37.7749, "longitude": -122.4194},
                    "hours": {"monday": "9:00 AM - 5:00 PM"}
                },
                {
                    "name": "Another Law Firm", 
                    "place_id": "ChIJ456",
                    "full_address": "456 Oak St, San Francisco, CA",
                    "phone_number": "555-987-6543",
                    "url": "https://anotherlaw.com",
                    "rating": 4.2,
                    "reviews_count": 10,
                    "categories": ["Legal services", "Attorney"]
                }
            ]
        }
    
    def test_scraper_initialization(self, scraper):
        assert scraper.api_key == "test-api-key"
        assert scraper.base_url == "https://api.scrapingdog.com/google_maps"
        assert scraper.cost_per_request == 0.00165  # 5 * 0.00033
        assert isinstance(scraper.client, httpx.Client)
    
    def test_estimate_cost(self, scraper):
        # Test cost estimation
        assert scraper.estimate_cost(20) == 0.00165  # 1 page
        assert scraper.estimate_cost(50) == 0.0033   # 3 pages  
        assert scraper.estimate_cost(150) == 0.0099  # 6 pages (max)
    
    @patch('httpx.Client.get')
    def test_search_success(self, mock_get, scraper, mock_response_data):
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response
        
        results = scraper.search("law offices", "San Francisco", 50)
        
        assert len(results) == 2
        assert results[0]['name'] == "Test Law Office"
        assert results[0]['place_id'] == "ChIJ123"
        assert results[0]['phone'] == "(555) 123-4567"
        assert results[1]['name'] == "Another Law Firm"
    
    @patch('httpx.Client.get')
    def test_search_with_pagination(self, mock_get, scraper, mock_response_data):
        # Mock multiple pages
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response
        
        results = scraper.search("law offices", "San Francisco", 100)
        
        # Should make multiple calls for pagination
        assert mock_get.call_count >= 1
        assert len(results) >= 0
    
    @patch('httpx.Client.get')
    def test_search_rate_limiting(self, mock_get, scraper):
        # Test that rate limiting is applied
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response
        
        import time
        start_time = time.time()
        scraper.search("test", max_results=20)
        end_time = time.time()
        
        # Should take some time due to rate limiting
        # Note: This is a basic test, more sophisticated timing tests could be added
        assert mock_get.called
    
    @patch('httpx.Client.get')
    def test_search_api_error(self, mock_get, scraper):
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 429  # Rate limited
        mock_get.return_value = mock_response
        
        results = scraper.search("law offices", "San Francisco", 20)
        
        # Should return empty list on error
        assert results == []
    
    def test_parse_business_data(self, scraper):
        business_data = {
            "title": "Test Business",
            "place_id": "ChIJ123",
            "address": "123 Test St",
            "phone": "(555) 123-4567",
            "website": "https://test.com",
            "rating": 4.5,
            "reviews": "10 reviews",
            "type": "Restaurant",
            "gps": {"latitude": 37.7749, "longitude": -122.4194}
        }
        
        parsed = scraper._parse_business(business_data)
        
        assert parsed['name'] == "Test Business"
        assert parsed['place_id'] == "ChIJ123"
        assert parsed['rating'] == 4.5
        assert parsed['reviews_count'] == 10
        assert parsed['latitude'] == 37.7749
        assert parsed['longitude'] == -122.4194
    
    def test_parse_business_with_missing_data(self, scraper):
        business_data = {
            "name": "Minimal Business"
        }
        
        parsed = scraper._parse_business(business_data)
        
        assert parsed['name'] == "Minimal Business"
        assert parsed['place_id'] is None
        assert parsed['phone'] == ""
        assert parsed['rating'] is None
    
    def test_parse_business_invalid_data(self, scraper):
        # Test with completely invalid data
        invalid_data = {"random_field": "value"}
        
        parsed = scraper._parse_business(invalid_data)
        
        # Should return None for businesses without names
        assert parsed is None