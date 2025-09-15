document.addEventListener('DOMContentLoaded', () => {
    const pubListContainer = document.getElementById('pub-list-container');
    const searchInput = document.getElementById('pub-search');
    const yearFilter = document.getElementById('year-filter');

    if (!pubListContainer) return;

    const allPublications = publicationsData;

    const populateYears = () => {
        const years = [...new Set(allPublications.map(p => p.year))].sort((a, b) => b - a);
        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        });
    };

    const renderPublications = (publications) => {
        pubListContainer.innerHTML = '';
        if (publications.length === 0) {
            pubListContainer.innerHTML = '<p class="pub-no-results">No publications found.</p>';
            return;
        }

        publications.forEach(pub => {
            const pubItem = document.createElement('div');
            pubItem.className = 'pub-item card fade-in-up';

            const authors = pub.authors.join(', ');

            pubItem.innerHTML = `
                <h3>${pub.title}</h3>
                <div class="authors">${authors}</div>
                <div class="journal">${pub.journal} (${pub.year})</div>
                <a href="${pub.doi}" target="_blank" rel="noopener">
                    View Publication
                </a>
            `;
            pubListContainer.appendChild(pubItem);
        });
    };

    const filterAndRender = () => {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedYear = yearFilter.value;

        let filteredPubs = allPublications;

        if (selectedYear !== 'all') {
            filteredPubs = filteredPubs.filter(p => p.year.toString() === selectedYear);
        }

        if (searchTerm) {
            filteredPubs = filteredPubs.filter(p => {
                const titleMatch = p.title.toLowerCase().includes(searchTerm);
                const authorMatch = p.authors.some(author => author.toLowerCase().includes(searchTerm));
                const journalMatch = p.journal.toLowerCase().includes(searchTerm);
                return titleMatch || authorMatch || journalMatch;
            });
        }

        renderPublications(filteredPubs);
    };

    let debounceTimer;
    searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(filterAndRender, 300);
    });

    yearFilter.addEventListener('change', filterAndRender);

    // Initial render
    populateYears();
    renderPublications(allPublications);
});
