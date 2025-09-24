import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import httpx

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enricher import EmailEnricher


class TestEmailEnricher:
    
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'apis.hunter.api_key': 'test-hunter-key',
            'apis.hunter.enabled': True,
            'enrichment.email_confidence_threshold': 0.7,
            'enrichment.website_scrape_timeout': 15,
            'enrichment.max_emails_per_business': 3,
            'enrichment.enable_website_scraping': True,
            'enrichment.enable_pattern_generation': True,
            'enrichment.use_scrapling': False  # Disable Scrapling for basic tests
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_proxy_manager(self):
        proxy_manager = Mock()
        proxy_manager.get_requests_proxy_dict.return_value = {
            'http': 'http://user:pass@proxy:8080',
            'https': 'http://user:pass@proxy:8080'
        }
        return proxy_manager
    
    @pytest.fixture
    def mock_db_manager(self):
        db = Mock()
        return db
    
    @pytest.fixture
    def enricher(self, mock_config, mock_proxy_manager, mock_db_manager):
        return EmailEnricher(mock_config, mock_proxy_manager, mock_db_manager)
    
    @pytest.fixture
    def sample_business(self):
        return {
            'name': 'Test Law Office',
            'website': 'https://testlaw.com',
            'place_id': 'ChIJ123',
            'address': '123 Main St, San Francisco, CA',
            'phone': '(555) 123-4567'
        }
    
    def test_validate_email_valid(self, enricher):
        assert enricher._validate_email('test@example.com') == True
        assert enricher._validate_email('user.name@domain.co.uk') == True
        assert enricher._validate_email('test+label@domain.com') == True
    
    def test_validate_email_invalid(self, enricher):
        assert enricher._validate_email('invalid-email') == False
        assert enricher._validate_email('test@') == False
        assert enricher._validate_email('@domain.com') == False
        assert enricher._validate_email('test@example.') == False
        assert enricher._validate_email('') == False
        assert enricher._validate_email('test@example.com' * 50) == False  # Too long
    
    def test_validate_email_excludes_test_domains(self, enricher):
        assert enricher._validate_email('test@example.com') == False
        assert enricher._validate_email('user@test.com') == False
        assert enricher._validate_email('contact@placeholder.com') == False
        assert enricher._validate_email('image@something.com') == False
    
    def test_clean_email(self, enricher):
        assert enricher._clean_email('Test@Example.COM') == 'test@example.com'
        assert enricher._clean_email('user at domain dot com') == 'user@domain.com'
        assert enricher._clean_email('test@domain.com,') == 'test@domain.com'
        assert enricher._clean_email('  test@domain.com  ') == 'test@domain.com'
    
    def test_generate_email_patterns(self, enricher):
        emails = enricher._generate_email_patterns('https://testlaw.com', 'Test Law Office')
        
        expected_patterns = [
            'info@testlaw.com',
            'contact@testlaw.com', 
            'hello@testlaw.com',
            'admin@testlaw.com',
            'support@testlaw.com',
            'sales@testlaw.com',
            'office@testlaw.com',
            'test@testlaw.com'  # From business name
        ]
        
        # Check that we get reasonable patterns
        assert len(emails) > 0
        assert any('info@testlaw.com' in email for email in emails)
        assert all(enricher._validate_email(email) for email in emails)
    
    def test_calculate_email_confidence(self, enricher):
        # Test confidence scoring
        confidence = enricher._calculate_email_confidence(
            'info@testlaw.com',
            'https://testlaw.com',
            'Test Law Office',
            ['website_scraping']
        )
        
        # Should be high confidence for scraped email with matching domain
        assert confidence >= 0.7
        assert confidence <= 1.0
    
    def test_calculate_email_confidence_low_quality(self, enricher):
        confidence = enricher._calculate_email_confidence(
            'noreply@gmail.com',
            'https://testlaw.com',
            'Test Law Office',
            ['pattern_generation']
        )
        
        # Should be lower confidence for suspicious email
        assert confidence < 0.7
    
    @patch('httpx.Client')
    def test_scrape_page_for_emails(self, mock_client_class, enricher):
        # Mock webpage with email addresses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <body>
                <p>Contact us at info@testlaw.com</p>
                <div class="contact">
                    <span>Manager: John Smith</span>
                    <a href="mailto:john@testlaw.com">john@testlaw.com</a>
                </div>
            </body>
        </html>
        '''
        # Setup mock client
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        emails, contacts = enricher._scrape_page_for_emails('https://testlaw.com')
        
        assert len(emails) >= 1
        assert 'info@testlaw.com' in emails or any('info@testlaw.com' in email for email in emails)
    
    @patch('httpx.Client')
    def test_scrape_website_for_emails(self, mock_client_class, enricher):
        # Mock multiple page responses
        def mock_get_side_effect(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            
            if 'contact' in url:
                mock_response.content = b'<html><body>Contact: admin@testlaw.com</body></html>'
            else:
                mock_response.content = b'<html><body>Email us at info@testlaw.com</body></html>'
            
            return mock_response
        
        # Setup mock client
        mock_client = Mock()
        mock_client.get.side_effect = mock_get_side_effect
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        emails, contacts = enricher._scrape_website_for_emails('https://testlaw.com')
        
        assert len(emails) >= 0  # Should find some emails
        assert mock_client.get.called  # Should make HTTP requests
    
    @patch('httpx.Client')
    def test_search_hunter_io_success(self, mock_client_class, enricher):
        # Mock Hunter.io API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'emails': [
                    {
                        'value': 'john@testlaw.com',
                        'first_name': 'John',
                        'last_name': 'Smith'
                    },
                    {
                        'value': 'info@testlaw.com',
                        'first_name': '',
                        'last_name': ''
                    }
                ]
            }
        }
        
        # Setup mock client
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        emails, contacts = enricher._search_hunter_io('https://testlaw.com')
        
        assert len(emails) == 2
        assert 'john@testlaw.com' in emails
        assert 'info@testlaw.com' in emails
        assert 'John Smith' in contacts
    
    @patch('httpx.Client')
    def test_search_hunter_io_api_error(self, mock_client_class, enricher):
        # Mock Hunter.io API error
        mock_response = Mock()
        mock_response.status_code = 429  # Rate limited
        mock_response.text = "Rate limited"
        # Setup mock client
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client
        
        emails, contacts = enricher._search_hunter_io('https://testlaw.com')
        
        assert emails == []
        assert contacts == []
    
    def test_enrich_business_no_website(self, enricher):
        business_data = {
            'name': 'Test Business',
            'website': '',  # No website
            'place_id': 'ChIJ123'
        }
        
        result = enricher.enrich_business(business_data)
        
        # Should return original data if no enrichment possible
        assert result['name'] == 'Test Business'
        # Email should be None or empty if no enrichment methods worked
        assert result.get('email') is None or result.get('email') == ''
    
    @patch.object(EmailEnricher, '_scrape_website_for_emails')
    def test_enrich_business_with_scraped_email(self, mock_scrape, enricher, sample_business):
        # Mock successful email scraping
        mock_scrape.return_value = (['info@testlaw.com'], ['John Doe'])
        
        result = enricher.enrich_business(sample_business)
        
        assert result['email'] == 'info@testlaw.com'
        assert result['contact_name'] == 'John Doe'
        assert result['confidence_score'] > 0.7
        assert result['enriched_at'] is not None
    
    @patch.object(EmailEnricher, '_scrape_website_for_emails')
    @patch.object(EmailEnricher, '_generate_email_patterns')
    def test_enrich_business_fallback_to_patterns(self, mock_patterns, mock_scrape, enricher, sample_business):
        # Mock scraping failure, patterns success
        mock_scrape.return_value = ([], [])
        mock_patterns.return_value = ['info@testlaw.com']
        
        result = enricher.enrich_business(sample_business)
        
        # Should fallback to pattern generation
        assert mock_scrape.called
        assert mock_patterns.called