"""
Enhanced web scraping using curl_cffi for better bot detection avoidance
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
import random
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Try to import curl_cffi with graceful fallback
try:
    from curl_cffi import requests
    from curl_cffi.requests import Session
    CURL_CFFI_AVAILABLE = True
    logger.debug("curl_cffi available: enhanced scraping enabled")
except Exception as e:
    CURL_CFFI_AVAILABLE = False
    logger.info(f"curl_cffi not available: {e}")


class CurlCffiScraper:
    """
    Enhanced web scraper using curl_cffi for better anti-bot evasion
    """
    
    def __init__(self, config, proxy_manager):
        self.config = config
        self.proxy_manager = proxy_manager
        self.enabled = CURL_CFFI_AVAILABLE and config.get('enrichment.enable_curl_cffi', True)
        
        # Scraping settings
        self.timeout = config.get('enrichment.website_scrape_timeout', 15)
        self.max_retries = config.get('enrichment.curl_cffi_max_retries', 2)
        
        # Browser impersonation options (using stable, widely supported versions)
        self.browser_versions = [
            'chrome110',
            'chrome116', 
            'chrome120',
            'safari15_5'
        ]
        
        # Session management
        self._sessions: Dict[str, Session] = {}
        self._session_uses: Dict[str, int] = {}
        self.max_session_uses = 10  # Rotate sessions after N uses
        
        logger.info(f"CurlCffiScraper initialized: {'enabled' if self.enabled else 'disabled'}")
    
    @contextmanager
    def get_session(self, domain: str = None):
        """
        Get or create a session with rotating browser impersonation
        """
        if not self.enabled:
            raise RuntimeError("curl_cffi is not available")
        
        session_key = domain or 'default'
        
        # Create new session if needed or if current one is overused
        if (session_key not in self._sessions or 
            self._session_uses.get(session_key, 0) >= self.max_session_uses):
            
            if session_key in self._sessions:
                self._sessions[session_key].close()
            
            # Select random browser version for this session
            browser_version = random.choice(self.browser_versions)
            
            # Create session with browser impersonation
            session = Session(impersonate=browser_version)
            
            # Set additional headers to mimic real browser
            session.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            })
            
            # Configure proxy if available
            proxies = self.proxy_manager.get_requests_proxy_dict()
            if proxies:
                # curl_cffi expects proxy format: "http://user:pass@host:port"
                if 'http' in proxies:
                    proxy_url = proxies['http']
                    session.proxies = {'http': proxy_url, 'https': proxy_url}
            
            self._sessions[session_key] = session
            self._session_uses[session_key] = 0
            
            logger.debug(f"Created new curl_cffi session for {session_key} with {browser_version}")
        
        session = self._sessions[session_key]
        self._session_uses[session_key] += 1
        
        try:
            yield session
        finally:
            pass  # Keep session alive for reuse
    
    def scrape_url_for_emails(self, url: str) -> Tuple[List[str], List[str]]:
        """
        Scrape a single URL for emails and contact names using curl_cffi
        Returns: (emails, contact_names)
        """
        if not self.enabled:
            raise RuntimeError("curl_cffi is not available")
        
        emails = []
        contact_names = []
        
        try:
            domain = urlparse(url).netloc
            
            with self.get_session(domain) as session:
                logger.debug(f"Scraping {url} with curl_cffi session")
                
                # Add random delay to seem more human
                time.sleep(random.uniform(0.5, 2.0))
                
                for attempt in range(self.max_retries):
                    try:
                        response = session.get(
                            url, 
                            timeout=self.timeout,
                            verify=False,  # Some business sites have SSL issues
                            allow_redirects=True,
                            max_redirects=5
                        )
                        
                        if response.status_code == 200:
                            # Extract emails and names from response
                            page_emails, page_names = self._extract_data_from_html(
                                response.text, url
                            )
                            emails.extend(page_emails)
                            contact_names.extend(page_names)
                            
                            logger.debug(f"curl_cffi found {len(page_emails)} emails on {url}")
                            break
                            
                        elif response.status_code in [403, 429]:
                            logger.warning(f"Access denied ({response.status_code}) for {url}, attempt {attempt + 1}")
                            if attempt < self.max_retries - 1:
                                # Wait longer and try with new session
                                time.sleep(2 ** attempt)
                                # Force new session for next attempt
                                if domain in self._sessions:
                                    self._sessions[domain].close()
                                    del self._sessions[domain]
                                    self._session_uses[domain] = self.max_session_uses
                            else:
                                logger.warning(f"Failed to access {url} after {self.max_retries} attempts")
                        else:
                            logger.debug(f"HTTP {response.status_code} for {url}")
                            break
                            
                    except Exception as e:
                        logger.warning(f"curl_cffi error for {url} (attempt {attempt + 1}): {e}")
                        if attempt < self.max_retries - 1:
                            time.sleep(1)
                        else:
                            raise
        
        except Exception as e:
            logger.error(f"curl_cffi scraping failed for {url}: {e}")
            raise
        
        return list(set(emails)), list(set(contact_names))
    
    def scrape_website_for_emails(self, website: str, max_pages: int = 4) -> Tuple[List[str], List[str]]:
        """
        Scrape website and common contact pages for emails using curl_cffi
        """
        if not self.enabled:
            raise RuntimeError("curl_cffi is not available")
        
        emails = []
        contact_names = []
        
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        # List of pages to check
        pages_to_check = [website]
        
        # Add common contact page paths
        contact_paths = [
            '/contact', '/contact-us', '/contact.html', '/contact.php',
            '/about', '/about-us', '/team', '/staff'
        ]
        
        for path in contact_paths[:max_pages-1]:  # Leave room for main page
            contact_url = urljoin(website, path)
            pages_to_check.append(contact_url)
        
        # Scrape each page
        for i, url in enumerate(pages_to_check):
            try:
                logger.debug(f"Checking page {i+1}/{len(pages_to_check)}: {url}")
                
                page_emails, page_names = self.scrape_url_for_emails(url)
                emails.extend(page_emails)
                contact_names.extend(page_names)
                
                # Small delay between pages
                if i < len(pages_to_check) - 1:
                    time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.debug(f"Error scraping {url}: {e}")
                continue
        
        return list(set(emails)), list(set(contact_names))
    
    def _extract_data_from_html(self, html_content: str, url: str) -> Tuple[List[str], List[str]]:
        """Extract emails and contact names from HTML content"""
        from bs4 import BeautifulSoup
        import re
        
        emails = []
        contact_names = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get all text content
            text_content = soup.get_text()
            
            # Email extraction patterns
            email_patterns = [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                r'\b[A-Za-z0-9._%+-]+\sat\s[A-Za-z0-9.-]+\sdot\s[A-Z|a-z]{2,}\b'
            ]
            
            # Extract emails using patterns
            for pattern in email_patterns:
                found_emails = re.findall(pattern, text_content, re.IGNORECASE)
                emails.extend(found_emails)
            
            # Find mailto links
            mailto_links = soup.find_all('a', href=lambda x: x and x.startswith('mailto:'))
            for link in mailto_links:
                href = link.get('href', '')
                email = href.replace('mailto:', '').split('?')[0]  # Remove query params
                if email:
                    emails.append(email)
            
            # Look for contact names in structured data
            # Find elements that might contain contact names
            contact_elements = soup.find_all(['div', 'section', 'p'], 
                                           class_=lambda x: x and any(
                                               keyword in x.lower() 
                                               for keyword in ['contact', 'team', 'staff', 'about']
                                           ))
            
            for element in contact_elements[:5]:  # Limit to prevent performance issues
                element_text = element.get_text()
                
                # Extract names using patterns
                name_patterns = [
                    r'(?:Contact|Manager|Director|Owner|CEO|President):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,\s*(?:Manager|Director|Owner|CEO))',
                ]
                
                for pattern in name_patterns:
                    matches = re.findall(pattern, element_text, re.IGNORECASE)
                    contact_names.extend(matches)
            
            # Clean and validate emails
            cleaned_emails = []
            for email in emails:
                email = email.strip().lower()
                if self._validate_email(email):
                    cleaned_emails.append(email)
            
            return cleaned_emails[:10], contact_names[:5]  # Limit results
            
        except Exception as e:
            logger.error(f"Error extracting data from HTML: {e}")
            return [], []
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def cleanup(self):
        """Clean up sessions"""
        for session in self._sessions.values():
            try:
                session.close()
            except:
                pass
        self._sessions.clear()
        self._session_uses.clear()
    
    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()