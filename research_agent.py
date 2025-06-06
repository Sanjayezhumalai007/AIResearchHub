import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import requests
from web_scraper import WebScraper
import google.generativeai as genai

class ResearchAgent:
    """AI Research Agent for comprehensive company analysis"""
    
    def __init__(self, gemini_api_key: str, tavily_api_key: str):
        self.gemini_api_key = gemini_api_key
        self.tavily_api_key = tavily_api_key
        self.web_scraper = WebScraper()
        
        # Configure Gemini AI
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def research_company(
        self, 
        website_url: str, 
        max_pages: int = 5,
        include_external: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Perform comprehensive company research
        
        Args:
            website_url: Target company website URL
            max_pages: Maximum number of pages to scrape
            include_external: Whether to include external research
            progress_callback: Function to call with progress updates
            
        Returns:
            Structured company profile dictionary
        """
        
        def update_progress(message: str, percentage: int):
            if progress_callback:
                progress_callback(message, percentage)
        
        try:
            # Step 1: Scrape website content
            update_progress("🔍 Scraping website content...", 30)
            scraped_data = self.web_scraper.scrape_website(website_url, max_pages)
            
            # Step 2: External research (if enabled)
            external_data = {}
            if include_external:
                update_progress("🌐 Conducting external research...", 50)
                external_data = self._perform_external_research(website_url, scraped_data.get('company_name', ''))
            
            # Step 3: Synthesize with AI
            update_progress("🤖 Synthesizing data with AI...", 70)
            company_profile = self._synthesize_with_ai(scraped_data, external_data)
            
            # Step 4: Finalize and structure
            update_progress("📊 Finalizing report...", 90)
            final_profile = self._finalize_profile(company_profile, website_url)
            
            update_progress("✅ Research completed!", 100)
            return final_profile
            
        except Exception as e:
            raise Exception(f"Research failed: {str(e)}")
    
    def _perform_external_research(self, website_url: str, company_name: str) -> Dict:
        """Perform external research using Tavily API"""
        
        if not company_name:
            # Extract company name from URL
            from urllib.parse import urlparse
            domain = urlparse(website_url).netloc
            company_name = domain.replace('www.', '').split('.')[0]
        
        try:
            # Tavily API search
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Search queries for comprehensive research
            queries = [
                f"{company_name} company funding valuation",
                f"{company_name} founders executives leadership",
                f"{company_name} products services business model",
                f"{company_name} headquarters location industry"
            ]
            
            external_results = {
                'funding_info': [],
                'leadership_info': [],
                'business_info': [],
                'company_info': []
            }
            
            for i, query in enumerate(queries):
                try:
                    payload = {
                        'api_key': self.tavily_api_key,
                        'query': query,
                        'search_depth': 'basic',
                        'include_answer': True,
                        'include_raw_content': False,
                        'max_results': 3
                    }
                    
                    response = requests.post(
                        'https://api.tavily.com/search',
                        headers=headers,
                        json=payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        result_key = list(external_results.keys())[i]
                        external_results[result_key] = data.get('results', [])
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"Tavily search failed for query '{query}': {str(e)}")
                    continue
            
            return external_results
            
        except Exception as e:
            print(f"External research failed: {str(e)}")
            return {}
    
    def _synthesize_with_ai(self, scraped_data: Dict, external_data: Dict) -> Dict:
        """Use Gemini AI to synthesize all collected data"""
        
        # Prepare the prompt
        prompt = self._create_synthesis_prompt(scraped_data, external_data)
        
        try:
            # Generate response with Gemini
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Clean up response if it contains markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Parse JSON
            company_profile = json.loads(response_text)
            return company_profile
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"AI synthesis failed: {str(e)}")
    
    def _create_synthesis_prompt(self, scraped_data: Dict, external_data: Dict) -> str:
        """Create a comprehensive prompt for AI synthesis"""
        
        prompt = f"""
You are an expert business analyst. Analyze the following company data and create a comprehensive company profile in JSON format.

SCRAPED WEBSITE DATA:
{json.dumps(scraped_data, indent=2)}

EXTERNAL RESEARCH DATA:
{json.dumps(external_data, indent=2)}

Based on this information, create a structured company profile with the following JSON schema:

{{
  "company_name": "string",
  "website_url": "string", 
  "linkedin_url": "string or null",
  "confidence_score": "High/Medium/Low",
  "summary": {{
    "about": "comprehensive company description",
    "tagline": "company tagline or mission statement"
  }},
  "company_details": {{
    "industry": "primary industry",
    "founded_year": "number or null",
    "company_type": "Public/Private/Startup/etc",
    "headquarters": "city, country/state"
  }},
  "people": {{
    "founders": ["list of founder names"],
    "key_executives": ["list of key executives with titles"]
  }},
  "offerings": {{
    "service_details": ["list of main products/services"],
    "pricing_model": "description of pricing approach"
  }},
  "valuation_and_revenue": {{
    "value": "string representation of value",
    "metric_type": "valuation/revenue/funding",
    "source": "source of information",
    "source_url": "url of source or null",
    "date_of_metric": "YYYY-MM-DD or null",
    "explanation": "brief explanation of the metric"
  }},
  "contact_info": {{
    "phone": "phone number or null",
    "email": "email address or null", 
    "contact_page_url": "contact page URL or null"
  }},
  "reference_links": {{
    "crunchbase_url": "crunchbase profile URL or null",
    "wikipedia_url": "wikipedia page URL or null",
    "other": ["array of other relevant URLs"]
  }},
  "last_updated": "YYYY-MM-DD"
}}

INSTRUCTIONS:
1. Extract and synthesize information from both scraped and external data
2. If information is missing or unclear, use null values
3. Provide a confidence score based on data quality and completeness
4. Ensure all extracted information is factual and verifiable
5. Use today's date for last_updated field
6. Return ONLY valid JSON, no additional text or explanations

JSON Response:
"""
        
        return prompt
    
    def _finalize_profile(self, profile: Dict, website_url: str) -> Dict:
        """Finalize the company profile with additional processing"""
        
        # Ensure required fields
        profile['website_url'] = website_url
        profile['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        # Set confidence score if not provided
        if 'confidence_score' not in profile:
            profile['confidence_score'] = 'Medium'
        
        # Ensure nested dictionaries exist
        required_sections = [
            'summary', 'company_details', 'people', 
            'offerings', 'contact_info', 'reference_links'
        ]
        
        for section in required_sections:
            if section not in profile:
                profile[section] = {}
        
        return profile
