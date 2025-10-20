class FeedbackHandler {
    constructor() {
        this.currentQuery = '';
        this.aiResponse = '';
        this.bindEvents();
        this.initializeSliders();
        console.log('FeedbackHandler initialized');
    }

    bindEvents() {
        // Bind submit feedback button
        document.getElementById('submit-feedback')?.addEventListener('click', () => this.submitFeedback());
        
        // Show revised feedback form when revised response is generated
        document.getElementById('generate-revised')?.addEventListener('click', async () => {
            await this.generateRevisedResponse();
            
            // Show the revised feedback form if we have a response
            const revisedResponse = document.getElementById('revised-response');
            const revisedFeedbackForm = document.getElementById('revisedFeedbackForm');
            
            if (revisedResponse?.textContent.trim() && revisedFeedbackForm) {
                revisedFeedbackForm.style.display = 'block';
            }
        });
    }

    initializeSliders() {
        // Initialize all sliders (both original and revised)
        document.querySelectorAll('.slider').forEach(slider => {
            const valueDisplay = slider.nextElementSibling;
            if (valueDisplay) {
                valueDisplay.textContent = slider.value;
                slider.oninput = function() {
                    valueDisplay.textContent = this.value;
                };
            }
        });
    }

    setCurrentQuery(query) {
        this.currentQuery = query;
    }

    setAIResponse(response) {
        this.aiResponse = response;
    }

    async generateRevisedResponse() {
        const revisedPrompt = document.querySelector('#revised-prompt')?.value.trim();
        const generateButton = document.querySelector('#generate-revised');
        const spinner = generateButton?.querySelector('.spinner');
        const buttonText = generateButton?.querySelector('.button-text');
        
        // Validation
        if (!revisedPrompt || revisedPrompt.length < 5) {
            alert('Please enter a revised prompt (minimum 5 characters)');
            return;
        }

        try {
            // Update button state
            generateButton.disabled = true;
            spinner?.classList.remove('hidden');
            buttonText.textContent = 'Generating...';

            const response = await fetch('/process-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    query: revisedPrompt,
                    type: 'research'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            const revisedResponseDiv = document.querySelector('#revised-response');
            if (revisedResponseDiv) {
                revisedResponseDiv.textContent = result.response;
                // Show the revised feedback form
                document.getElementById('revisedFeedbackForm').style.display = 'block';
            }
        } catch (error) {
            console.error('Error generating revised response:', error);
            alert('Error generating revised response. Please try again.');
        } finally {
            // Reset button state
            generateButton.disabled = false;
            spinner?.classList.add('hidden');
            buttonText.textContent = 'Generate Revised Response';
        }
    }

    async submitFeedback() {
        console.log('Starting feedback submission...');
        
        // Get revised response content to check if it exists
        const revisedResponseContent = document.querySelector('#revised-response')?.textContent?.trim();
        
        const feedbackData = {
            feedback_id: crypto.randomUUID(), // Generate unique ID for the feedback
            user_query: document.querySelector('#searchInput')?.value || '',
            ai_response: document.querySelector('.answer-section')?.textContent || '',
            question_type: document.querySelector('input[name="question_type"]:checked')?.value || 'research',
            
            // Original metrics and tags
            metrics: {
                clarity: parseInt(document.querySelector('input[name="ai_clarity"]')?.value || '4'),
                interpretation: parseInt(document.querySelector('input[name="paper_interpretation"]')?.value || '4'),
                relevance: parseInt(document.querySelector('input[name="topic_relevance"]')?.value || '4'),
                depth: parseInt(document.querySelector('input[name="response_depth"]')?.value || '4'),
                citations_quality: parseInt(document.querySelector('input[name="citations_quality"]')?.value || '4'),
                reasoning: parseInt(document.querySelector('input[name="ai_reasoning"]')?.value || '4')
            },
            tags: {
                strengths: Array.from(document.querySelectorAll('input[name="strength"]:checked')).map(cb => cb.value),
                weaknesses: Array.from(document.querySelectorAll('input[name="weakness"]:checked')).map(cb => cb.value)
            }
        };

        // Only add revised data if there's a revised response
        if (revisedResponseContent) {
            feedbackData.revised_prompt = document.querySelector('#revised-prompt')?.value || '';
            feedbackData.revised_response = revisedResponseContent;
            feedbackData.revised_metrics = {
                clarity: parseInt(document.querySelector('input[name="revised_ai_clarity"]')?.value || '4'),
                interpretation: parseInt(document.querySelector('input[name="revised_paper_interpretation"]')?.value || '4'),
                relevance: parseInt(document.querySelector('input[name="revised_topic_relevance"]')?.value || '4'),
                depth: parseInt(document.querySelector('input[name="revised_response_depth"]')?.value || '4'),
                citations_quality: parseInt(document.querySelector('input[name="revised_citations_quality"]')?.value || '4'),
                reasoning: parseInt(document.querySelector('input[name="revised_ai_reasoning"]')?.value || '4')
            };
            feedbackData.revised_tags = {
                strengths: Array.from(document.querySelectorAll('input[name="revised_strength"]:checked')).map(cb => cb.value),
                weaknesses: Array.from(document.querySelectorAll('input[name="revised_weakness"]:checked')).map(cb => cb.value)
            };
        }
        
        console.log('Submitting feedback data:', feedbackData);

        try {
            const response = await fetch('/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(feedbackData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Error details:', errorData);
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            console.log('Feedback submitted successfully');
            alert('Feedback submitted successfully!');
            this.resetForm();
        } catch (error) {
            console.error('Error submitting feedback:', error);
            alert('Error submitting feedback. Please try again.');
        }
    }

    resetForm() {
        // Reset all sliders (both original and revised)
        document.querySelectorAll('.slider').forEach(slider => {
            slider.value = 4;
            slider.nextElementSibling.textContent = '4';
        });
        
        // Reset all checkboxes (both original and revised)
        document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        // Reset radio buttons
        document.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.checked = false;
        });
        // Set default radio button (research)
        const defaultRadio = document.querySelector('input[name="question_type"][value="research"]');
        if (defaultRadio) defaultRadio.checked = true;

        // Reset revised prompt textarea
        const revisedPrompt = document.querySelector('#revised-prompt');
        if (revisedPrompt) revisedPrompt.value = '';

        // Reset revised response and hide revised feedback form
        const revisedResponse = document.querySelector('#revised-response');
        if (revisedResponse) revisedResponse.textContent = '';
        
        const revisedFeedbackForm = document.querySelector('#revisedFeedbackForm');
        if (revisedFeedbackForm) revisedFeedbackForm.style.display = 'none';

        // Reset character counter
        const charCount = document.querySelector('#char-count');
        if (charCount) charCount.textContent = '0';
    }
}

// Export the instance
export const feedbackHandler = new FeedbackHandler(); 