/**
 * BlackBoxAF API client
 */
const API = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || 'API request failed');
        }
        return res.json();
    },

    async post(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || 'API request failed');
        }
        return res.json();
    },

    // Patterns
    async getPatterns(params = {}) {
        const qs = new URLSearchParams();
        for (const [k, v] of Object.entries(params)) {
            if (v !== null && v !== undefined && v !== '') qs.set(k, v);
        }
        return this.get(`/api/patterns?${qs}`);
    },

    async getPattern(id) {
        return this.get(`/api/patterns/${id}`);
    },

    async toggleFavorite(id) {
        return this.post(`/api/patterns/${id}/favorite`);
    },

    // Stats & Filters
    async getStats() {
        return this.get('/api/stats');
    },

    async getFilters() {
        return this.get('/api/filters');
    },

    // Ingest
    async ingestProject(path) {
        return this.post('/api/ingest', { path });
    },

    async getProjects(basePath) {
        const qs = basePath ? `?base_path=${encodeURIComponent(basePath)}` : '';
        return this.get(`/api/projects${qs}`);
    },

    async getIngestStatus() {
        return this.get('/api/ingest/status');
    },

    // AI Search
    async searchNL(query) {
        return this.post(`/api/patterns/search/nl?query=${encodeURIComponent(query)}`);
    },

    async getAICost() {
        return this.get('/api/patterns/search/cost');
    },
};
