import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import trafilatura
import re
from typing import Dict, List, Set
import time

class WebScraper:
    """Web scraper for extracting company information from websites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_website(self, base_url: str, max_pages: int = 5) -> Dict:
        """
        Scrape website for company information
        
        Args:
            base_url: The main website URL
            max_pages: Maximum number of pages to scrape
            
        Returns:
            Dictionary containing scraped company information
        """
        
        try:
            # Get the main page first
            main_content = self.get_website_text_content(base_url)
            
            # Find relevant pages to scrape
            relevant_urls = self._find_relevant_pages(base_url, max_pages)
            
            # Scrape content from all relevant pages
            all_content = [main_content]
            
            for url in relevant_urls[:max_pages-1]:  # -1 because we already have main page
                try:
                    content = self.get_website_text_content(url)
                    if content:
                        all_content.append(content)
                    time.sleep(1)  # Rate limiting
                except:
                    continue
            
            # Extract structured information
            structured_data = self._extract_structured_info(base_url, all_content)
            
            return structured_data
            
        except Exception as e:
            raise Exception(f"Website scraping failed: {str(e)}")
    
    def get_website_text_content(self, url: str) -> str:
        """
        Extract main text content from a website URL using trafilatura
        
        Args:
            url: Website URL to scrape
            
        Returns:
            Clean text content from the website
        """
        try:
            # Download the page
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return ""
            
            # Extract text content
            text = trafilatura.extract(downloaded)
            return text or ""
            
        except Exception as e:
            print(f"Failed to extract content from {url}: {str(e)}")
            return ""
    
    def _find_relevant_pages(self, base_url: str, max_pages: int) -> List[str]:
        """Find relevant pages to scrape (about, team, products, etc.)"""
        
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Keywords for relevant pages
            relevant_keywords = [
                'about', 'team', 'company', 'leadership', 'founders',
                'products', 'services', 'solutions', 'contact',
                'careers', 'investors', 'press', 'news'
            ]
            
            # Find all links
            links = soup.find_all('a', href=True)
            relevant_urls = set()
            
            base_domain = urlparse(base_url).netloc
            
            for link in links:
                href = link.get('href')
                if not href:
                    continue
                
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, href)
                parsed_url = urlparse(full_url)
                
                # Only consider same-domain links
                if parsed_url.netloc != base_domain:
                    continue
                
                # Check if URL contains relevant keywords
                url_text = (href + ' ' + link.get_text()).lower()
                
                for keyword in relevant_keywords:
                    if keyword in url_text and len(relevant_urls) < max_pages:
                        relevant_urls.add(full_url)
                        break
            
            return list(relevant_urls)
            
        except Exception as e:
            print(f"Failed to find relevant pages: {str(e)}")
            return []
    
    def _extract_structured_info(self, base_url: str, content_list: List[str]) -> Dict:
        """Extract structured information from scraped content"""
        
        # Combine all content
        full_content = '\n\n'.join(filter(None, content_list))
        
        # Extract basic information
        structured_info = {
            'base_url': base_url,
            'company_name': self._extract_company_name(base_url, full_content),
            'content': full_content,
            'emails': self._extract_emails(full_content),
            'phone_numbers': self._extract_phone_numbers(full_content),
            'social_links': self._extract_social_links(base_url),
            'scraped_pages_count': len(content_list)
        }
        
        return structured_info
    
    def _extract_company_name(self, url: str, content: str) -> str:
        """Extract company name from URL and content"""
        
        # Try to extract from URL domain
        domain = urlparse(url).netloc.replace('www.', '')
        domain_name = domain.split('.')[0]
        
        # Look for company name patterns in content
        lines = content.split('\n')[:20]  # Check first 20 lines
        
        for line in lines:
            line = line.strip()
            if len(line) > 3 and len(line) < 50:
                # Simple heuristic: if line looks like a company name
                if any(word in line.lower() for word in ['inc', 'corp', 'ltd', 'llc', 'company']):
                    return line
        
        # Fallback to domain name
        return domain_name.title()
    
    def _extract_emails(self, content: str) -> List[str]:
        """Extract email addresses from content"""
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        
        # Filter out common non-business emails
        filtered_emails = []
        excluded_domains = ['example.com', 'test.com', 'gmail.com', 'yahoo.com']
        
        for email in emails:
            domain = email.split('@')[1].lower()
            if not any(excluded in domain for excluded in excluded_domains):
                filtered_emails.append(email)
        
        return list(set(filtered_emails))
    
    def _extract_phone_numbers(self, content: str) -> List[str]:
        """Extract phone numbers from content"""
        
        # Phone number patterns
        phone_patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',  # US format
            r'\+?[0-9]{1,3}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}',  # International
        ]
        
        phone_numbers = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, content)
            phone_numbers.extend(matches)
        
        # Clean and deduplicate
        cleaned_numbers = []
        for number in phone_numbers:
            # Remove extra formatting
            cleaned = re.sub(r'[^\d+]', '', number)
            if len(cleaned) >= 10:  # Valid phone number length
                cleaned_numbers.append(number.strip())
        
        return list(set(cleaned_numbers))
    
    def _extract_social_links(self, base_url: str) -> Dict[str, str]:
        """Extract social media links from the website"""
        
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            social_links = {}
            social_platforms = {
                'linkedin': 'linkedin.com',
                'twitter': 'twitter.com',
                'facebook': 'facebook.com',
                'instagram': 'instagram.com',
                'youtube': 'youtube.com'
            }
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                if not href:
                    continue
                
                for platform, domain in social_platforms.items():
                    if domain in href.lower():
                        social_links[platform] = href
                        break
            
            return social_links
            
        except Exception as e:
            print(f"Failed to extract social links: {str(e)}")
            return {}
