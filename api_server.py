
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import re
import json
from urllib.parse import urlparse
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Configure Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
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

def perform_external_research(company_name, tavily_api_key):
    """Perform external research using Tavily API"""
    if not tavily_api_key:
        return {'error': 'Tavily API key not provided'}
    
    try:
        queries = [
            f"{company_name} company funding valuation",
            f"{company_name} founders executives leadership",
            f"{company_name} products services business model"
        ]
        
        results = {
            'funding_info': [],
            'leadership_info': [],
            'business_info': []
        }
        
        for i, query in enumerate(queries):
            try:
                response = requests.post('https://api.tavily.com/search', 
                    json={
                        'api_key': tavily_api_key,
                        'query': query,
                        'search_depth': 'basic',
                        'include_answer': True,
                        'include_raw_content': False,
                        'max_results': 3
                    },
                    timeout=15
                )
                
                if response.ok:
                    data = response.json()
                    result_key = list(results.keys())[i]
                    results[result_key] = data.get('results', [])
            except:
                continue
        
        return results
    except Exception as e:
        return {'error': str(e)}

def synthesize_with_ai(scraped_data, external_data, gemini_api_key):
    """Synthesize data with Gemini AI"""
    if not gemini_api_key:
        raise Exception('Gemini API key not provided')
    
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
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON in request body'}), 400
        
        website_url = data.get('websiteUrl')
        max_pages = data.get('maxPages', 5)
        include_external = data.get('includeExternal', True)
        
        if not website_url:
            return jsonify({'error': 'Website URL is required'}), 400
        
        # Get API keys from environment
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        
        if not gemini_api_key:
            return jsonify({'error': 'Gemini API key not configured. Please add GEMINI_API_KEY to your environment variables.'}), 400
        
        # Step 1: Scrape website content
        try:
            response = fetch_with_timeout(website_url)
            if not response.ok:
                return jsonify({'error': f'Website returned error: {response.status_code}'}), 500
        except Exception as e:
            return jsonify({'error': f'Failed to fetch website: {str(e)}'}), 500
        
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
        try:
            company_profile = synthesize_with_ai(scraped_data, external_data, gemini_api_key)
        except Exception as e:
            return jsonify({'error': f'AI analysis failed: {str(e)}'}), 500
        
        # Step 4: Finalize profile
        company_profile['website_url'] = website_url
        company_profile['last_updated'] = '2024-01-20'  # Current date
        
        if 'confidence_score' not in company_profile:
            company_profile['confidence_score'] = 'Medium'
        
        return jsonify(company_profile)
        
    except Exception as e:
        return jsonify({'error': f'Research failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
