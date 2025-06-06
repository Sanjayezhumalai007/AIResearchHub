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
            // Try calling Flask API
            let response;
            try {
                response = await fetch('/api/research-agent', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });
            } catch (fetchError) {
                // If API is not available, show helpful error
                throw new Error('API server not accessible. Please ensure the Flask API server is running and the GEMINI_API_KEY environment variable is configured.');
            }

            let results;
            if (response.ok) {
                results = await response.json();
            } else {
                const errorText = await response.text();
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch (parseError) {
                    throw new Error(`Server error (${response.status}): ${errorText}`);
                }
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }

            this.currentResults = results;
            this.displayResults(results);
            
        } catch (error) {
            console.error('Research error:', error);
            
            // Check if this is an API key configuration issue
            if (error.message.includes('API key not configured') || error.message.includes('Gemini API key')) {
                this.showError('API key not configured. Please add GEMINI_API_KEY to your Secrets in the Tools panel on the left side of the screen.');
            } else if (error.message.includes('API server not accessible')) {
                this.showError('API server not accessible. Please ensure the Flask API server is running properly.');
            } else if (error.message.includes('Failed to fetch website')) {
                this.showError('Unable to access the website. Please check the URL and try again.');
            } else {
                this.showError(error.message || 'An unexpected error occurred during research. Please check the console for details.');
            }
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
        
        // Reset all progress indicators
        this.resetProgressIndicators();
        
        // Start the visual progress simulation
        this.startProgressAnimation();
    }

    resetProgressIndicators() {
        // Reset all stage progress bars
        for (let i = 1; i <= 5; i++) {
            document.getElementById(`stage${i}Progress`).style.width = '0%';
            document.getElementById(`stage${i}Details`).classList.add('hidden');
            
            // Reset stage icons
            const icon = document.getElementById(`stage${i}Icon`);
            icon.className = 'flex items-center justify-center w-16 h-16 rounded-full bg-gray-200 border-4 border-white shadow-lg z-10 transition-all duration-500';
            
            // Reset icon colors and restore original icons
            const iconElement = icon.querySelector('i');
            iconElement.classList.remove('fa-spin', 'fa-check');
            iconElement.className = iconElement.className.replace('text-blue-600', 'text-gray-400').replace('text-green-600', 'text-gray-400');
            
            // Restore original icons
            const originalIcons = ['fa-globe', 'fa-cogs', 'fa-search', 'fa-brain', 'fa-file-alt'];
            iconElement.className = iconElement.className.replace(/fa-[^ ]+/, originalIcons[i - 1]);
        }
        
        // Reset overall progress
        document.getElementById('overallProgressBar').style.width = '0%';
        document.getElementById('overallProgressBar').className = 'bg-gradient-to-r from-blue-600 to-blue-700 h-3 rounded-full transition-all duration-500';
        document.getElementById('overallProgressText').textContent = '0%';
        document.getElementById('progressLine').style.height = '0%';
        
        // Reset stats
        document.getElementById('pagesProcessed').textContent = '0';
        document.getElementById('dataPointsFound').textContent = '0';
        document.getElementById('aiTokensUsed').textContent = '0';
        
        // Reset estimated time
        document.getElementById('estimatedTime').textContent = 'Estimated time: 30-45 seconds';
    }

    startProgressAnimation() {
        let currentStage = 0;
        let overallProgress = 0;
        
        const stages = [
            {
                name: 'Website Analysis',
                duration: 3000,
                steps: [
                    'Connecting to website...',
                    'Downloading HTML content...',
                    'Extracting main content...',
                    'Identifying company information...'
                ]
            },
            {
                name: 'Content Processing',
                duration: 2000,
                steps: [
                    'Cleaning extracted text...',
                    'Parsing company details...',
                    'Extracting contact information...',
                    'Structuring data...'
                ]
            },
            {
                name: 'External Research',
                duration: 4000,
                steps: [
                    'Searching funding information...',
                    'Looking up leadership data...',
                    'Gathering business intelligence...',
                    'Collecting reference links...'
                ]
            },
            {
                name: 'AI Analysis',
                duration: 3000,
                steps: [
                    'Preparing data for AI analysis...',
                    'Sending to Gemini AI...',
                    'Processing AI response...',
                    'Structuring final output...'
                ]
            },
            {
                name: 'Report Generation',
                duration: 1500,
                steps: [
                    'Finalizing company profile...',
                    'Validating data quality...',
                    'Generating final report...',
                    'Preparing display...'
                ]
            }
        ];

        const animateStage = (stageIndex) => {
            if (stageIndex >= stages.length) return;
            
            const stage = stages[stageIndex];
            const stageNumber = stageIndex + 1;
            
            // Update main progress text
            document.getElementById('progressText').textContent = `${stage.name} in progress...`;
            
            // Activate stage icon
            this.activateStageIcon(stageNumber);
            
            // Show stage details
            document.getElementById(`stage${stageNumber}Details`).classList.remove('hidden');
            
            // Animate stage progress
            this.animateStageProgress(stageNumber, stage.steps, stage.duration, () => {
                // Complete this stage
                this.completeStage(stageNumber);
                
                // Update overall progress
                overallProgress = Math.round(((stageIndex + 1) / stages.length) * 100);
                this.updateOverallProgress(overallProgress);
                
                // Update progress line
                const lineProgress = ((stageIndex + 1) / stages.length) * 100;
                document.getElementById('progressLine').style.height = `${lineProgress}%`;
                
                // Move to next stage
                setTimeout(() => {
                    animateStage(stageIndex + 1);
                }, 500);
            });
        };

        // Start with first stage
        animateStage(0);
    }

    activateStageIcon(stageNumber) {
        const icon = document.getElementById(`stage${stageNumber}Icon`);
        const iconElement = icon.querySelector('i');
        
        // Add active state with enhanced animations
        icon.className = 'flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 border-4 border-blue-200 shadow-lg z-10 transition-all duration-500 pulse-glow stage-active';
        
        // Add spinning animation and enhanced styling
        iconElement.classList.add('fa-spin');
        iconElement.className = iconElement.className.replace('text-gray-400', 'text-blue-600');
        
        // Add progress shimmer to the stage progress bar
        const progressBar = document.getElementById(`stage${stageNumber}Progress`);
        progressBar.classList.add('progress-shimmer');
    }

    completeStage(stageNumber) {
        const icon = document.getElementById(`stage${stageNumber}Icon`);
        const iconElement = icon.querySelector('i');
        const progressBar = document.getElementById(`stage${stageNumber}Progress`);
        
        // Remove active animations
        iconElement.classList.remove('fa-spin');
        icon.classList.remove('pulse-glow', 'stage-active');
        progressBar.classList.remove('progress-shimmer');
        
        // Add completed state with success animation
        icon.className = 'flex items-center justify-center w-16 h-16 rounded-full bg-green-100 border-4 border-green-200 shadow-lg z-10 transition-all duration-500 success-bounce';
        iconElement.className = iconElement.className.replace('text-blue-600', 'text-green-600');
        
        // Change icon to checkmark
        iconElement.className = iconElement.className.replace(/fa-[^ ]+/, 'fa-check');
        
        // Add completion sound effect (optional - browser compatible)
        this.playCompletionSound();
    }

    playCompletionSound() {
        // Create a simple completion beep using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(1000, audioContext.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (e) {
            // Fallback: silent if audio context not available
            console.log('Audio feedback not available');
        }
    }

    animateStageProgress(stageNumber, steps, duration, onComplete) {
        const progressBar = document.getElementById(`stage${stageNumber}Progress`);
        const statusElement = document.getElementById(`stage${stageNumber}Status`);
        
        let currentStep = 0;
        const stepDuration = duration / steps.length;
        
        const updateStep = () => {
            if (currentStep < steps.length) {
                statusElement.textContent = steps[currentStep];
                
                const progress = ((currentStep + 1) / steps.length) * 100;
                progressBar.style.width = `${progress}%`;
                
                // Update realistic stats based on stage
                this.updateRealtimeStats(stageNumber, currentStep);
                
                currentStep++;
                setTimeout(updateStep, stepDuration);
            } else {
                onComplete();
            }
        };
        
        updateStep();
    }

    updateRealtimeStats(stageNumber, stepIndex) {
        const pagesElement = document.getElementById('pagesProcessed');
        const dataPointsElement = document.getElementById('dataPointsFound');
        const tokensElement = document.getElementById('aiTokensUsed');
        
        // Simulate realistic stat updates based on current stage
        switch(stageNumber) {
            case 1: // Website Analysis
                if (stepIndex >= 1) {
                    pagesElement.textContent = Math.min(stepIndex, 3);
                }
                break;
            case 2: // Content Processing
                if (stepIndex >= 2) {
                    dataPointsElement.textContent = Math.min(5 + stepIndex * 3, 15);
                }
                break;
            case 3: // External Research
                if (stepIndex >= 1) {
                    dataPointsElement.textContent = Math.min(15 + stepIndex * 5, 35);
                }
                break;
            case 4: // AI Analysis
                if (stepIndex >= 1) {
                    tokensElement.textContent = Math.min(stepIndex * 250, 1000);
                }
                break;
            case 5: // Report Generation
                dataPointsElement.textContent = Math.min(parseInt(dataPointsElement.textContent) + stepIndex * 2, 45);
                tokensElement.textContent = Math.min(parseInt(tokensElement.textContent) + stepIndex * 50, 1200);
                break;
        }
    }

    updateOverallProgress(percentage) {
        document.getElementById('overallProgressBar').style.width = `${percentage}%`;
        document.getElementById('overallProgressText').textContent = `${percentage}%`;
        
        // Update estimated time based on progress
        const remainingTime = Math.max(0, Math.round((100 - percentage) * 0.4));
        if (remainingTime > 0) {
            document.getElementById('estimatedTime').textContent = `${remainingTime} seconds remaining`;
        } else {
            document.getElementById('estimatedTime').textContent = 'Almost done...';
        }
    }

    hideProgress() {
        // Show completion animation before hiding
        this.showCompletionAnimation(() => {
            document.getElementById('progressSection').classList.add('hidden');
        });
    }

    showCompletionAnimation(callback) {
        // Update main text to completion
        document.getElementById('progressText').textContent = 'Research completed successfully!';
        
        // Final progress update
        this.updateOverallProgress(100);
        document.getElementById('progressLine').style.height = '100%';
        
        // Add success animation to overall progress bar
        const overallBar = document.getElementById('overallProgressBar');
        overallBar.className = 'bg-gradient-to-r from-green-600 to-green-700 h-3 rounded-full transition-all duration-500';
        
        // Update estimated time
        document.getElementById('estimatedTime').textContent = 'Complete!';
        
        // Wait for animation to complete
        setTimeout(() => {
            callback();
        }, 1500);
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