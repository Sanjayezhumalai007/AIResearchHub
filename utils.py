import re
from urllib.parse import urlparse
from typing import Dict, Any
import json

def validate_url(url: str) -> bool:
    """
    Validate if a given string is a valid URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def format_company_profile(profile: Dict[str, Any]) -> str:
    """
    Format company profile dictionary into a readable string
    
    Args:
        profile: Company profile dictionary
        
    Returns:
        Formatted string representation
    """
    
    formatted_text = []
    
    # Company header
    company_name = profile.get('company_name', 'Unknown Company')
    formatted_text.append(f"=== {company_name.upper()} ===\n")
    
    # Basic info
    website = profile.get('website_url', 'N/A')
    formatted_text.append(f"Website: {website}")
    
    confidence = profile.get('confidence_score', 'N/A')
    formatted_text.append(f"Confidence Score: {confidence}")
    
    # Summary
    summary = profile.get('summary', {})
    if summary:
        formatted_text.append("\n--- SUMMARY ---")
        if summary.get('about'):
            formatted_text.append(f"About: {summary['about']}")
        if summary.get('tagline'):
            formatted_text.append(f"Tagline: {summary['tagline']}")
    
    # Company details
    details = profile.get('company_details', {})
    if details:
        formatted_text.append("\n--- COMPANY DETAILS ---")
        for key, value in details.items():
            if value:
                formatted_text.append(f"{key.replace('_', ' ').title()}: {value}")
    
    # People
    people = profile.get('people', {})
    if people:
        formatted_text.append("\n--- KEY PEOPLE ---")
        if people.get('founders'):
            formatted_text.append("Founders:")
            for founder in people['founders']:
                formatted_text.append(f"  • {founder}")
        
        if people.get('key_executives'):
            formatted_text.append("Key Executives:")
            for exec in people['key_executives']:
                formatted_text.append(f"  • {exec}")
    
    # Offerings
    offerings = profile.get('offerings', {})
    if offerings:
        formatted_text.append("\n--- PRODUCTS & SERVICES ---")
        if offerings.get('service_details'):
            for service in offerings['service_details']:
                formatted_text.append(f"• {service}")
        
        if offerings.get('pricing_model'):
            formatted_text.append(f"Pricing Model: {offerings['pricing_model']}")
    
    # Financial info
    valuation = profile.get('valuation_and_revenue', {})
    if valuation and valuation.get('value'):
        formatted_text.append("\n--- FINANCIAL INFORMATION ---")
        value = valuation.get('value', 'N/A')
        metric_type = valuation.get('metric_type', 'value')
        formatted_text.append(f"{metric_type.title()}: ${value}")
        
        if valuation.get('source'):
            formatted_text.append(f"Source: {valuation['source']}")
        if valuation.get('date_of_metric'):
            formatted_text.append(f"Date: {valuation['date_of_metric']}")
    
    # Contact info
    contact = profile.get('contact_info', {})
    if contact:
        formatted_text.append("\n--- CONTACT INFORMATION ---")
        for key, value in contact.items():
            if value:
                formatted_text.append(f"{key.replace('_', ' ').title()}: {value}")
    
    # Reference links
    links = profile.get('reference_links', {})
    if links:
        formatted_text.append("\n--- REFERENCE LINKS ---")
        for platform, url in links.items():
            if url and platform != 'other':
                formatted_text.append(f"{platform.title()}: {url}")
        
        if links.get('other'):
            for other_link in links['other']:
                formatted_text.append(f"Other: {other_link}")
    
    # Last updated
    last_updated = profile.get('last_updated', 'N/A')
    formatted_text.append(f"\nLast Updated: {last_updated}")
    
    return '\n'.join(formatted_text)

def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.,!?;:\-\(\)\'\"@]', '', text)
    
    # Trim
    text = text.strip()
    
    return text

def extract_domain_from_url(url: str) -> str:
    """
    Extract domain name from URL
    
    Args:
        url: Full URL
        
    Returns:
        Domain name without www
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return ""

def is_business_email(email: str) -> bool:
    """
    Check if an email appears to be a business email
    
    Args:
        email: Email address to check
        
    Returns:
        True if likely business email, False otherwise
    """
    if not email or '@' not in email:
        return False
    
    # Common personal email domains
    personal_domains = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'aol.com', 'icloud.com', 'protonmail.com'
    ]
    
    domain = email.split('@')[1].lower()
    return domain not in personal_domains

def format_json_for_display(data: Dict[str, Any]) -> str:
    """
    Format JSON data for display with proper indentation
    
    Args:
        data: Dictionary to format
        
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, indent=2, ensure_ascii=False)

def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Truncate text to specified length with ellipsis
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length].rsplit(' ', 1)[0] + "..."

def parse_company_size(text: str) -> str:
    """
    Parse company size information from text
    
    Args:
        text: Text containing potential company size info
        
    Returns:
        Standardized company size category
    """
    text_lower = text.lower()
    
    # Size patterns
    if any(term in text_lower for term in ['startup', 'small', '1-10', '2-10']):
        return "Startup/Small (1-50 employees)"
    elif any(term in text_lower for term in ['medium', '50-200', '100-500']):
        return "Medium (50-500 employees)"
    elif any(term in text_lower for term in ['large', '500+', '1000+', 'enterprise']):
        return "Large (500+ employees)"
    else:
        return "Unknown"
