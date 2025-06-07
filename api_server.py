from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
import re
import json
from urllib.parse import urlparse
import google.generativeai as genai
from datetime import datetime
import time
import traceback

app = Flask(__name__)
CORS(app)

# Configure Gemini AI
GEMINI_API_KEY = "AIzaSyBrcXjJl74fJwtDLgVtZJ3UrEEjUCgaK1U"
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def fetch_with_timeout(url, timeout=25):
    """Fetch URL with timeout and proper headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; AIResearchAgent/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return response
    except requests.exceptions.Timeout:
        raise Exception(f"Request timed out after {timeout} seconds")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")

def extract_text_from_html(html):
    """Extract text content from HTML"""
    import re
    # Remove script and style elements
    text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text, flags=re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', ' ', text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_company_name(url, content):
    """Extract company name from URL and content"""
    try:
        url_obj = urlparse(url)
        domain = url_obj.hostname.replace('www.', '') if url_obj.hostname else ''
        domain_name = domain.split('.')[0] if domain else 'Unknown'
        
        # Look for title tags
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            if title and len(title) < 100:
                return title.split(' - ')[0].split(' | ')[0]
        
        return domain_name.capitalize()
    except:
        return 'Unknown Company'

def extract_emails(content):
    """Extract email addresses from content"""
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_regex, content)
    
    # Filter out common non-business emails
    excluded_domains = ['example.com', 'test.com', 'gmail.com', 'yahoo.com']
    return [email for email in emails if not any(excluded in email.lower() for excluded in excluded_domains)]

def extract_financial_metrics(text):
    """Extract financial metrics from text using regex patterns"""
    metrics = {
        'market_cap': [],
        'valuation': [],
        'funding': [],
        'revenue': []
    }
    
    # Market cap patterns (e.g., "$1.2B market cap", "market cap of $500M")
    market_cap_patterns = [
        r'\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)\s*(?:market\s*cap|market\s*capitalization)',
        r'market\s*cap(?:italization)?\s*(?:of|at)?\s*\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)',
        r'market\s*cap(?:italization)?\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)'
    ]
    
    # Valuation patterns (e.g., "valued at $1B", "valuation of $500M")
    valuation_patterns = [
        r'valued\s*at\s*\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)',
        r'valuation\s*(?:of|at)?\s*\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)',
        r'valuation\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)'
    ]
    
    # Funding patterns (e.g., "raised $50M", "funding of $100M")
    funding_patterns = [
        r'raised\s*\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)',
        r'funding\s*(?:of|at)?\s*\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)',
        r'funding\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)'
    ]
    
    # Revenue patterns (e.g., "revenue of $200M", "annual revenue $500M")
    revenue_patterns = [
        r'revenue\s*(?:of|at)?\s*\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)',
        r'annual\s*revenue\s*(?:of|at)?\s*\$(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)',
        r'revenue\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*(?:billion|b|million|m|trillion|t)'
    ]
    
    # Extract dates
    date_pattern = r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4}|\d{4}-\d{2}-\d{2}'
    
    for pattern in market_cap_patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            value = match.group(1)
            # Look for nearby date
            date_match = re.search(date_pattern, text[max(0, match.start()-100):match.end()+100])
            date = date_match.group(0) if date_match else None
            metrics['market_cap'].append({'value': value, 'date': date, 'context': text[max(0, match.start()-50):match.end()+50]})
    
    for pattern in valuation_patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            value = match.group(1)
            date_match = re.search(date_pattern, text[max(0, match.start()-100):match.end()+100])
            date = date_match.group(0) if date_match else None
            metrics['valuation'].append({'value': value, 'date': date, 'context': text[max(0, match.start()-50):match.end()+50]})
    
    for pattern in funding_patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            value = match.group(1)
            date_match = re.search(date_pattern, text[max(0, match.start()-100):match.end()+100])
            date = date_match.group(0) if date_match else None
            metrics['funding'].append({'value': value, 'date': date, 'context': text[max(0, match.start()-50):match.end()+50]})
    
    for pattern in revenue_patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            value = match.group(1)
            date_match = re.search(date_pattern, text[max(0, match.start()-100):match.end()+100])
            date = date_match.group(0) if date_match else None
            metrics['revenue'].append({'value': value, 'date': date, 'context': text[max(0, match.start()-50):match.end()+50]})
    
    return metrics

def perform_external_research(company_name, tavily_api_key):
    """Perform external research using Tavily API"""
    if not tavily_api_key:
        return {'error': 'Tavily API key not provided'}
    
    try:
        # More targeted queries to find financial data
        financial_queries = [
            f"{company_name} market cap stock price",
            f"{company_name} stock symbol ticker",
            f"{company_name} latest funding round valuation",
            f"{company_name} annual revenue financial results",
            f"{company_name} total funding raised",
            f"{company_name} financial statements annual report",
            f"{company_name} investor relations",
            f"{company_name} SEC filings"  # For public companies
        ]
        
        general_queries = [
            f"{company_name} founders executives leadership",
            f"{company_name} products services business model"
        ]
        
        results = {
            'financial_info': [],  # All financial results go here
            'leadership_info': [],
            'business_info': []
        }
        
        # Process all queries
        all_queries = financial_queries + general_queries
        result_keys = ['financial_info'] * len(financial_queries) + ['leadership_info', 'business_info']
        
        for i, query in enumerate(all_queries):
            try:
                response = requests.post('https://api.tavily.com/search', 
                    json={
                        'api_key': tavily_api_key,
                        'query': query,
                        'search_depth': 'basic',
                        'include_answer': True,
                        'include_raw_content': True,  # Get full content for better extraction
                        'max_results': 3
                    },
                    timeout=15
                )
                
                if response.ok:
                    data = response.json()
                    result_key = result_keys[i]
                    if data.get('results'):
                        # Extract financial metrics from each result
                        for result in data['results']:
                            if result.get('content'):
                                metrics = extract_financial_metrics(result['content'])
                                result['extracted_metrics'] = metrics
                        results[result_key].extend(data['results'])
            except:
                continue
        
        return results
    except Exception as e:
        return {'error': str(e)}

def calculate_industry_multiple(industry, growth_rate=None):
    """Calculate industry-specific valuation multiple"""
    # Base multiples by industry
    base_multiples = {
        'saas': 10.0,
        'fintech': 8.0,
        'ecommerce': 5.0,
        'healthtech': 7.0,
        'ai_ml': 12.0,
        'enterprise_software': 8.0,
        'consumer_tech': 6.0,
        'biotech': 15.0,
        'clean_tech': 9.0,
        'default': 5.0
    }
    
    # Growth rate adjustments
    growth_multipliers = {
        'high': 1.5,    # >50% YoY growth
        'medium': 1.2,  # 20-50% YoY growth
        'low': 1.0      # <20% YoY growth
    }
    
    # Normalize industry name
    industry = industry.lower().replace(' ', '_')
    if industry not in base_multiples:
        industry = 'default'
    
    # Get base multiple
    multiple = base_multiples[industry]
    
    # Apply growth rate adjustment if available
    if growth_rate:
        if growth_rate > 0.5:
            multiple *= growth_multipliers['high']
        elif growth_rate > 0.2:
            multiple *= growth_multipliers['medium']
        else:
            multiple *= growth_multipliers['low']
    
    return multiple

def extract_growth_rate(text):
    """Extract growth rate information from text"""
    growth_patterns = [
        r'(\d+(?:\.\d+)?)%\s*(?:year over year|yoy|annual) growth',
        r'grew\s*(?:by)?\s*(\d+(?:\.\d+)?)%',
        r'growth\s*(?:of|at)?\s*(\d+(?:\.\d+)?)%',
        r'increased\s*(?:by)?\s*(\d+(?:\.\d+)?)%'
    ]
    
    for pattern in growth_patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            try:
                return float(match.group(1)) / 100
            except:
                continue
    return None

def analyze_valuation_methods(financial_data, company_info):
    """Analyze company valuation using multiple methodologies"""
    valuation_methods = {
        'funding_based': None,
        'revenue_based': None,
        'comparable_based': None
    }
    
    # 1. Funding-based valuation
    if financial_data.get('valuation'):
        latest_valuation = max(
            financial_data['valuation'],
            key=lambda x: x['date'] if x.get('date') else '0000-00-00'
        )
        valuation_methods['funding_based'] = {
            'value': latest_valuation['value'],
            'date': latest_valuation['date'],
            'confidence': 'High',
            'explanation': f"Based on latest funding round valuation of ${latest_valuation['value']}M"
        }
    
    # 2. Revenue-based valuation
    if financial_data.get('revenue'):
        latest_revenue = max(
            financial_data['revenue'],
            key=lambda x: x['date'] if x.get('date') else '0000-00-00'
        )
        
        # Determine industry and growth rate
        industry = company_info.get('industry', 'default')
        growth_rate = extract_growth_rate(latest_revenue.get('context', ''))
        
        # Calculate multiple
        multiple = calculate_industry_multiple(industry, growth_rate)
        
        # Calculate valuation
        try:
            revenue_value = float(latest_revenue['value'])
            valuation = revenue_value * multiple
            
            valuation_methods['revenue_based'] = {
                'value': str(round(valuation, 2)),
                'date': latest_revenue['date'],
                'confidence': 'Medium',
                'explanation': f"Based on {industry} industry multiple of {multiple}x applied to ${revenue_value}M revenue"
            }
        except:
            pass
    
    # 3. Comparable company analysis
    if company_info.get('competitors'):
        competitor_valuations = []
        for competitor in company_info['competitors']:
            if competitor.get('valuation'):
                competitor_valuations.append({
                    'name': competitor['name'],
                    'valuation': competitor['valuation'],
                    'date': competitor.get('valuation_date'),
                    'size_ratio': competitor.get('size_ratio', 1.0)
                })
        
        if competitor_valuations:
            # Calculate weighted average based on recency and size ratio
            total_weight = 0
            weighted_sum = 0
            
            for comp in competitor_valuations:
                # Weight by recency (more recent = higher weight)
                date_weight = 1.0
                if comp.get('date'):
                    try:
                        days_old = (datetime.now() - datetime.strptime(comp['date'], '%Y-%m-%d')).days
                        date_weight = 1 / (1 + days_old/365)  # Decay over years
                    except:
                        pass
                
                # Weight by size ratio (closer size = higher weight)
                size_weight = 1 / (1 + abs(1 - comp['size_ratio']))
                
                total_weight += date_weight * size_weight
                weighted_sum += float(comp['valuation']) * date_weight * size_weight
            
            if total_weight > 0:
                avg_valuation = weighted_sum / total_weight
                valuation_methods['comparable_based'] = {
                    'value': str(round(avg_valuation, 2)),
                    'confidence': 'Medium',
                    'explanation': f"Based on weighted average of {len(competitor_valuations)} comparable companies"
                }
    
    return valuation_methods

def synthesize_with_ai(scraped_data, external_data, gemini_api_key):
    """Synthesize data with Gemini AI"""
    if not gemini_api_key:
        raise Exception('Gemini API key not provided')
    
    # Pre-process financial data to find the most recent and reliable metrics
    financial_metrics = {
        'market_cap': None,
        'valuation': None,
        'funding': None,
        'revenue': None
    }
    
    if isinstance(external_data, dict) and external_data.get('financial_info'):
        for result in external_data['financial_info']:
            if isinstance(result, dict) and result.get('extracted_metrics'):
                for metric_type, values in result['extracted_metrics'].items():
                    if values and (not financial_metrics[metric_type] or 
                                 (values[0].get('date') and 
                                  financial_metrics[metric_type].get('date') and 
                                  values[0]['date'] > financial_metrics[metric_type]['date'])):
                        financial_metrics[metric_type] = values[0]
    
    # Analyze valuation using multiple methodologies
    company_info = {
        'industry': None,
        'competitors': [],
        'growth_rate': None
    }
    
    # Extract company info from scraped data
    if isinstance(scraped_data, dict) and scraped_data.get('content'):
        # Look for industry mentions
        industry_patterns = [
            r'industry:\s*([^\.]+)',
            r'sector:\s*([^\.]+)',
            r'we are a\s*([^\.]+) company',
            r'leading\s*([^\.]+) company'
        ]
        
        for pattern in industry_patterns:
            match = re.search(pattern, scraped_data['content'].lower())
            if match:
                company_info['industry'] = match.group(1).strip()
                break
        
        # Extract growth rate
        company_info['growth_rate'] = extract_growth_rate(scraped_data['content'])
    
    # Analyze valuation methods
    valuation_methods = analyze_valuation_methods(financial_metrics, company_info)
    
    # Add pre-processed metrics and valuation analysis to the prompt
    prompt = f"""
You are an expert business analyst. Your goal is to create a factual and comprehensive company profile in JSON format based on the provided data.

SCRAPED WEBSITE DATA:
{json.dumps(scraped_data, indent=2)}

EXTERNAL RESEARCH DATA:
{json.dumps(external_data, indent=2)}

PRE-PROCESSED FINANCIAL METRICS:
{json.dumps(financial_metrics, indent=2)}

VALUATION ANALYSIS:
{json.dumps(valuation_methods, indent=2)}

Create a structured company profile using this exact JSON schema:

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
    "value": "string representation of value, e.g., '$1.2 Billion', '€500 Million'",
    "metric_type": "market_cap/valuation/total_funding/revenue/null",
    "source": "source of information, e.g., 'Yahoo Finance', 'Crunchbase'",
    "source_url": "url of source or null",
    "date_of_metric": "YYYY-MM-DD or null",
    "explanation": "CRUCIAL: The context for the value. E.g., 'Market cap as of YYYY-MM-DD.' or 'Valuation from Series C funding round.'",
    "confidence": "High/Medium/Low based on source reliability and data freshness",
    "methodology": "funding_based/revenue_based/comparable_based/blended",
    "supporting_metrics": {{
      "revenue": "revenue figure if available",
      "growth_rate": "annual growth rate if available",
      "industry_multiple": "multiple used for revenue-based valuation",
      "comparable_companies": ["list of comparable companies used"]
    }}
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

CRITICAL INSTRUCTIONS:

1. Valuation is a Priority: You MUST aggressively search the 'financial_info' in the external data to populate the 'valuation_and_revenue' section. Do not leave it null unless there is absolutely no mention of any financial metric.

2. Follow this Hierarchy for Value:
   - First Priority (The "Market Rate"): Look for the Market Capitalization if the company is public. This is the most important metric. Set 'metric_type' to 'market_cap'.
   - Second Priority: If not public or no market cap is found, look for the most recent Funding Valuation (e.g., "valued at $1B in its Series C"). Set 'metric_type' to 'valuation'.
   - Third Priority: If no specific valuation is found, use the Total Funding Amount Raised. Set 'metric_type' to 'total_funding'.
   - Last Resort: If none of the above are found, look for reported Annual Revenue. Set 'metric_type' to 'revenue'.

3. Explain the Value ("Show the Calculation"): The 'explanation' field is MANDATORY if a value is found. It must state exactly what the number represents and its context. For example:
   - "Market cap based on stock price on 2023-10-27."
   - "Valuation from a Series B funding round announced in May 2022."
   - "Total funding raised across all rounds as of 2023."
   - "Annual revenue reported in 2023 financial statements."

4. Set Confidence Level:
   - High: Official sources (SEC filings, company reports, major financial news)
   - Medium: Reliable news sources or industry reports
   - Low: Unverified sources or older data

5. Valuation Methodology:
   - Use the provided VALUATION ANALYSIS to determine the most appropriate methodology
   - If multiple methods are available, use a weighted average based on confidence levels
   - Include all supporting metrics in the supporting_metrics field
   - Set methodology to 'blended' if using multiple approaches

6. General Instructions:
   - Fill all other fields based on the combined data. Use null for missing information.
   - Set a confidence score based on data quality.
   - Use today's date for 'last_updated'.
   - Return ONLY valid JSON. No commentary or markdown.

JSON Response:"""

    max_retries = 3
    retry_delay = 20  # seconds
    last_error = None

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    top_k=1,
                    top_p=1,
                    max_output_tokens=2048,
                )
            )
            
            if not hasattr(response, 'text'):
                raise Exception("Invalid response format from Gemini API")
                
            response_text = response.text.strip()
            
            # Clean up the response
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Find the JSON object
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')
            
            if first_brace != -1 and last_brace != -1:
                response_text = response_text[first_brace:last_brace + 1]
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                last_error = f"Failed to parse AI response as JSON: {str(e)}"
                continue
                
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and "quota" in error_str.lower():
                if attempt < max_retries - 1:
                    print(f"Rate limit hit, waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    continue
            last_error = f"AI synthesis failed: {error_str}"
    
    # If we get here, all retries failed
    raise Exception(last_error or "AI synthesis failed after multiple attempts")

def calculate_industry_valuation(company_data):
    """Calculate industry-specific valuation based on company data"""
    try:
        # Extract required metrics
        revenue = None
        growth_rate = None
        industry = company_data.get('company_details', {}).get('industry', '').lower()
        
        # Get revenue from valuation data if available
        if company_data.get('valuation_and_revenue', {}).get('supporting_metrics', {}).get('revenue'):
            revenue_str = company_data['valuation_and_revenue']['supporting_metrics']['revenue']
            # Convert revenue string to number (handle formats like "$1.2M", "500K", etc.)
            revenue = convert_revenue_to_number(revenue_str)
        
        # Get growth rate
        if company_data.get('valuation_and_revenue', {}).get('supporting_metrics', {}).get('growth_rate'):
            growth_rate_str = company_data['valuation_and_revenue']['supporting_metrics']['growth_rate']
            growth_rate = float(growth_rate_str.strip('%')) / 100 if '%' in growth_rate_str else float(growth_rate_str)
        
        # Get industry multiple
        industry_multiple = calculate_industry_multiple(industry, growth_rate)
        
        # Calculate valuation
        valuation = None
        methodology = []
        
        if revenue and industry_multiple:
            # Revenue-based valuation
            revenue_valuation = revenue * industry_multiple
            methodology.append({
                'type': 'revenue_based',
                'value': revenue_valuation,
                'multiple': industry_multiple,
                'revenue': revenue
            })
        
        if growth_rate and revenue:
            # Growth-adjusted valuation
            growth_multiplier = 1 + (growth_rate * 2)  # Double the growth rate impact
            growth_valuation = revenue * industry_multiple * growth_multiplier
            methodology.append({
                'type': 'growth_adjusted',
                'value': growth_valuation,
                'growth_rate': growth_rate,
                'growth_multiplier': growth_multiplier
            })
        
        # Calculate final valuation (weighted average of methodologies)
        if methodology:
            total_weight = 0
            weighted_sum = 0
            
            for method in methodology:
                if method['type'] == 'revenue_based':
                    weight = 0.6  # Higher weight for revenue-based
                else:
                    weight = 0.4  # Lower weight for growth-adjusted
                
                total_weight += weight
                weighted_sum += method['value'] * weight
            
            final_valuation = weighted_sum / total_weight if total_weight > 0 else None
            
            return {
                'valuation': format_currency(final_valuation),
                'methodology': methodology,
                'confidence': 'High' if revenue and industry_multiple else 'Medium',
                'supporting_metrics': {
                    'revenue': format_currency(revenue) if revenue else None,
                    'growth_rate': f"{growth_rate*100:.1f}%" if growth_rate else None,
                    'industry_multiple': industry_multiple,
                    'industry': industry
                }
            }
        
        return {
            'error': 'Insufficient data for valuation calculation',
            'required_metrics': {
                'revenue': bool(revenue),
                'industry': bool(industry),
                'growth_rate': bool(growth_rate)
            }
        }
        
    except Exception as e:
        return {
            'error': f'Valuation calculation failed: {str(e)}',
            'details': str(e)
        }

def convert_revenue_to_number(revenue_str):
    """Convert revenue string to number"""
    try:
        # Remove currency symbols and whitespace
        revenue_str = revenue_str.strip().replace('$', '').replace('€', '').replace('£', '').strip()
        
        # Handle different formats
        if 'B' in revenue_str or 'billion' in revenue_str.lower():
            return float(revenue_str.replace('B', '').replace('billion', '').strip()) * 1e9
        elif 'M' in revenue_str or 'million' in revenue_str.lower():
            return float(revenue_str.replace('M', '').replace('million', '').strip()) * 1e6
        elif 'K' in revenue_str or 'thousand' in revenue_str.lower():
            return float(revenue_str.replace('K', '').replace('thousand', '').strip()) * 1e3
        else:
            return float(revenue_str)
    except:
        return None

def format_currency(value):
    """Format number as currency string"""
    if value is None:
        return None
    if value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    elif value >= 1e3:
        return f"${value/1e3:.2f}K"
    else:
        return f"${value:.2f}"

def generate_company_report(company_data, research_data, valuation_data):
    """Generate comprehensive company report"""
    try:
        # Validate input data
        if not isinstance(company_data, dict):
            company_data = {}
        if not isinstance(research_data, dict):
            research_data = {}
        if not isinstance(valuation_data, dict):
            valuation_data = {}

        # Initialize report structure
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'version': '1.0',
                'data_points': 0,
                'ai_tokens_used': 0,
                'pages_processed': 0
            },
            'company_profile': {
                'basic_info': {},
                'financial_metrics': {},
                'market_analysis': {},
                'competitor_analysis': {},
                'risk_assessment': {},
                'growth_metrics': {}
            },
            'valuation_analysis': {},
            'data_quality': {
                'confidence_scores': {},
                'data_sources': [],
                'verification_status': {}
            }
        }
        
        # Extract and organize basic information
        if isinstance(company_data, dict):
            report['company_profile']['basic_info'] = {
                'name': company_data.get('company_name'),
                'website': company_data.get('website_url'),
                'industry': company_data.get('company_details', {}).get('industry') if isinstance(company_data.get('company_details'), dict) else None,
                'founded_year': company_data.get('company_details', {}).get('founded_year') if isinstance(company_data.get('company_details'), dict) else None,
                'headquarters': company_data.get('company_details', {}).get('headquarters') if isinstance(company_data.get('company_details'), dict) else None,
                'company_type': company_data.get('company_details', {}).get('company_type') if isinstance(company_data.get('company_details'), dict) else None
            }
        
        # Process financial metrics
        if isinstance(company_data, dict) and isinstance(company_data.get('valuation_and_revenue'), dict):
            financial_data = company_data['valuation_and_revenue']
            report['company_profile']['financial_metrics'] = {
                'current_valuation': financial_data.get('value'),
                'valuation_methodology': financial_data.get('methodology'),
                'revenue': financial_data.get('supporting_metrics', {}).get('revenue') if isinstance(financial_data.get('supporting_metrics'), dict) else None,
                'growth_rate': financial_data.get('supporting_metrics', {}).get('growth_rate') if isinstance(financial_data.get('supporting_metrics'), dict) else None,
                'industry_multiple': financial_data.get('supporting_metrics', {}).get('industry_multiple') if isinstance(financial_data.get('supporting_metrics'), dict) else None
            }
        
        # Add valuation analysis
        if isinstance(valuation_data, dict):
            report['valuation_analysis'] = {
                'calculated_valuation': valuation_data.get('valuation'),
                'methodology_breakdown': valuation_data.get('methodology'),
                'confidence_level': valuation_data.get('confidence'),
                'supporting_metrics': valuation_data.get('supporting_metrics') if isinstance(valuation_data.get('supporting_metrics'), dict) else {}
            }
        
        # Process market analysis
        if isinstance(research_data, dict) and isinstance(research_data.get('market_info'), dict):
            market_info = research_data['market_info']
            report['company_profile']['market_analysis'] = {
                'market_size': market_info.get('market_size'),
                'market_growth': market_info.get('market_growth'),
                'market_trends': market_info.get('market_trends'),
                'key_players': market_info.get('key_players')
            }
        
        # Process competitor analysis
        if isinstance(research_data, dict) and isinstance(research_data.get('competitor_info'), dict):
            competitor_info = research_data['competitor_info']
            report['company_profile']['competitor_analysis'] = {
                'direct_competitors': competitor_info.get('direct_competitors'),
                'competitive_advantages': competitor_info.get('competitive_advantages'),
                'market_position': competitor_info.get('market_position')
            }
        
        # Calculate data quality metrics
        report['data_quality']['confidence_scores'] = {
            'financial_data': calculate_confidence_score(company_data.get('valuation_and_revenue') if isinstance(company_data, dict) else None),
            'market_data': calculate_confidence_score(research_data.get('market_info') if isinstance(research_data, dict) else None),
            'competitor_data': calculate_confidence_score(research_data.get('competitor_info') if isinstance(research_data, dict) else None),
            'overall': calculate_overall_confidence(report)
        }
        
        # Track data sources
        report['data_quality']['data_sources'] = [
            {'type': 'company_website', 'url': company_data.get('website_url') if isinstance(company_data, dict) else None},
            {'type': 'market_research', 'source': 'Tavily API'},
            {'type': 'valuation_analysis', 'source': 'Industry Multiples'}
        ]
        
        # Calculate metadata
        report['metadata']['data_points'] = count_data_points(report)
        report['metadata']['pages_processed'] = 1  # Base website + external sources
        report['metadata']['ai_tokens_used'] = estimate_ai_tokens(report)
        
        return report
        
    except Exception as e:
        return {
            'error': f'Report generation failed: {str(e)}',
            'details': str(e),
            'input_data': {
                'company_data_type': str(type(company_data)),
                'research_data_type': str(type(research_data)),
                'valuation_data_type': str(type(valuation_data))
            }
        }

def calculate_confidence_score(data):
    """Calculate confidence score for data section"""
    if not data or not isinstance(data, dict):
        return 'Low'
    
    # Count non-null values
    non_null_count = sum(1 for v in data.values() if v is not None)
    total_fields = len(data)
    
    if total_fields == 0:
        return 'Low'
    
    if non_null_count / total_fields >= 0.8:
        return 'High'
    elif non_null_count / total_fields >= 0.5:
        return 'Medium'
    return 'Low'

def calculate_overall_confidence(report):
    """Calculate overall confidence score"""
    if not isinstance(report, dict) or 'data_quality' not in report or 'confidence_scores' not in report['data_quality']:
        return 'Low'
        
    confidence_scores = report['data_quality']['confidence_scores']
    if not isinstance(confidence_scores, dict):
        return 'Low'
        
    score_map = {'High': 3, 'Medium': 2, 'Low': 1}
    
    valid_scores = [score_map[score] for score in confidence_scores.values() 
                   if score != 'overall' and score in score_map]
    
    if not valid_scores:
        return 'Low'
        
    avg_score = sum(valid_scores) / len(valid_scores)
    
    if avg_score >= 2.5:
        return 'High'
    elif avg_score >= 1.5:
        return 'Medium'
    return 'Low'

def count_data_points(report):
    """Count total data points in report"""
    if not isinstance(report, dict) or 'company_profile' not in report:
        return 0
        
    def count_dict(d):
        if not isinstance(d, dict):
            return 0
        return sum(1 for v in d.values() if v is not None)
    
    total = 0
    for section in report['company_profile'].values():
        if isinstance(section, dict):
            total += count_dict(section)
    return total

def estimate_ai_tokens(report):
    """Estimate AI tokens used in report generation"""
    if not isinstance(report, dict):
        return 0
    # Rough estimate: 1 token per 4 characters
    report_str = json.dumps(report)
    return len(report_str) // 4

def calculate_industry_specific_valuation(company_data):
    """Calculate industry-specific valuation with detailed methodology"""
    try:
        # Initialize valuation result
        valuation_result = {
            'calculated_value': None,
            'methodology': [],
            'confidence': 'Low',
            'supporting_metrics': {},
            'industry_analysis': {},
            'calculation_steps': []
        }
        
        # Extract required metrics
        revenue = None
        growth_rate = None
        industry = company_data.get('company_details', {}).get('industry', '').lower()
        
        # Get revenue from valuation data
        if company_data.get('valuation_and_revenue', {}).get('supporting_metrics', {}).get('revenue'):
            revenue_str = company_data['valuation_and_revenue']['supporting_metrics']['revenue']
            revenue = convert_revenue_to_number(revenue_str)
            valuation_result['calculation_steps'].append({
                'step': 'Revenue Extraction',
                'value': revenue_str,
                'converted_value': revenue
            })
        
        # Get growth rate
        if company_data.get('valuation_and_revenue', {}).get('supporting_metrics', {}).get('growth_rate'):
            growth_rate_str = company_data['valuation_and_revenue']['supporting_metrics']['growth_rate']
            growth_rate = float(growth_rate_str.strip('%')) / 100 if '%' in growth_rate_str else float(growth_rate_str)
            valuation_result['calculation_steps'].append({
                'step': 'Growth Rate Extraction',
                'value': growth_rate_str,
                'converted_value': growth_rate
            })
        
        # Get industry multiple
        industry_multiple = calculate_industry_multiple(industry)
        valuation_result['calculation_steps'].append({
            'step': 'Industry Multiple Selection',
            'industry': industry,
            'multiple': industry_multiple
        })
        
        # Calculate base valuation
        if revenue and industry_multiple:
            base_valuation = revenue * industry_multiple
            valuation_result['methodology'].append({
                'type': 'revenue_based',
                'value': base_valuation,
                'calculation': f"{revenue} * {industry_multiple}",
                'weight': 0.6
            })
            valuation_result['calculation_steps'].append({
                'step': 'Base Valuation',
                'calculation': f"{revenue} * {industry_multiple}",
                'result': base_valuation
            })
        
        # Calculate growth-adjusted valuation
        if growth_rate and revenue:
            growth_multiplier = 1 + (growth_rate * 2)
            growth_valuation = revenue * industry_multiple * growth_multiplier
            valuation_result['methodology'].append({
                'type': 'growth_adjusted',
                'value': growth_valuation,
                'calculation': f"{revenue} * {industry_multiple} * {growth_multiplier}",
                'weight': 0.4
            })
            valuation_result['calculation_steps'].append({
                'step': 'Growth Adjustment',
                'calculation': f"Base * (1 + {growth_rate*2})",
                'result': growth_valuation
            })
        
        # Calculate final weighted valuation
        if valuation_result['methodology']:
            total_weight = 0
            weighted_sum = 0
            
            for method in valuation_result['methodology']:
                total_weight += method['weight']
                weighted_sum += method['value'] * method['weight']
            
            final_valuation = weighted_sum / total_weight if total_weight > 0 else None
            
            valuation_result['calculated_value'] = format_currency(final_valuation)
            valuation_result['confidence'] = 'High' if revenue and industry_multiple else 'Medium'
            valuation_result['supporting_metrics'] = {
                'revenue': format_currency(revenue) if revenue else None,
                'growth_rate': f"{growth_rate*100:.1f}%" if growth_rate else None,
                'industry_multiple': industry_multiple,
                'industry': industry
            }
            
            valuation_result['calculation_steps'].append({
                'step': 'Final Weighted Valuation',
                'calculation': 'Weighted average of methodologies',
                'result': final_valuation
            })
        
        return valuation_result
        
    except Exception as e:
        return {
            'error': f'Valuation calculation failed: {str(e)}',
            'details': str(e)
        }

@app.route('/api/calculate-industry-valuation', methods=['POST', 'OPTIONS'])
def calculate_industry_valuation_endpoint():
    """Calculate industry-specific valuation endpoint"""
    # Enable CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return '', 200, headers
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400, headers
        
        # Calculate valuation
        result = calculate_industry_specific_valuation(data)
        
        if 'error' in result:
            return jsonify(result), 400, headers
        
        return jsonify(result), 200, headers
        
    except Exception as e:
        return jsonify({
            'error': f'Valuation calculation failed: {str(e)}',
            'details': str(e)
        }), 500, headers

@app.route('/api/calculate-valuation', methods=['POST', 'OPTIONS'])
def calculate_valuation():
    """Calculate industry-specific valuation"""
    # Enable CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return '', 200, headers
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400, headers
        
        # Calculate valuation
        result = calculate_industry_valuation(data)
        
        if 'error' in result:
            return jsonify(result), 400, headers
        
        return jsonify(result), 200, headers
        
    except Exception as e:
        return jsonify({
            'error': f'Valuation calculation failed: {str(e)}',
            'details': str(e)
        }), 500, headers

@app.route('/api/research-agent', methods=['POST', 'OPTIONS'])
def research_agent():
    """Handle research agent API requests"""
    # Enable CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return '', 200, headers
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400, headers
        
        website_url = data.get('websiteUrl')
        if not website_url:
            return jsonify({'error': 'Website URL is required'}), 400, headers
        
        # Get API keys
        gemini_api_key = "AIzaSyBrcXjJl74fJwtDLgVtZJ3UrEEjUCgaK1U"
        tavily_api_key = "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"
        
        if not gemini_api_key:
            return jsonify({'error': 'Gemini API key not configured'}), 400, headers
        
        # Scrape website
        try:
            response = fetch_with_timeout(website_url)
            if not response.ok:
                return jsonify({'error': f'Failed to fetch website: {response.status_code}'}), 500, headers
            
            html_content = response.text
            text_content = extract_text_from_html(html_content)
            
            scraped_data = {
                'url': website_url,
                'company_name': extract_company_name(website_url, html_content),
                'content': text_content,
                'emails': extract_emails(text_content)
            }
            
        except Exception as e:
            return jsonify({'error': f'Website scraping failed: {str(e)}'}), 500, headers
        
        # Perform external research
        external_data = {}
        if tavily_api_key:
            try:
                external_data = perform_external_research(scraped_data['company_name'], tavily_api_key)
            except Exception as e:
                print(f"External research failed: {str(e)}")
                external_data = {'error': str(e)}
        
        # Synthesize with AI
        try:
            company_profile = synthesize_with_ai(scraped_data, external_data, gemini_api_key)
            return jsonify(company_profile), 200, headers
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and "quota" in error_msg.lower():
                return jsonify({
                    'error': 'API rate limit exceeded. Please try again in a few minutes.',
                    'details': error_msg
                }), 429, headers
            return jsonify({'error': f'AI analysis failed: {error_msg}'}), 500, headers
            
    except Exception as e:
        return jsonify({'error': f'Research failed: {str(e)}'}), 500, headers

@app.route('/api/test')
def test_api():
    """Test endpoint to check API status"""
    gemini_key = os.getenv('GEMINI_API_KEY')
    tavily_key = os.getenv('TAVILY_API_KEY')
    
    return jsonify({
        'status': 'API is running',
        'gemini_configured': bool(gemini_key),
        'tavily_configured': bool(tavily_key),
        'timestamp': '2024-01-20'
    })

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/generate-report', methods=['POST', 'OPTIONS'])
def generate_report():
    """Generate comprehensive company report"""
    # Enable CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return '', 200, headers
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400, headers
        
        # Extract and validate input data
        company_data = data.get('company_data', {})
        research_data = data.get('research_data', {})
        valuation_data = data.get('valuation_data', {})
        
        # Generate report
        report = generate_company_report(company_data, research_data, valuation_data)
        
        if 'error' in report:
            return jsonify(report), 400, headers
        
        return jsonify(report), 200, headers
        
    except Exception as e:
        return jsonify({
            'error': f'Report generation failed: {str(e)}',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500, headers

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
