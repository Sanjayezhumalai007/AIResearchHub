class AIResearchAgent {
    constructor() {
        this.currentResults = null;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Form submission
        document.getElementById('researchForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startResearch();
        });

        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Download button
        document.getElementById('downloadBtn').addEventListener('click', () => {
            this.downloadResults();
        });

        // Clear button
        document.getElementById('clearBtn').addEventListener('click', () => {
            this.clearResults();
        });
    }

    async startResearch() {
        const form = document.getElementById('researchForm');
        const formData = new FormData(form);
        
        const requestData = {
            websiteUrl: formData.get('websiteUrl'),
            maxPages: parseInt(formData.get('maxPages')),
            includeExternal: formData.get('includeExternal') === 'on'
        };

        // Validate URL
        if (!this.isValidUrl(requestData.websiteUrl)) {
            this.showError('Please enter a valid URL');
            return;
        }

        // Show progress
        this.showProgress();
        
        try {
            // Call Netlify function
            const response = await fetch('/.netlify/functions/research-agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Research failed');
            }

            const results = await response.json();
            this.currentResults = results;
            this.displayResults(results);
            
        } catch (error) {
            console.error('Research error:', error);
            this.showError(error.message || 'An unexpected error occurred during research');
        } finally {
            this.hideProgress();
        }
    }

    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    showProgress() {
        document.getElementById('progressSection').classList.remove('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        document.getElementById('errorSection').classList.add('hidden');
        
        // Simulate progress updates
        let progress = 0;
        const messages = [
            'Initializing web scraper...',
            'Scraping website content...',
            'Conducting external research...',
            'Synthesizing data with AI...',
            'Finalizing report...'
        ];
        
        const interval = setInterval(() => {
            progress += 20;
            document.getElementById('progressBar').style.width = `${progress}%`;
            
            if (progress <= 80) {
                const messageIndex = Math.floor((progress - 20) / 20);
                document.getElementById('progressText').textContent = messages[messageIndex];
            }
            
            if (progress >= 100) {
                clearInterval(interval);
                document.getElementById('progressText').textContent = 'Research completed!';
            }
        }, 1000);
    }

    hideProgress() {
        document.getElementById('progressSection').classList.add('hidden');
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorSection').classList.remove('hidden');
        document.getElementById('progressSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
    }

    displayResults(results) {
        document.getElementById('resultsSection').classList.remove('hidden');
        document.getElementById('errorSection').classList.add('hidden');

        // Update header
        document.getElementById('companyName').textContent = results.company_name || 'Unknown Company';
        
        const websiteLink = document.querySelector('#websiteLink a');
        websiteLink.href = results.website_url;
        websiteLink.textContent = results.website_url;
        
        document.querySelector('#confidenceScore span').textContent = results.confidence_score || 'N/A';
        document.querySelector('#lastUpdated span').textContent = results.last_updated || 'N/A';

        // Populate tabs
        this.populateSummaryTab(results.summary || {});
        this.populateDetailsTab(results.company_details || {});
        this.populatePeopleTab(results.people || {});
        this.populateOfferingsTab(results.offerings || {});
        this.populateFinancialsTab(results.valuation_and_revenue || {});
        this.populateContactInfo(results.contact_info || {});
        this.populateReferenceLinks(results.reference_links || {});

        // Show first tab
        this.switchTab('summary');
    }

    populateSummaryTab(summary) {
        const aboutSection = document.getElementById('aboutSection');
        const taglineSection = document.getElementById('taglineSection');

        if (summary.about) {
            aboutSection.querySelector('p').textContent = summary.about;
            aboutSection.classList.remove('hidden');
        }

        if (summary.tagline) {
            taglineSection.querySelector('p').textContent = summary.tagline;
            taglineSection.classList.remove('hidden');
        }
    }

    populateDetailsTab(details) {
        const container = document.getElementById('detailsContent');
        container.innerHTML = '';

        const fields = [
            { key: 'industry', label: 'Industry', icon: 'fas fa-industry' },
            { key: 'founded_year', label: 'Founded', icon: 'fas fa-calendar-alt' },
            { key: 'company_type', label: 'Type', icon: 'fas fa-building' },
            { key: 'headquarters', label: 'Headquarters', icon: 'fas fa-map-marker-alt' }
        ];

        fields.forEach(field => {
            if (details[field.key]) {
                const div = document.createElement('div');
                div.className = 'bg-gray-50 p-4 rounded-lg';
                div.innerHTML = `
                    <div class="flex items-center mb-2">
                        <i class="${field.icon} text-blue-600 mr-2"></i>
                        <h4 class="font-medium text-gray-800">${field.label}</h4>
                    </div>
                    <p class="text-gray-600">${details[field.key]}</p>
                `;
                container.appendChild(div);
            }
        });
    }

    populatePeopleTab(people) {
        const container = document.getElementById('peopleContent');
        container.innerHTML = '';

        if (people.founders && people.founders.length > 0) {
            const foundersDiv = document.createElement('div');
            foundersDiv.innerHTML = `
                <h4 class="font-medium text-gray-800 mb-3">
                    <i class="fas fa-user-tie text-blue-600 mr-2"></i>Founders
                </h4>
                <ul class="space-y-2">
                    ${people.founders.map(founder => `<li class="text-gray-600">• ${founder}</li>`).join('')}
                </ul>
            `;
            container.appendChild(foundersDiv);
        }

        if (people.key_executives && people.key_executives.length > 0) {
            const execsDiv = document.createElement('div');
            execsDiv.innerHTML = `
                <h4 class="font-medium text-gray-800 mb-3">
                    <i class="fas fa-users text-blue-600 mr-2"></i>Key Executives
                </h4>
                <ul class="space-y-2">
                    ${people.key_executives.map(exec => `<li class="text-gray-600">• ${exec}</li>`).join('')}
                </ul>
            `;
            container.appendChild(execsDiv);
        }
    }

    populateOfferingsTab(offerings) {
        const container = document.getElementById('offeringsContent');
        container.innerHTML = '';

        if (offerings.service_details && offerings.service_details.length > 0) {
            const servicesDiv = document.createElement('div');
            servicesDiv.innerHTML = `
                <h4 class="font-medium text-gray-800 mb-3">
                    <i class="fas fa-cogs text-blue-600 mr-2"></i>Services & Products
                </h4>
                <ul class="space-y-2">
                    ${offerings.service_details.map(service => `<li class="text-gray-600">• ${service}</li>`).join('')}
                </ul>
            `;
            container.appendChild(servicesDiv);
        }

        if (offerings.pricing_model) {
            const pricingDiv = document.createElement('div');
            pricingDiv.innerHTML = `
                <h4 class="font-medium text-gray-800 mb-3">
                    <i class="fas fa-dollar-sign text-blue-600 mr-2"></i>Pricing Model
                </h4>
                <p class="text-gray-600">${offerings.pricing_model}</p>
            `;
            container.appendChild(pricingDiv);
        }
    }

    populateFinancialsTab(financials) {
        const container = document.getElementById('financialsContent');
        container.innerHTML = '';

        if (financials.value) {
            const valueDiv = document.createElement('div');
            valueDiv.className = 'bg-green-50 p-6 rounded-lg border border-green-200';
            valueDiv.innerHTML = `
                <h4 class="font-medium text-green-800 mb-3">
                    <i class="fas fa-chart-line text-green-600 mr-2"></i>${financials.metric_type || 'Value'}
                </h4>
                <p class="text-2xl font-bold text-green-700 mb-2">$${financials.value}</p>
                ${financials.source ? `<p class="text-sm text-green-600">Source: ${financials.source}</p>` : ''}
                ${financials.date_of_metric ? `<p class="text-sm text-green-600">Date: ${financials.date_of_metric}</p>` : ''}
                ${financials.explanation ? `<p class="text-sm text-green-600 mt-2">${financials.explanation}</p>` : ''}
            `;
            container.appendChild(valueDiv);
        }
    }

    populateContactInfo(contact) {
        const container = document.getElementById('contactContent');
        container.innerHTML = '';

        const fields = [
            { key: 'email', label: 'Email', icon: 'fas fa-envelope' },
            { key: 'phone', label: 'Phone', icon: 'fas fa-phone' },
            { key: 'contact_page_url', label: 'Contact Page', icon: 'fas fa-external-link-alt', isLink: true }
        ];

        fields.forEach(field => {
            if (contact[field.key]) {
                const div = document.createElement('div');
                div.className = 'flex items-center';
                
                if (field.isLink) {
                    div.innerHTML = `
                        <i class="${field.icon} text-blue-600 mr-2"></i>
                        <a href="${contact[field.key]}" target="_blank" class="text-blue-600 hover:underline">${field.label}</a>
                    `;
                } else {
                    div.innerHTML = `
                        <i class="${field.icon} text-blue-600 mr-2"></i>
                        <span class="text-gray-600">${contact[field.key]}</span>
                    `;
                }
                container.appendChild(div);
            }
        });
    }

    populateReferenceLinks(links) {
        const container = document.getElementById('linksContent');
        container.innerHTML = '';

        const linkFields = [
            { key: 'linkedin_url', label: 'LinkedIn', icon: 'fab fa-linkedin', color: 'bg-blue-600' },
            { key: 'crunchbase_url', label: 'Crunchbase', icon: 'fas fa-database', color: 'bg-orange-500' },
            { key: 'wikipedia_url', label: 'Wikipedia', icon: 'fab fa-wikipedia-w', color: 'bg-gray-700' }
        ];

        linkFields.forEach(field => {
            if (links[field.key]) {
                const link = document.createElement('a');
                link.href = links[field.key];
                link.target = '_blank';
                link.className = `${field.color} text-white px-3 py-2 rounded-lg text-sm hover:opacity-90 transition duration-200`;
                link.innerHTML = `<i class="${field.icon} mr-2"></i>${field.label}`;
                container.appendChild(link);
            }
        });

        if (links.other && links.other.length > 0) {
            links.other.forEach(url => {
                const link = document.createElement('a');
                link.href = url;
                link.target = '_blank';
                link.className = 'bg-gray-500 text-white px-3 py-2 rounded-lg text-sm hover:opacity-90 transition duration-200';
                link.innerHTML = `<i class="fas fa-link mr-2"></i>Other`;
                container.appendChild(link);
            });
        }
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            if (button.dataset.tab === tabName) {
                button.classList.add('active', 'border-blue-500', 'text-blue-600');
                button.classList.remove('border-transparent', 'text-gray-500');
            } else {
                button.classList.remove('active', 'border-blue-500', 'text-blue-600');
                button.classList.add('border-transparent', 'text-gray-500');
            }
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            if (content.id === `tab-${tabName}`) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        });
    }

    downloadResults() {
        if (!this.currentResults) return;

        const dataStr = JSON.stringify(this.currentResults, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `${this.currentResults.company_name || 'company'}_report_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    clearResults() {
        this.currentResults = null;
        document.getElementById('resultsSection').classList.add('hidden');
        document.getElementById('errorSection').classList.add('hidden');
        document.getElementById('researchForm').reset();
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new AIResearchAgent();
});