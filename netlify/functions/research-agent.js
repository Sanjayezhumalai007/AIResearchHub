// Simplified HTTP request function for Netlify
async function fetchWithTimeout(url, options = {}, timeout = 10000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; AIResearchAgent/1.0)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                ...options.headers
            }
        });
        
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
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
                const response = await fetchWithTimeout('https://api.tavily.com/search', {
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

                if (response.ok) {
                    const data = await response.json();
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
        const response = await fetchWithTimeout(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=${geminiApiKey}`, {
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

        if (!response.ok) {
            throw new Error(`Gemini API error: ${response.status}`);
        }

        const data = await response.json();
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
        console.log('Function started, parsing request body...');
        
        let requestData;
        try {
            requestData = JSON.parse(event.body);
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'Invalid JSON in request body' })
            };
        }

        const { websiteUrl, maxPages = 5, includeExternal = true } = requestData;

        // Progress tracking function
        const updateProgress = (stage, message, percentage) => {
            console.log(`[${stage}] ${message} (${percentage}%)`);
        };

        if (!websiteUrl) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'Website URL is required' })
            };
        }

        console.log('Processing request for:', websiteUrl);

        // Get environment variables
        const geminiApiKey = process.env.GEMINI_API_KEY;
        const tavilyApiKey = process.env.TAVILY_API_KEY;

        console.log('API keys available:', {
            gemini: !!geminiApiKey,
            tavily: !!tavilyApiKey
        });

        if (!geminiApiKey) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'Gemini API key not configured. Please add GEMINI_API_KEY to your Netlify environment variables.' })
            };
        }

        // Step 1: Scrape website content
        updateProgress('Website Analysis', 'Connecting to website...', 15);
        console.log('Step 1: Scraping website content...');
        let response;
        try {
            response = await fetchWithTimeout(websiteUrl);
            updateProgress('Website Analysis', 'Content downloaded successfully', 25);
        } catch (scrapeError) {
            console.error('Website scraping error:', scrapeError);
            return {
                statusCode: 500,
                headers,
                body: JSON.stringify({ error: `Failed to fetch website: ${scrapeError.message}` })
            };
        }

        if (!response.ok) {
            return {
                statusCode: 500,
                headers,
                body: JSON.stringify({ error: `Website returned error: ${response.status}` })
            };
        }

        updateProgress('Content Processing', 'Extracting text content...', 35);
        const htmlContent = await response.text();
        const textContent = extractTextFromHTML(htmlContent);
        
        updateProgress('Content Processing', 'Parsing company information...', 40);
        const scrapedData = {
            base_url: websiteUrl,
            company_name: extractCompanyName(websiteUrl, htmlContent),
            content: textContent.substring(0, 5000),
            emails: extractEmails(textContent),
            scraped_pages_count: 1
        };

        console.log('Scraped data extracted:', {
            company_name: scrapedData.company_name,
            content_length: scrapedData.content.length,
            emails_found: scrapedData.emails.length
        });

        // Step 2: External research (if enabled)
        updateProgress('External Research', 'Initiating external data gathering...', 50);
        console.log('Step 2: External research...');
        let externalData = {};
        if (includeExternal && tavilyApiKey) {
            try {
                updateProgress('External Research', 'Searching external sources...', 55);
                externalData = await performExternalResearch(scrapedData.company_name, tavilyApiKey);
                updateProgress('External Research', 'External research completed', 65);
                console.log('External research completed');
            } catch (externalError) {
                console.error('External research error:', externalError);
                updateProgress('External Research', 'External research failed, continuing...', 65);
                // Continue without external data
            }
        } else {
            updateProgress('External Research', 'Skipped - no Tavily API key', 65);
            console.log('External research skipped - no Tavily API key');
        }

        // Step 3: Synthesize with AI
        updateProgress('AI Analysis', 'Preparing data for AI synthesis...', 70);
        console.log('Step 3: AI synthesis...');
        let companyProfile;
        try {
            updateProgress('AI Analysis', 'Sending to Gemini AI...', 75);
            companyProfile = await synthesizeWithAI(scrapedData, externalData, geminiApiKey);
            updateProgress('AI Analysis', 'AI analysis completed', 85);
            console.log('AI synthesis completed');
        } catch (aiError) {
            console.error('AI synthesis error:', aiError);
            return {
                statusCode: 500,
                headers,
                body: JSON.stringify({ error: `AI analysis failed: ${aiError.message}` })
            };
        }

        // Step 4: Finalize profile
        updateProgress('Report Generation', 'Finalizing company profile...', 90);
        companyProfile.website_url = websiteUrl;
        companyProfile.last_updated = new Date().toISOString().split('T')[0];

        if (!companyProfile.confidence_score) {
            companyProfile.confidence_score = 'Medium';
        }

        updateProgress('Report Generation', 'Research completed successfully', 100);
        console.log('Research completed successfully');

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(companyProfile)
        };

    } catch (error) {
        console.error('Unexpected error:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ 
                error: `Research failed: ${error.message}`
            })
        };
    }
};