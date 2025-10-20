// Debug flag to verify script loading
console.log('Main.js loaded - v2');

import { feedbackHandler } from './components/FeedbackHandler.js';

// SearchHandler class
class SearchHandler {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.searchButton = document.getElementById('searchButton');
        this.resultsDiv = document.getElementById('results');
        this.referencesDiv = document.getElementById('referenced-studies');
        this.bindEvents();
    }

    bindEvents() {
        this.searchButton.addEventListener('click', () => this.handleSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.handleSearch();
            }
        });
    }

    async handleSearch() {
        const query = this.searchInput.value.trim();
        if (!query) return;

        // Set loading state
        this.setLoadingState(true);

        // Set the current query in the feedback handler
        feedbackHandler.setCurrentQuery(query);

        // Get selected query type
        const selectedType = document.querySelector('input[name="query_type"]:checked');
        const queryType = selectedType ? selectedType.value : 'research';

        console.log('Sending request with:', { query, query_type: queryType }); // Debug log

        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    query: query,
                    query_type: queryType 
                })
            });
            const data = await response.json();
            this.displayResults(data);
        } catch (error) {
            console.error('Search error:', error);
            this.resultsDiv.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        } finally {
            // Reset loading state
            this.setLoadingState(false);
        }
    }

    setLoadingState(isLoading) {
        const button = this.searchButton;
        const input = this.searchInput;
        
        if (isLoading) {
            button.classList.add('loading');
            button.disabled = true;
            input.disabled = true;
        } else {
            button.classList.remove('loading');
            button.disabled = false;
            input.disabled = false;
        }
    }

    displayResults(data) {
        try {
            console.log("Full data received:", data);
            
            // Handle the main answer
            if (data.response) {
                this.resultsDiv.innerHTML = `<div class="answer-section">${data.response}</div>`;
                feedbackHandler.setAIResponse(data.response);
            } else if (data.result && data.result.answer) {
                this.resultsDiv.innerHTML = `<div class="answer-section">${data.result.answer}</div>`;
                feedbackHandler.setAIResponse(data.result.answer);
            } else {
                this.resultsDiv.innerHTML = `<div class="answer-section">No answer available</div>`;
                feedbackHandler.setAIResponse('No answer available');
            }

            // Handle cited articles in the sidebar - try multiple possible data structures
            let citedPapers = [];
            if (data.cited_papers) {
                citedPapers = data.cited_papers;
                console.log("Found cited_papers:", citedPapers);
            } else if (data.result && data.result.cited_papers) {
                citedPapers = data.result.cited_papers;
                console.log("Found result.cited_papers:", citedPapers);
            } else if (data.result && data.result.sources) {
                citedPapers = data.result.sources;
                console.log("Using result.sources as cited_papers:", citedPapers);
            }
            
            this.displayCitedArticles(citedPapers);

            // Handle sources/studies if any exist (keeping for backward compatibility)
            if (data.result && data.result.sources && data.result.sources.length > 0) {
                console.log("Sources found:", data.result.sources);
                const sourcesHtml = data.result.sources.map(source => {
                    console.log("Processing source:", source);
                    return `
                        <div class="study-card">
                            <h3>${source.title || 'Source'}</h3>
                            ${source.authors ? `<p><strong>Authors:</strong> ${Array.isArray(source.authors) ? source.authors.join(', ') : source.authors}</p>` : ''}
                            ${source.journal ? `<p><strong>Journal:</strong> ${source.journal}</p>` : ''}
                            <p>
                                ${source.pmid ? 
                                    `<strong>PubMed:</strong> <a href="https://pubmed.ncbi.nlm.nih.gov/${source.pmid}" target="_blank">View on PubMed</a>` : 
                                    ''}
                                ${source.arxiv_id ? 
                                    `<strong>arXiv:</strong> <a href="https://arxiv.org/abs/${source.arxiv_id}" target="_blank">View on arXiv</a>` : 
                                    ''}
                            </p>
                            ${source.abstract ? `<div class="study-summary"><strong>Abstract:</strong><p>${source.abstract}</p></div>` : ''}
                        </div>
                    `;
                }).join('');
                if (this.referencesDiv) {
                    this.referencesDiv.innerHTML = sourcesHtml;
                }
            } else if (this.referencesDiv) {
                this.referencesDiv.innerHTML = '<p>No studies referenced</p>';
            }

        } catch (error) {
            console.error('Error displaying results:', error);
            this.resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        }
    }

    displayCitedArticles(citedPapers) {
        console.log("displayCitedArticles called with:", citedPapers);
        
        const citedArticlesContainer = document.querySelector('.cited-articles-container');
        console.log("Found citedArticlesContainer:", citedArticlesContainer);
        
        if (!citedArticlesContainer) {
            console.error("Could not find .cited-articles-container element");
            return;
        }

        if (citedPapers && citedPapers.length > 0) {
            console.log("Processing", citedPapers.length, "cited papers");
            const articlesHtml = citedPapers.map((paper, index) => {
                console.log("Processing paper", index, ":", paper);
                const authors = Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors || 'Unknown Authors';
                const journal = paper.journal || 'Unknown Journal';
                const title = paper.title || 'Untitled Paper';
                
                // Create PubMed link if we have a PMID
                const pmid = paper.pmid || paper.id;
                const pubmedUrl = pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : null;
                
                return `
                    <div class="cited-article" data-index="${index}">
                        <div class="cited-article-title">
                            ${pubmedUrl ? `<a href="${pubmedUrl}" target="_blank" class="article-link">${title}</a>` : title}
                        </div>
                        <div class="cited-article-authors">${authors}</div>
                        <div class="cited-article-journal">${journal}</div>
                    </div>
                `;
            }).join('');
            
            console.log("Generated HTML for sidebar:", articlesHtml);
            citedArticlesContainer.innerHTML = articlesHtml;
        } else {
            console.log("No cited papers found, showing placeholder message");
            citedArticlesContainer.innerHTML = `
                <div class="no-articles-message">
                    
                    <p>No articles found for this query</p>
                </div>
            `;
        }
    }
}

// FeedbackHandler class
class FeedbackHandler {
    constructor() {
        this.form = document.getElementById('feedbackForm');
        this.bindEvents();
        this.initializeSliders();
    }

    bindEvents() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        document.querySelectorAll('input[name="topics"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.enforceTopicLimit());
        });
    }

    initializeSliders() {
        document.querySelectorAll('.slider').forEach(slider => {
            const valueDisplay = slider.nextElementSibling;
            valueDisplay.textContent = slider.value;
            
            slider.oninput = function() {
                valueDisplay.textContent = this.value;
            };
        });
    }

    enforceTopicLimit() {
        const checkedTopics = document.querySelectorAll('input[name="topics"]:checked');
        if (checkedTopics.length > 2) {
            checkedTopics[checkedTopics.length - 1].checked = false;
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        try {
            const data = this.collectFormData();
            console.log('Submitting feedback:', data);

            const response = await fetch('/submit-feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.showSuccessMessage();
            this.form.reset();
            
        } catch (error) {
            console.error('Error submitting feedback:', error);
            alert('Error submitting feedback. Please try again.');
        }
    }

    collectFormData() {
        return {
            feedback_id: crypto.randomUUID(),
            user_query: document.getElementById('searchInput')?.value || 'No query captured',
            ai_response: document.querySelector('.answer-section p')?.textContent || 
                        document.querySelector('#results p')?.textContent || 
                        'No response captured',
            
            // Original feedback metrics
            metrics: {
                clarity: parseInt(document.querySelector('input[name="ai_clarity"]').value) || 4,
                interpretation: parseInt(document.querySelector('input[name="paper_interpretation"]').value) || 4,
                relevance: parseInt(document.querySelector('input[name="topic_relevance"]').value) || 4,
                depth: parseInt(document.querySelector('input[name="response_depth"]').value) || 4,
                citations_quality: parseInt(document.querySelector('input[name="citations_quality"]').value) || 4,
                reasoning: parseInt(document.querySelector('input[name="ai_reasoning"]').value) || 4,
            },
            
            // Revised feedback metrics (if present)
            revised_metrics: {
                revised_clarity: parseInt(document.querySelector('input[name="revised_ai_clarity"]')?.value) || 4,
                revised_interpretation: parseInt(document.querySelector('input[name="revised_paper_interpretation"]')?.value) || 4,
                revised_relevance: parseInt(document.querySelector('input[name="revised_topic_relevance"]')?.value) || 4,
                revised_depth: parseInt(document.querySelector('input[name="revised_response_depth"]')?.value) || 4,
                revised_citations_quality: parseInt(document.querySelector('input[name="revised_citations_quality"]')?.value) || 4,
                revised_reasoning: parseInt(document.querySelector('input[name="revised_ai_reasoning"]')?.value) || 4,
            },
            
            // Tags
            strength_tags: Array.from(document.querySelectorAll('input[name="strength"]:checked'))
                .map(checkbox => checkbox.value),
            weakness_tags: Array.from(document.querySelectorAll('input[name="weakness"]:checked'))
                .map(checkbox => checkbox.value),
            
            // Revised tags
            revised_tags: {
                strengths: Array.from(document.querySelectorAll('input[name="revised_strength"]:checked'))
                    .map(checkbox => checkbox.value),
                improvements: Array.from(document.querySelectorAll('input[name="revised_weakness"]:checked'))
                    .map(checkbox => checkbox.value)
            },
            
            question_type: document.querySelector('input[name="question_type"]:checked')?.value || 'concept'
        };
    }

    showSuccessMessage() {
        const confirmMessage = document.createElement('div');
        confirmMessage.textContent = 'Feedback submitted successfully!';
        confirmMessage.style.color = 'green';
        confirmMessage.style.marginTop = '10px';
        this.form.appendChild(confirmMessage);
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM is loaded');
    try {
        const searchHandler = new SearchHandler();
        const feedbackHandler = new FeedbackHandler();
        console.log('Handlers initialized');
    } catch (error) {
        console.error('Error initializing handlers:', error);
    }
});
