from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
import re
import json
from urllib.parse import urlparse
import google.generativeai as genai
from datetime import datetime

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
    
    if external_data.get('financial_info'):
        for result in external_data['financial_info']:
            if result.get('extracted_metrics'):
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
    if scraped_data.get('content'):
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
        
        response_text = response.text.strip()
        
        # Clean up the response
        response_text = re.sub(r'^```(?:json)?\s*', '', response_text, flags=re.IGNORECASE)
        response_text = re.sub(r'\s*```$', '', response_text, flags=re.IGNORECASE)
        response_text = response_text.replace('`', '')
        
        # Find JSON object
        first_brace = response_text.find('{')
        last_brace = response_text.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            response_text = response_text[first_brace:last_brace + 1]
        
        # Additional cleanup
        response_text = re.sub(r'\n\s*\n', '\n', response_text)
        response_text = response_text.replace('\\`', '`')
        response_text = response_text.replace('\\\\', '\\')
        
        try:
            company_profile = json.loads(response_text)
            return company_profile
        except json.JSONDecodeError as e:
            # Try additional cleanup
            cleaned_text = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', response_text)
            cleaned_text = cleaned_text.replace('\\n', '\\\\n')
            cleaned_text = cleaned_text.replace('\\"', '\\"')
            cleaned_text = cleaned_text.replace("\\'", "'")
            
            try:
                company_profile = json.loads(cleaned_text)
                return company_profile
            except json.JSONDecodeError:
                raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
        
    except Exception as e:
        raise Exception(f"AI synthesis failed: {str(e)}")

@app.route('/api/research-agent', methods=['POST', 'OPTIONS'])
def research_agent():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        print("Received research request")
        
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'Invalid JSON in request body'}), 400
        
        print(f"Request data: {data}")
        
        website_url = data.get('websiteUrl')
        max_pages = data.get('maxPages', 5)
        include_external = data.get('includeExternal', True)
        
        if not website_url:
            print("No website URL provided")
            return jsonify({'error': 'Website URL is required'}), 400
        
        print(f"Processing URL: {website_url}")
        
        # Get API keys from environment
        gemini_api_key = "AIzaSyBrcXjJl74fJwtDLgVtZJ3UrEEjUCgaK1U"
        tavily_api_key = "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"
        
        print(f"API Keys - Gemini: {'✓' if gemini_api_key else '✗'}, Tavily: {'✓' if tavily_api_key else '✗'}")
        
        if not gemini_api_key:
            error_msg = 'Gemini API key not configured. Please add GEMINI_API_KEY to your Secrets in the Tools panel.'
            print(f"Error: {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        # Step 1: Scrape website content
        print("Step 1: Fetching website content...")
        try:
            response = fetch_with_timeout(website_url)
            if not response.ok:
                error_msg = f'Website returned error: {response.status_code}'
                print(f"Website fetch error: {error_msg}")
                return jsonify({'error': error_msg}), 500
            print("Website content fetched successfully")
        except Exception as e:
            error_msg = f'Failed to fetch website: {str(e)}'
            print(f"Website fetch exception: {error_msg}")
            return jsonify({'error': error_msg}), 500
        
        # Check content length
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 5000000:  # 5MB limit
            return jsonify({'error': 'Website content too large to process'}), 500
        
        html_content = response.text
        
        # Limit HTML content size
        if len(html_content) > 1000000:
            html_content = html_content[:1000000]
        
        text_content = extract_text_from_html(html_content)
        
        scraped_data = {
            'base_url': website_url,
            'company_name': extract_company_name(website_url, html_content),
            'content': text_content[:8000],  # Limit for better analysis
            'emails': extract_emails(text_content),
            'scraped_pages_count': 1
        }
        
        # Step 2: External research
        external_data = {}
        if include_external and tavily_api_key:
            try:
                external_data = perform_external_research(scraped_data['company_name'], tavily_api_key)
            except Exception as e:
                external_data = {'error': f'External research failed: {str(e)}'}
        else:
            external_data = {'error': 'External research skipped - no Tavily API key'}
        
        # Step 3: AI synthesis
        print("Step 3: AI synthesis...")
        try:
            company_profile = synthesize_with_ai(scraped_data, external_data, gemini_api_key)
            print("AI synthesis completed successfully")
        except Exception as e:
            error_msg = f'AI analysis failed: {str(e)}'
            print(f"AI synthesis error: {error_msg}")
            return jsonify({'error': error_msg}), 500
        
        # Step 4: Finalize profile
        print("Step 4: Finalizing profile...")
        company_profile['website_url'] = website_url
        company_profile['last_updated'] = '2024-01-20'  # Current date
        
        if 'confidence_score' not in company_profile:
            company_profile['confidence_score'] = 'Medium'
        
        print("Research completed successfully")
        return jsonify(company_profile)
        
    except Exception as e:
        error_msg = f'Research failed: {str(e)}'
        print(f"Unexpected error: {error_msg}")
        return jsonify({'error': error_msg}), 500

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
