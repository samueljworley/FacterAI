export class SearchHandler {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.searchButton = document.getElementById('searchButton');
        this.resultsDiv = document.getElementById('results');
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

        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await response.json();
            this.displayResults(data);
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    displayResults(data) {
        // Your results display logic
    }
} 