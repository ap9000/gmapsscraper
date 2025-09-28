import httpx
import re
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)

# Try to enable Scrapling if available; fallback gracefully if not installed
try:
    from scrapling.fetchers import StealthyFetcher  # type: ignore
    SCRAPLING_AVAILABLE = True
    logger.debug("Scrapling available: advanced scraping enabled when configured")
except Exception:
    SCRAPLING_AVAILABLE = False
    logger.info("Scrapling not available; using traditional web scraping with proxies")

# Try to enable curl_cffi scraper
try:
    from curl_cffi_scraper import CurlCffiScraper
    CURL_CFFI_AVAILABLE = True
    logger.debug("curl_cffi available: enhanced browser impersonation enabled")
except Exception as e:
    try:
        # Try relative import as fallback
        from .curl_cffi_scraper import CurlCffiScraper
        CURL_CFFI_AVAILABLE = True
        logger.debug("curl_cffi available: enhanced browser impersonation enabled")
    except Exception as e2:
        CURL_CFFI_AVAILABLE = False
        logger.warning(f"curl_cffi not available: {e} / {e2}")


class EmailEnricher:
    def __init__(self, config, proxy_manager, db_manager):
        self.config = config
        self.proxy_manager = proxy_manager
        self.db = db_manager
        
        # Hunter.io setup
        self.hunter_api_key = config.get('apis.hunter.api_key')
        self.hunter_enabled = config.get('apis.hunter.enabled', False) and self.hunter_api_key
        self.hunter_cost_per_email = 0.049  # $0.049 per successful email find
        
        # Settings
        self.confidence_threshold = config.get('enrichment.email_confidence_threshold', 0.7)
        self.scrape_timeout = config.get('enrichment.website_scrape_timeout', 15)
        self.max_emails_per_business = config.get('enrichment.max_emails_per_business', 3)
        
        # Scrapling settings
        self.use_scrapling = config.get('enrichment.use_scrapling', True) and SCRAPLING_AVAILABLE
        self.scrapling_headless = config.get('enrichment.scrapling_headless', True)
        self.scrapling_solve_cloudflare = config.get('enrichment.scrapling_solve_cloudflare', True)
        
        # Email patterns
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+\sat\s[A-Za-z0-9.-]+\sdot\s[A-Z|a-z]{2,}\b'
        ]
        
        # curl_cffi scraper setup
        self.use_curl_cffi = config.get('enrichment.enable_curl_cffi', True) and CURL_CFFI_AVAILABLE
        logger.debug(f"curl_cffi setup: config_enabled={config.get('enrichment.enable_curl_cffi', True)}, available={CURL_CFFI_AVAILABLE}")
        if self.use_curl_cffi:
            self.curl_cffi_scraper = CurlCffiScraper(config, proxy_manager)
            logger.info("curl_cffi scraper initialized for enhanced email discovery")
        else:
            self.curl_cffi_scraper = None
            logger.info("curl_cffi scraper disabled")
        
        # Common contact page paths
        self.contact_paths = [
            '/contact', '/contact-us', '/contact.html', '/contact.php',
            '/about', '/about-us', '/team', '/staff',
            '/get-in-touch', '/reach-out', '/connect'
        ]
    
    def enrich_business(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich business with email and contact information
        Priority: 1) Scrapling (free), 2) curl_cffi (free), 3) httpx scraping (free), 4) Hunter.io (paid), 5) Pattern generation (free)
        """
        logger.info(f"Enriching business: {business_data.get('name', 'Unknown')}")
        
        # Initialize enrichment results
        enriched_data = business_data.copy()
        enrichment_results = {
            'emails_found': [],
            'contact_names': [],
            'confidence_scores': {},
            'methods_tried': [],
            'successful_method': None,  # Track which method found the email
            'method_results': {},  # Track results per method
            'success': False
        }
        
        website = business_data.get('website', '').strip()
        business_name = business_data.get('name', '').strip()
        
        # Method 1: Website Scraping (Free - Priority 1)
        if self.config.get('enrichment.enable_website_scraping', True) and website:
            try:
                logger.debug(f"Trying website scraping for {business_name}")
                enrichment_results['methods_tried'].append('website_scraping')
                
                emails, contacts = self._scrape_website_for_emails(website)
                enrichment_results['method_results']['website_scraping'] = len(emails)
                if emails:
                    enrichment_results['emails_found'].extend(emails)
                    enrichment_results['contact_names'].extend(contacts)
                    if not enrichment_results['successful_method']:
                        enrichment_results['successful_method'] = 'website_scraping'
                    logger.info(f"Website scraping found {len(emails)} emails for {business_name}")
                
            except Exception as e:
                logger.warning(f"Website scraping failed for {business_name}: {e}")
        
        # Method 2: curl_cffi Enhanced Scraping (Free - Priority 2)
        if (self.use_curl_cffi and 
            len(enrichment_results['emails_found']) < self.max_emails_per_business and
            website):
            try:
                logger.debug(f"Trying curl_cffi enhanced scraping for {business_name}")
                enrichment_results['methods_tried'].append('curl_cffi')
                
                cffi_emails, cffi_contacts = self.curl_cffi_scraper.scrape_website_for_emails(website)
                enrichment_results['method_results']['curl_cffi'] = len(cffi_emails)
                if cffi_emails:
                    enrichment_results['emails_found'].extend(cffi_emails)
                    enrichment_results['contact_names'].extend(cffi_contacts)
                    if not enrichment_results['successful_method']:
                        enrichment_results['successful_method'] = 'curl_cffi'
                    logger.info(f"curl_cffi found {len(cffi_emails)} emails for {business_name}")
                
            except Exception as e:
                logger.warning(f"curl_cffi scraping failed for {business_name}: {e}")
        
        # Method 3: Hunter.io Domain Search (Paid - Priority 3)
        if (self.hunter_enabled and 
            len(enrichment_results['emails_found']) < self.max_emails_per_business and
            website):
            try:
                logger.debug(f"Trying Hunter.io for {business_name}")
                enrichment_results['methods_tried'].append('hunter_io')
                
                hunter_emails, hunter_contacts = self._search_hunter_io(website)
                enrichment_results['method_results']['hunter_io'] = len(hunter_emails)
                if hunter_emails:
                    enrichment_results['emails_found'].extend(hunter_emails)
                    enrichment_results['contact_names'].extend(hunter_contacts)
                    if not enrichment_results['successful_method']:
                        enrichment_results['successful_method'] = 'hunter_io'
                    logger.info(f"Hunter.io found {len(hunter_emails)} emails for {business_name}")
                
            except Exception as e:
                logger.warning(f"Hunter.io search failed for {business_name}: {e}")
        
        # Method 4: Pattern Generation (Free - Priority 4)
        if (self.config.get('enrichment.enable_pattern_generation', True) and
            len(enrichment_results['emails_found']) < self.max_emails_per_business and
            website):
            try:
                logger.debug(f"Trying pattern generation for {business_name}")
                enrichment_results['methods_tried'].append('pattern_generation')
                
                pattern_emails = self._generate_email_patterns(website, business_name)
                enrichment_results['method_results']['pattern_generation'] = len(pattern_emails)
                if pattern_emails:
                    enrichment_results['emails_found'].extend(pattern_emails)
                    if not enrichment_results['successful_method']:
                        enrichment_results['successful_method'] = 'pattern_generation'
                    logger.info(f"Pattern generation created {len(pattern_emails)} emails for {business_name}")
                
            except Exception as e:
                logger.warning(f"Pattern generation failed for {business_name}: {e}")
        
        # Process and score results
        if enrichment_results['emails_found']:
            # Remove duplicates and validate
            unique_emails = list(set(enrichment_results['emails_found']))
            valid_emails = [email for email in unique_emails if self._validate_email(email)]
            
            # Calculate confidence scores
            scored_emails = []
            for email in valid_emails:
                confidence = self._calculate_email_confidence(
                    email, website, business_name, enrichment_results['methods_tried']
                )
                if confidence >= self.confidence_threshold:
                    scored_emails.append((email, confidence))
            
            if scored_emails:
                # Sort by confidence and take the best ones
                scored_emails.sort(key=lambda x: x[1], reverse=True)
                best_emails = scored_emails[:self.max_emails_per_business]
                
                # Update enriched data
                enriched_data['email'] = best_emails[0][0]  # Primary email
                enriched_data['confidence_score'] = best_emails[0][1]
                enriched_data['enriched_at'] = datetime.now().isoformat()
                enriched_data['enrichment_method'] = enrichment_results['successful_method']
                
                # Add contact name if found
                if enrichment_results['contact_names']:
                    enriched_data['contact_name'] = enrichment_results['contact_names'][0]
                
                # Store additional emails in metadata
                if len(best_emails) > 1:
                    enriched_data['additional_emails'] = [e[0] for e in best_emails[1:]]
                
                enrichment_results['success'] = True
                logger.info(f"Successfully enriched {business_name} with email: {best_emails[0][0]}")
        
        # Log enrichment attempt
        self._log_enrichment_attempt(business_data, enrichment_results)
        
        return enriched_data
    
    def _scrape_website_for_emails(self, website: str) -> Tuple[List[str], List[str]]:
        """Scrape website for email addresses using Scrapling or fallback methods"""
        emails = []
        contact_names = []
        
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        # Try Scrapling first (handles Cloudflare, JS, etc.)
        if self.use_scrapling:
            try:
                logger.debug(f"Using Scrapling for {website}")
                scrapling_emails, scrapling_contacts = self._scrape_with_scrapling(website)
                emails.extend(scrapling_emails)
                contact_names.extend(scrapling_contacts)
                
                # If Scrapling found emails, we might be done
                if emails:
                    logger.info(f"Scrapling found {len(emails)} emails for {website}")
                    return list(set(emails)), list(set(contact_names))
                
            except Exception as e:
                logger.warning(f"Scrapling failed for {website}: {e}")
        
        # Fallback to traditional scraping with proxies
        logger.debug(f"Using traditional scraping for {website}")
        proxies = self.proxy_manager.get_requests_proxy_dict()
        
        try:
            # First try the main page
            emails_main, contacts_main = self._scrape_page_for_emails(website, proxies)
            emails.extend(emails_main)
            contact_names.extend(contacts_main)
            
            # Then try common contact pages
            for path in self.contact_paths[:3]:  # Limit to 3 additional pages
                try:
                    contact_url = urljoin(website, path)
                    logger.debug(f"Checking contact page: {contact_url}")
                    
                    emails_contact, contacts_contact = self._scrape_page_for_emails(contact_url, proxies)
                    emails.extend(emails_contact)
                    contact_names.extend(contacts_contact)
                    
                    # Small delay between requests
                    time.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"Error scraping contact page {path}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"Error scraping website {website}: {e}")
        
        return list(set(emails)), list(set(contact_names))
    
    def _scrape_with_scrapling(self, website: str) -> Tuple[List[str], List[str]]:
        """Use Scrapling for advanced web scraping (bypasses Cloudflare, renders JS)"""
        emails = []
        contact_names = []
        
        try:
            logger.debug(f"Fetching {website} with Scrapling")
            
            # Fetch main page with Scrapling
            page = StealthyFetcher.fetch(
                website,
                headless=self.scrapling_headless,
                solve_cloudflare=self.scrapling_solve_cloudflare,
                timeout=self.scrape_timeout * 1000  # Convert seconds to milliseconds
            )
            
            if page and page.status == 200:
                # Extract emails from page content
                page_emails, page_contacts = self._extract_emails_from_scrapling_page(page)
                emails.extend(page_emails)
                contact_names.extend(page_contacts)
                
                # Try to find and scrape contact pages
                contact_links = []
                
                # Look for contact links using adaptive selectors
                try:
                    # Common contact link patterns
                    contact_selectors = [
                        'a[href*="contact"]',
                        'a[href*="about"]', 
                        'a[href*="team"]',
                        'a:contains("Contact")',
                        'a:contains("About")',
                        'a:contains("Team")'
                    ]
                    
                    for selector in contact_selectors:
                        try:
                            links = page.css(selector, adaptive=True)
                            for link in links[:2]:  # Limit to 2 links per type
                                href = link.get('href')
                                if href:
                                    full_url = urljoin(website, href)
                                    if full_url not in contact_links and len(contact_links) < 3:
                                        contact_links.append(full_url)
                        except Exception as e:
                            logger.debug(f"Error finding contact links with {selector}: {e}")
                            continue
                
                except Exception as e:
                    logger.debug(f"Error finding contact links: {e}")
                
                # Scrape contact pages
                for contact_url in contact_links:
                    try:
                        logger.debug(f"Scraping contact page: {contact_url}")
                        contact_page = StealthyFetcher.fetch(
                            contact_url,
                            headless=self.scrapling_headless,
                            timeout=10000  # Shorter timeout for contact pages (10 seconds in ms)
                        )
                        
                        if contact_page and contact_page.status == 200:
                            contact_emails, contact_contacts = self._extract_emails_from_scrapling_page(contact_page)
                            emails.extend(contact_emails)
                            contact_names.extend(contact_contacts)
                        
                        time.sleep(1)  # Small delay between pages
                        
                    except Exception as e:
                        logger.debug(f"Error scraping contact page {contact_url}: {e}")
                        continue
            
            else:
                logger.warning(f"Scrapling failed to fetch {website} - status: {page.status if page else 'None'}")
        
        except Exception as e:
            logger.error(f"Scrapling error for {website}: {e}")
            raise  # Re-raise to trigger fallback
        
        return emails, contact_names
    
    def _extract_emails_from_scrapling_page(self, page) -> Tuple[List[str], List[str]]:
        """Extract emails and contact names from a Scrapling page object"""
        emails = []
        contact_names = []
        
        try:
            # Get page text content
            text_content = page.text if (hasattr(page, 'text') and page.text) else page.get_all_text() if hasattr(page, 'get_all_text') else str(page)
            
            # Extract emails using regex patterns
            for pattern in self.email_patterns:
                found_emails = re.findall(pattern, text_content, re.IGNORECASE)
                emails.extend(found_emails)
            
            # Look for structured email data
            try:
                # Find mailto links
                mailto_links = page.css('a[href^="mailto:"]')
                for link in mailto_links:
                    href = link.get('href', '') if hasattr(link, 'get') else link.attrib.get('href', '')
                    if href.startswith('mailto:'):
                        email = href.replace('mailto:', '').split('?')[0]  # Remove query params
                        if email:
                            emails.append(email)
            except Exception as e:
                logger.debug(f"Error extracting mailto links: {e}")
            
            # Look for contact names near emails or in contact sections
            try:
                # Find contact sections
                contact_sections = page.css('[class*="contact"], [id*="contact"], [class*="team"], [id*="team"], [class*="about"], [id*="about"]')
                
                for section in contact_sections[:3]:  # Limit to 3 sections
                    section_text = section.text if hasattr(section, 'text') else section.get_all_text() if hasattr(section, 'get_all_text') else str(section)
                    
                    # Extract names using common patterns
                    name_patterns = [
                        r'(?:Contact|Manager|Director|Owner|CEO|President):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                        r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,\s*(?:Manager|Director|Owner|CEO))',
                        r'<[^>]*class[^>]*(?:name|contact-name|manager)[^>]*>([A-Z][a-z]+\s+[A-Z][a-z]+)</[^>]*>'
                    ]
                    
                    for pattern in name_patterns:
                        matches = re.findall(pattern, section_text, re.IGNORECASE)
                        contact_names.extend(matches)
            
            except Exception as e:
                logger.debug(f"Error extracting contact names: {e}")
            
            # Clean and validate emails
            cleaned_emails = []
            for email in emails:
                cleaned = self._clean_email(email)
                if cleaned and self._validate_email(cleaned):
                    cleaned_emails.append(cleaned)
            
            return cleaned_emails, contact_names[:5]  # Limit names to 5
            
        except Exception as e:
            logger.error(f"Error extracting data from Scrapling page: {e}")
            return [], []
    
    def _scrape_page_for_emails(self, url: str, proxies: Optional[Dict] = None) -> Tuple[List[str], List[str]]:
        """Scrape a single page for emails and contact names using httpx"""
        emails = []
        contact_names = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        # Configure httpx client for this request
        client_kwargs = {
            'headers': headers,
            'timeout': httpx.Timeout(self.scrape_timeout),
            'verify': False,  # Some business sites have SSL issues
        }
        
        # Add proxies if available - httpx expects proxies parameter directly
        if proxies:
            client_kwargs['proxies'] = proxies
        
        try:
            with httpx.Client(**client_kwargs) as client:
                response = client.get(url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text = soup.get_text()
                    
                    # Extract emails using regex patterns
                    for pattern in self.email_patterns:
                        found_emails = re.findall(pattern, text, re.IGNORECASE)
                        emails.extend(found_emails)
                    
                    # Look for potential contact names near emails
                    contact_names.extend(self._extract_contact_names(soup, emails))
                    
                    # Clean up emails
                    emails = [self._clean_email(email) for email in emails]
                    emails = [email for email in emails if email and self._validate_email(email)]
        except TypeError as e:
            if "unexpected keyword argument 'proxies'" in str(e):
                logger.debug(f"Proxy configuration not supported, trying without proxies for {url}")
                # Retry without proxies
                try:
                    client_kwargs_no_proxy = {k: v for k, v in client_kwargs.items() if k != 'proxies'}
                    with httpx.Client(**client_kwargs_no_proxy) as client:
                        response = client.get(url)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            text = soup.get_text()
                            
                            # Extract emails using regex patterns
                            for pattern in self.email_patterns:
                                found_emails = re.findall(pattern, text, re.IGNORECASE)
                                emails.extend(found_emails)
                            
                            # Look for potential contact names near emails
                            contact_names.extend(self._extract_contact_names(soup, emails))
                            
                            # Clean up emails
                            emails = [self._clean_email(email) for email in emails]
                            emails = [email for email in emails if email and self._validate_email(email)]
                except Exception as retry_e:
                    logger.debug(f"Retry without proxies also failed for {url}: {retry_e}")
            else:
                logger.debug(f"TypeError scraping page {url}: {e}")
        except Exception as e:
            logger.debug(f"Error scraping page {url}: {e}")
        
        return emails, contact_names
    
    def _search_hunter_io(self, website: str) -> Tuple[List[str], List[str]]:
        """Search Hunter.io for domain emails"""
        emails = []
        contact_names = []
        
        if not self.hunter_api_key:
            return emails, contact_names
        
        try:
            # Extract domain from website
            domain = urlparse(website).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Hunter.io Domain Search API
            url = "https://api.hunter.io/v2/domain-search"
            params = {
                'domain': domain,
                'api_key': self.hunter_api_key,
                'limit': self.max_emails_per_business
            }
            
            with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
                response = client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('data', {}).get('emails'):
                    for email_data in data['data']['emails']:
                        email = email_data.get('value')
                        if email and self._validate_email(email):
                            emails.append(email)
                            
                            # Extract contact name if available
                            first_name = email_data.get('first_name', '')
                            last_name = email_data.get('last_name', '')
                            if first_name or last_name:
                                contact_names.append(f"{first_name} {last_name}".strip())
                
                # Log the cost
                self.db.log_api_call(
                    'hunter_io', 
                    'domain-search', 
                    self.hunter_cost_per_email * len(emails),
                    success=True
                )
                
                logger.debug(f"Hunter.io found {len(emails)} emails for domain {domain}")
            
            else:
                logger.warning(f"Hunter.io API error: {response.status_code} - {response.text}")
                self.db.log_api_call('hunter_io', 'domain-search', 0, success=False, error_message=response.text)
        
        except Exception as e:
            logger.error(f"Hunter.io search error: {e}")
            self.db.log_api_call('hunter_io', 'domain-search', 0, success=False, error_message=str(e))
        
        return emails, contact_names
    
    def _generate_email_patterns(self, website: str, business_name: str) -> List[str]:
        """Generate common email patterns for the domain"""
        emails = []
        
        try:
            # Extract domain from website
            domain = urlparse(website).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Common business email patterns
            common_patterns = [
                f"info@{domain}",
                f"contact@{domain}",
                f"hello@{domain}",
                f"admin@{domain}",
                f"support@{domain}",
                f"sales@{domain}",
                f"office@{domain}"
            ]
            
            # Business name-based patterns
            if business_name:
                clean_name = re.sub(r'[^\w\s]', '', business_name.lower())
                name_parts = clean_name.split()
                
                if name_parts:
                    # Use first word of business name
                    first_word = name_parts[0][:10]  # Limit length
                    common_patterns.extend([
                        f"{first_word}@{domain}",
                        f"{first_word}.info@{domain}"
                    ])
            
            emails = [email for email in common_patterns if self._validate_email(email)]
        
        except Exception as e:
            logger.debug(f"Error generating email patterns: {e}")
        
        return emails
    
    def _extract_contact_names(self, soup: BeautifulSoup, emails: List[str]) -> List[str]:
        """Extract potential contact names from webpage"""
        names = []
        
        try:
            # Look for common contact patterns
            contact_patterns = [
                r'Contact:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Manager:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Owner:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Director:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            ]
            
            text = soup.get_text()
            for pattern in contact_patterns:
                matches = re.findall(pattern, text)
                names.extend(matches)
            
            # Look in specific HTML elements that commonly contain names
            name_selectors = [
                '.contact-name', '.manager', '.owner', '.director',
                '.team-member', '.staff-name', '.contact-person'
            ]
            
            for selector in name_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text().strip()
                    if text and len(text.split()) == 2:  # Likely a first+last name
                        names.append(text)
        
        except Exception as e:
            logger.debug(f"Error extracting contact names: {e}")
        
        return names[:3]  # Limit to 3 names
    
    def _clean_email(self, email: str) -> str:
        """Clean and normalize email address"""
        if not email:
            return ""
        
        # Remove common obfuscation
        email = email.replace(' at ', '@').replace(' dot ', '.')
        email = email.strip().lower()
        
        # Remove any trailing punctuation
        email = re.sub(r'[.,;!?]+$', '', email)
        
        return email
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        if not email or len(email) > 254:
            return False
        
        # Basic regex validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False
        
        # Exclude common false positives
        excluded_patterns = [
            r'@example\.',
            r'@test\.',
            r'@placeholder\.',
            r'@domain\.',
            r'@company\.',
            r'@yoursite\.',
            r'image@',
            r'photo@',
            r'picture@'
        ]
        
        for excluded in excluded_patterns:
            if re.search(excluded, email, re.IGNORECASE):
                return False
        
        return True
    
    def _calculate_email_confidence(self, email: str, website: str, business_name: str, methods_used: List[str]) -> float:
        """Calculate confidence score for an email address"""
        confidence = 0.0
        
        # Base confidence by method
        if 'website_scraping' in methods_used:
            confidence += 0.7  # High confidence for found emails
        if 'hunter_io' in methods_used:
            confidence += 0.9  # Very high confidence for verified emails
        if 'pattern_generation' in methods_used:
            confidence += 0.4  # Lower confidence for guessed emails
        
        # Domain matching bonus
        if website:
            domain = urlparse(website).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            if domain.lower() in email.lower():
                confidence += 0.2
        
        # Professional email patterns bonus
        professional_patterns = ['info@', 'contact@', 'hello@', 'admin@', 'office@']
        if any(pattern in email.lower() for pattern in professional_patterns):
            confidence += 0.1
        
        # Penalty for generic/suspicious patterns
        suspicious_patterns = ['noreply@', 'no-reply@', 'test@', 'fake@', 'admin@gmail.com']
        if any(pattern in email.lower() for pattern in suspicious_patterns):
            confidence -= 0.3
        
        return min(max(confidence, 0.0), 1.0)  # Clamp between 0 and 1
    
    def _log_enrichment_attempt(self, business_data: Dict[str, Any], results: Dict[str, Any]):
        """Log enrichment attempt for debugging and analytics"""
        try:
            log_entry = {
                'business_name': business_data.get('name'),
                'website': business_data.get('website'),
                'methods_tried': results['methods_tried'],
                'method_results': results.get('method_results', {}),
                'successful_method': results.get('successful_method'),
                'emails_found_count': len(results['emails_found']),
                'success': results['success'],
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Enrichment log: {json.dumps(log_entry)}")
            
            # Also log to database for analytics if needed
            if results['success']:
                logger.info(f"✅ {business_data.get('name')} enriched via {results.get('successful_method')}")
                
        except Exception as e:
            logger.debug(f"Error logging enrichment attempt: {e}")
