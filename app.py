import streamlit as st
import json
import pandas as pd
from datetime import datetime
import os
from research_agent import ResearchAgent
from utils import validate_url, format_company_profile

# Page configuration
st.set_page_config(
    page_title="AI Research Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'research_results' not in st.session_state:
    st.session_state.research_results = None
if 'research_in_progress' not in st.session_state:
    st.session_state.research_in_progress = False

def main():
    st.title("🔍 AI Research Agent")
    st.markdown("### Comprehensive Company Profile Analysis")
    st.markdown("Enter a company website URL to generate a detailed research report using AI-powered analysis.")
    
    # Sidebar for API configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key inputs
        gemini_api_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Get your API key from Google AI Studio"
        )
        
        tavily_api_key = st.text_input(
            "Tavily API Key",
            value=os.getenv("TAVILY_API_KEY", ""),
            type="password",
            help="Get your API key from Tavily.com"
        )
        
        st.markdown("---")
        
        # Research settings
        st.subheader("Research Settings")
        max_pages = st.slider("Max pages to scrape", 1, 10, 5)
        include_external = st.checkbox("Include external research", value=True)
        confidence_threshold = st.slider("Confidence threshold", 0.0, 1.0, 0.7)
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        url_input = st.text_input(
            "Website URL",
            placeholder="https://example.com",
            help="Enter the company website URL to analyze"
        )
    
    with col2:
        research_button = st.button(
            "🚀 Start Research",
            type="primary",
            disabled=st.session_state.research_in_progress
        )
    
    # Validate inputs
    if research_button:
        if not url_input:
            st.error("Please enter a website URL")
            return
        
        if not validate_url(url_input):
            st.error("Please enter a valid URL")
            return
        
        if not gemini_api_key:
            st.error("Please provide a Gemini API key")
            return
        
        if not tavily_api_key:
            st.error("Please provide a Tavily API key")
            return
        
        # Start research
        st.session_state.research_in_progress = True
        st.rerun()
    
    # Research process
    if st.session_state.research_in_progress:
        research_placeholder = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Initialize research agent
            agent = ResearchAgent(
                gemini_api_key=gemini_api_key,
                tavily_api_key=tavily_api_key
            )
            
            # Update progress
            status_text.text("🌐 Initializing web scraper...")
            progress_bar.progress(10)
            
            # Perform research
            status_text.text("🔍 Scraping website content...")
            progress_bar.progress(30)
            
            research_results = agent.research_company(
                url_input,
                max_pages=max_pages,
                include_external=include_external,
                progress_callback=lambda msg, pct: (
                    status_text.text(msg),
                    progress_bar.progress(pct)
                )
            )
            
            # Complete
            progress_bar.progress(100)
            status_text.text("✅ Research completed!")
            
            # Store results
            st.session_state.research_results = research_results
            st.session_state.research_in_progress = False
            
            # Clear progress indicators
            research_placeholder.empty()
            progress_bar.empty()
            status_text.empty()
            
            st.success("Research completed successfully!")
            st.rerun()
            
        except Exception as e:
            st.session_state.research_in_progress = False
            st.error(f"Research failed: {str(e)}")
            progress_bar.empty()
            status_text.empty()
    
    # Display results
    if st.session_state.research_results:
        display_results(st.session_state.research_results)

def display_results(results):
    st.markdown("---")
    st.header("📊 Research Results")
    
    # Company overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Company",
            results.get('company_name', 'Unknown'),
            help="Company name identified from website"
        )
    
    with col2:
        st.metric(
            "Confidence Score",
            results.get('confidence_score', 'N/A'),
            help="AI confidence in the analysis"
        )
    
    with col3:
        st.metric(
            "Last Updated",
            results.get('last_updated', 'N/A'),
            help="When this analysis was performed"
        )
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Summary", "🏢 Company Details", "👥 People", "💼 Offerings", "📈 Financials"
    ])
    
    with tab1:
        st.subheader("Company Summary")
        summary = results.get('summary', {})
        if summary.get('about'):
            st.write(summary['about'])
        if summary.get('tagline'):
            st.info(f"**Tagline:** {summary['tagline']}")
    
    with tab2:
        st.subheader("Company Details")
        details = results.get('company_details', {})
        
        col1, col2 = st.columns(2)
        with col1:
            if details.get('industry'):
                st.write(f"**Industry:** {details['industry']}")
            if details.get('founded_year'):
                st.write(f"**Founded:** {details['founded_year']}")
        
        with col2:
            if details.get('company_type'):
                st.write(f"**Type:** {details['company_type']}")
            if details.get('headquarters'):
                st.write(f"**Headquarters:** {details['headquarters']}")
    
    with tab3:
        st.subheader("Key People")
        people = results.get('people', {})
        
        if people.get('founders'):
            st.write("**Founders:**")
            for founder in people['founders']:
                st.write(f"• {founder}")
        
        if people.get('key_executives'):
            st.write("**Key Executives:**")
            for exec in people['key_executives']:
                st.write(f"• {exec}")
    
    with tab4:
        st.subheader("Products & Services")
        offerings = results.get('offerings', {})
        
        if offerings.get('service_details'):
            st.write("**Services:**")
            for service in offerings['service_details']:
                st.write(f"• {service}")
        
        if offerings.get('pricing_model'):
            st.info(f"**Pricing Model:** {offerings['pricing_model']}")
    
    with tab5:
        st.subheader("Financial Information")
        valuation = results.get('valuation_and_revenue', {})
        
        if valuation:
            col1, col2 = st.columns(2)
            with col1:
                if valuation.get('value'):
                    st.metric("Value", f"${valuation['value']}")
                if valuation.get('metric_type'):
                    st.write(f"**Type:** {valuation['metric_type']}")
            
            with col2:
                if valuation.get('date_of_metric'):
                    st.write(f"**Date:** {valuation['date_of_metric']}")
                if valuation.get('source'):
                    st.write(f"**Source:** {valuation['source']}")
    
    # Contact Information
    st.subheader("📞 Contact Information")
    contact = results.get('contact_info', {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if contact.get('email'):
            st.write(f"**Email:** {contact['email']}")
    
    with col2:
        if contact.get('phone'):
            st.write(f"**Phone:** {contact['phone']}")
    
    with col3:
        if contact.get('contact_page_url'):
            st.link_button("Contact Page", contact['contact_page_url'])
    
    # Reference Links
    if results.get('reference_links'):
        st.subheader("🔗 Reference Links")
        links = results['reference_links']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if links.get('linkedin_url'):
                st.link_button("LinkedIn", links['linkedin_url'])
        
        with col2:
            if links.get('crunchbase_url'):
                st.link_button("Crunchbase", links['crunchbase_url'])
        
        with col3:
            if links.get('wikipedia_url'):
                st.link_button("Wikipedia", links['wikipedia_url'])
    
    # Download section
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Download JSON
        json_data = json.dumps(results, indent=2)
        st.download_button(
            label="📥 Download JSON Report",
            data=json_data,
            file_name=f"{results.get('company_name', 'company')}_report_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
    
    with col2:
        # Clear results
        if st.button("🗑️ Clear Results"):
            st.session_state.research_results = None
            st.rerun()

if __name__ == "__main__":
    main()
