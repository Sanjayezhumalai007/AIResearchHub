# AI Research Agent - Netlify Deployment

A powerful AI Research Agent that analyzes websites and generates comprehensive company profiles using web scraping, external APIs, and Gemini AI.

## Features

- **Web Scraping**: Extracts content from company websites
- **External Research**: Uses Tavily API for additional data gathering
- **AI Analysis**: Gemini AI synthesizes data into structured company profiles
- **Modern UI**: Responsive interface with progress tracking
- **Export**: Download results as JSON reports

## Deployment to Netlify

### 1. Upload Files
Upload all files to your Netlify site:
- `index.html` - Main application interface
- `script.js` - Frontend JavaScript functionality
- `netlify/functions/research-agent.js` - Serverless function for backend processing
- `netlify.toml` - Netlify configuration

### 2. Configure Environment Variables

In your Netlify dashboard, go to **Site settings → Environment variables** and add:

- **GEMINI_API_KEY**: Your Google Gemini API key
  - Get from: https://aistudio.google.com/app/apikey
  - Free tier available

- **TAVILY_API_KEY**: Your Tavily API key  
  - Get from: https://tavily.com
  - Required for external research

### 3. Deploy and Test

After deployment:
1. Visit your Netlify URL
2. Enter a company website URL (e.g., https://stripe.com)
3. Click "Start Research"
4. View the generated company profile

## Troubleshooting

### Common Issues

**"Gemini API key not configured"**
- Add GEMINI_API_KEY to Netlify environment variables
- Redeploy the site after adding variables

**"502 Bad Gateway"**
- Check Netlify function logs in dashboard
- Ensure environment variables are set correctly
- Verify API keys are valid

**"Function not found"**
- Ensure `netlify/functions/research-agent.js` is uploaded
- Check `netlify.toml` configuration is present

### API Key Setup

1. **Gemini API Key**:
   - Visit https://aistudio.google.com/app/apikey
   - Sign in with Google account
   - Create new API key
   - Copy and add to Netlify environment variables

2. **Tavily API Key**:
   - Visit https://tavily.com
   - Sign up for account
   - Get API key from dashboard
   - Add to Netlify environment variables

## Architecture

- **Frontend**: Static HTML/CSS/JavaScript
- **Backend**: Netlify serverless function
- **APIs**: Gemini AI for analysis, Tavily for research
- **Hosting**: Netlify static hosting with serverless functions

## Output Format

The research agent generates structured company profiles including:
- Company summary and tagline
- Industry and company details
- Key people and executives
- Products and services
- Financial information
- Contact details
- Reference links

Results are displayed in an organized interface and can be exported as JSON.