const https = require('https');
const http = require('http');
const { URL } = require('url');

// Helper function to make HTTP requests
function makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const lib = urlObj.protocol === 'https:' ? https : http;
        
        const requestOptions = {
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname + urlObj.search,
            method: options.method || 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                ...options.headers
            }
        };

        const req = lib.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    headers: res.headers,
                    body: data
                });
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        if (options.body) {
            req.write(options.body);
        }

        req.end();
    });
}

// Extract text content from HTML
function extractTextFromHTML(html) {
    // Simple HTML tag removal - basic implementation
    let text = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
    text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
    text = text.replace(/<[^>]*>/g, ' ');
    text = text.replace(/\s+/g, ' ').trim();
    return text;
}

// Extract company name from URL and content
function extractCompanyName(url, content) {
    try {
        const urlObj = new URL(url);
        const domain = urlObj.hostname.replace('www.', '');
        const domainName = domain.split('.')[0];
        
        // Look for title tags or h1 elements in content
        const titleMatch = content.match(/<title[^>]*>([^<]+)<\/title>/i);
        if (titleMatch) {
            const title = titleMatch[1].trim();
            if (title.length > 0 && title.length < 100) {
                return title.split(' - ')[0].split(' | ')[0];
            }
        }
        
        return domainName.charAt(0).toUpperCase() + domainName.slice(1);
    } catch (e) {
        return 'Unknown Company';
    }
}

// Extract emails from content
function extractEmails(content) {
    const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
    const emails = content.match(emailRegex) || [];
    
    // Filter out common non-business emails
    const excludedDomains = ['example.com', 'test.com', 'gmail.com', 'yahoo.com'];
    return emails.filter(email => {
        const domain = email.split('@')[1].toLowerCase();
        return !excludedDomains.some(excluded => domain.includes(excluded));
    });
}

// Perform external research using Tavily API
async function performExternalResearch(companyName, tavilyApiKey) {
    if (!tavilyApiKey) {
        return { error: 'Tavily API key not provided' };
    }

    try {
        const queries = [
            `${companyName} company funding valuation`,
            `${companyName} founders executives leadership`,
            `${companyName} products services business model`
        ];

        const results = {
            funding_info: [],
            leadership_info: [],
            business_info: []
        };

        for (let i = 0; i < queries.length; i++) {
            try {
                const response = await makeRequest('https://api.tavily.com/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        api_key: tavilyApiKey,
                        query: queries[i],
                        search_depth: 'basic',
                        include_answer: true,
                        include_raw_content: false,
                        max_results: 3
                    })
                });

                if (response.statusCode === 200) {
                    const data = JSON.parse(response.body);
                    const resultKey = Object.keys(results)[i];
                    results[resultKey] = data.results || [];
                }
            } catch (e) {
                console.log(`Tavily search failed for query: ${queries[i]}`);
            }
        }

        return results;
    } catch (error) {
        return { error: error.message };
    }
}

// Synthesize data with Gemini AI
async function synthesizeWithAI(scrapedData, externalData, geminiApiKey) {
    if (!geminiApiKey) {
        throw new Error('Gemini API key not provided');
    }

    const prompt = `
You are an expert business analyst. Analyze the following company data and create a comprehensive company profile in JSON format.

SCRAPED WEBSITE DATA:
${JSON.stringify(scrapedData, null, 2)}

EXTERNAL RESEARCH DATA:
${JSON.stringify(externalData, null, 2)}

Based on this information, create a structured company profile with the following JSON schema:

{
  "company_name": "string",
  "website_url": "string", 
  "linkedin_url": "string or null",
  "confidence_score": "High/Medium/Low",
  "summary": {
    "about": "comprehensive company description",
    "tagline": "company tagline or mission statement"
  },
  "company_details": {
    "industry": "primary industry",
    "founded_year": "number or null",
    "company_type": "Public/Private/Startup/etc",
    "headquarters": "city, country/state"
  },
  "people": {
    "founders": ["list of founder names"],
    "key_executives": ["list of key executives with titles"]
  },
  "offerings": {
    "service_details": ["list of main products/services"],
    "pricing_model": "description of pricing approach"
  },
  "valuation_and_revenue": {
    "value": "string representation of value",
    "metric_type": "valuation/revenue/funding",
    "source": "source of information",
    "source_url": "url of source or null",
    "date_of_metric": "YYYY-MM-DD or null",
    "explanation": "brief explanation of the metric"
  },
  "contact_info": {
    "phone": "phone number or null",
    "email": "email address or null", 
    "contact_page_url": "contact page URL or null"
  },
  "reference_links": {
    "crunchbase_url": "crunchbase profile URL or null",
    "wikipedia_url": "wikipedia page URL or null",
    "other": ["array of other relevant URLs"]
  },
  "last_updated": "YYYY-MM-DD"
}

INSTRUCTIONS:
1. Extract and synthesize information from both scraped and external data
2. If information is missing or unclear, use null values
3. Provide a confidence score based on data quality and completeness
4. Ensure all extracted information is factual and verifiable
5. Use today's date for last_updated field
6. Return ONLY valid JSON, no additional text or explanations

JSON Response:`;

    try {
        const response = await makeRequest(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=${geminiApiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: prompt
                    }]
                }],
                generationConfig: {
                    temperature: 0.1,
                    topK: 1,
                    topP: 1,
                    maxOutputTokens: 2048,
                }
            })
        });

        if (response.statusCode !== 200) {
            throw new Error(`Gemini API error: ${response.statusCode}`);
        }

        const data = JSON.parse(response.body);
        let responseText = data.candidates[0].content.parts[0].text;

        // Clean up response if it contains markdown code blocks
        if (responseText.startsWith('```json')) {
            responseText = responseText.slice(7);
        }
        if (responseText.endsWith('```')) {
            responseText = responseText.slice(0, -3);
        }

        const companyProfile = JSON.parse(responseText);
        return companyProfile;

    } catch (error) {
        throw new Error(`AI synthesis failed: ${error.message}`);
    }
}

// Main handler function
exports.handler = async (event, context) => {
    // Enable CORS
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    };

    // Handle preflight requests
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: ''
        };
    }

    if (event.httpMethod !== 'POST') {
        return {
            statusCode: 405,
            headers,
            body: JSON.stringify({ error: 'Method not allowed' })
        };
    }

    try {
        const { websiteUrl, maxPages = 5, includeExternal = true } = JSON.parse(event.body);

        if (!websiteUrl) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'Website URL is required' })
            };
        }

        // Get environment variables
        const geminiApiKey = process.env.GEMINI_API_KEY;
        const tavilyApiKey = process.env.TAVILY_API_KEY;

        if (!geminiApiKey) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'Gemini API key not configured' })
            };
        }

        // Step 1: Scrape website content
        const response = await makeRequest(websiteUrl);
        if (response.statusCode >= 400) {
            throw new Error(`Failed to fetch website: ${response.statusCode}`);
        }

        const htmlContent = response.body;
        const textContent = extractTextFromHTML(htmlContent);
        
        const scrapedData = {
            base_url: websiteUrl,
            company_name: extractCompanyName(websiteUrl, htmlContent),
            content: textContent.substring(0, 5000), // Limit content length
            emails: extractEmails(textContent),
            scraped_pages_count: 1
        };

        // Step 2: External research (if enabled)
        let externalData = {};
        if (includeExternal && tavilyApiKey) {
            externalData = await performExternalResearch(scrapedData.company_name, tavilyApiKey);
        }

        // Step 3: Synthesize with AI
        const companyProfile = await synthesizeWithAI(scrapedData, externalData, geminiApiKey);

        // Step 4: Finalize profile
        companyProfile.website_url = websiteUrl;
        companyProfile.last_updated = new Date().toISOString().split('T')[0];

        if (!companyProfile.confidence_score) {
            companyProfile.confidence_score = 'Medium';
        }

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(companyProfile)
        };

    } catch (error) {
        console.error('Research error:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ 
                error: error.message || 'An unexpected error occurred during research'
            })
        };
    }
};