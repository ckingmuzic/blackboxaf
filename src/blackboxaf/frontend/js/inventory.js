/**
 * BlackBoxAF Inventory Grid - Minecraft-style pattern block display
 */

const CATEGORY_ICONS = {
    'Flow Logic':      '\u26A1',
    'Data Validation': '\u2714',
    'Data Model':      '\u2B22',
    'UI Component':    '\u25A3',
    'Reporting':       '\u2637',
    'Page Layout':     '\u2B1A',
    'Apex Logic':      '\u2699',
};

const COMPLEXITY_LABELS = ['', 'Basic', 'Simple', 'Moderate', 'Complex', 'Expert'];

let currentFilters = {};
let currentPage = 1;
let filtersData = null;

// ── Initialize ──
document.addEventListener('DOMContentLoaded', async () => {
    await loadFilters();
    await loadStats();
    await loadPatterns();
    setupEventListeners();
});

function setupEventListeners() {
    // Search
    const searchInput = document.getElementById('search-input');
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentFilters.q = searchInput.value;
            currentPage = 1;
            loadPatterns();
        }, 300);
    });

    // Filter dropdowns
    document.getElementById('filter-category').addEventListener('change', (e) => {
        currentFilters.category = e.target.value;
        currentPage = 1;
        loadPatterns();
    });
    document.getElementById('filter-type').addEventListener('change', (e) => {
        currentFilters.pattern_type = e.target.value;
        currentPage = 1;
        loadPatterns();
    });
    document.getElementById('filter-object').addEventListener('change', (e) => {
        currentFilters.source_object = e.target.value;
        currentPage = 1;
        loadPatterns();
    });
    document.getElementById('filter-complexity').addEventListener('change', (e) => {
        const val = e.target.value;
        currentFilters.min_complexity = val || null;
        currentFilters.max_complexity = val || null;
        currentPage = 1;
        loadPatterns();
    });

    // AI Search button
    document.getElementById('ai-search-btn').addEventListener('click', runAISearch);

    // Shift+Enter for AI search
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            runAISearch();
        }
    });

    // Ingest button
    document.getElementById('ingest-btn').addEventListener('click', showIngestModal);

    // Modal close
    document.getElementById('modal-overlay').addEventListener('click', (e) => {
        if (e.target.id === 'modal-overlay') closeModal();
    });
}

// ── Load Data ──
async function loadFilters() {
    try {
        filtersData = await API.getFilters();
        populateDropdown('filter-category', filtersData.categories);
        populateDropdown('filter-type', filtersData.pattern_types);
        populateDropdown('filter-object', filtersData.objects);
    } catch (e) {
        // Filters may fail if DB is empty - that's OK
    }
}

function populateDropdown(id, options) {
    const select = document.getElementById(id);
    // Keep the first "All" option
    while (select.options.length > 1) select.remove(1);
    for (const opt of options) {
        const el = document.createElement('option');
        el.value = opt;
        el.textContent = opt;
        select.appendChild(el);
    }
}

async function loadStats() {
    try {
        const stats = await API.getStats();
        document.getElementById('stat-total').textContent = stats.total_patterns.toLocaleString();

        const breakdown = document.getElementById('stat-breakdown');
        breakdown.innerHTML = '';
        for (const cat of stats.by_category) {
            const badge = document.createElement('span');
            badge.className = 'stat-badge';
            badge.style.backgroundColor = cat.color + '22';
            badge.style.color = cat.color;
            badge.style.borderColor = cat.color;
            badge.textContent = `${cat.category}: ${cat.count}`;
            breakdown.appendChild(badge);
        }
    } catch (e) {
        document.getElementById('stat-total').textContent = '0';
    }
}

async function loadPatterns() {
    const grid = document.getElementById('pattern-grid');
    grid.innerHTML = '<div class="loading">Loading patterns...</div>';

    try {
        const params = { ...currentFilters, page: currentPage, page_size: 60 };
        const data = await API.getPatterns(params);

        if (data.total === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">\u2B22</div>
                    <h3>No patterns yet</h3>
                    <p>Click <strong>Ingest Project</strong> to scan an SFDX project and extract patterns.</p>
                </div>`;
            updatePagination(data);
            return;
        }

        grid.innerHTML = '';
        for (const pattern of data.patterns) {
            grid.appendChild(createPatternBlock(pattern));
        }
        updatePagination(data);
    } catch (e) {
        grid.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
    }
}

// ── Pattern Block Card ──
function createPatternBlock(pattern) {
    const block = document.createElement('div');
    block.className = 'pattern-block';
    block.dataset.id = pattern.id;

    const color = (filtersData && filtersData.colors[pattern.category]) || '#888';
    block.style.setProperty('--block-color', color);

    const icon = CATEGORY_ICONS[pattern.category] || '\u2B22';
    const complexityDots = '\u25CF'.repeat(pattern.complexity_score) +
                           '\u25CB'.repeat(5 - pattern.complexity_score);

    block.innerHTML = `
        <div class="block-header">
            <span class="block-icon">${icon}</span>
            <span class="block-fav ${pattern.favorited ? 'active' : ''}"
                  onclick="event.stopPropagation(); toggleFav(${pattern.id}, this)">\u2605</span>
        </div>
        <div class="block-type-badge">${pattern.pattern_type.replace(/_/g, ' ')}</div>
        <div class="block-name" title="${escapeHtml(pattern.name)}">${escapeHtml(truncate(pattern.name, 40))}</div>
        <div class="block-object">${escapeHtml(pattern.source_object)}</div>
        <div class="block-complexity" title="${COMPLEXITY_LABELS[pattern.complexity_score]}">
            ${complexityDots}
        </div>
    `;

    block.addEventListener('click', () => showPatternDetail(pattern.id));
    return block;
}

// ── Pattern Detail Modal ──
async function showPatternDetail(id) {
    const overlay = document.getElementById('modal-overlay');
    const content = document.getElementById('modal-content');
    content.innerHTML = '<div class="loading">Loading...</div>';
    overlay.classList.add('active');

    try {
        const p = await API.getPattern(id);
        const color = (filtersData && filtersData.colors[p.category]) || '#888';
        const icon = CATEGORY_ICONS[p.category] || '\u2B22';

        content.innerHTML = `
            <div class="detail-header" style="border-left: 4px solid ${color}">
                <span class="detail-icon" style="color:${color}">${icon}</span>
                <div>
                    <h2>${escapeHtml(p.name)}</h2>
                    <span class="detail-badge" style="background:${color}">${p.category}</span>
                    <span class="detail-badge">${p.pattern_type.replace(/_/g, ' ')}</span>
                    ${p.api_version ? `<span class="detail-badge">API v${p.api_version}</span>` : ''}
                </div>
            </div>
            <p class="detail-desc">${escapeHtml(p.description)}</p>

            <div class="detail-meta">
                <div><strong>Object:</strong> ${escapeHtml(p.source_object)}</div>
                <div><strong>Complexity:</strong> ${COMPLEXITY_LABELS[p.complexity_score]} (${p.complexity_score}/5)</div>
                <div><strong>Source File:</strong> ${escapeHtml(p.source_file)}</div>
                <div><strong>Uses:</strong> ${p.use_count}</div>
            </div>

            ${p.field_references.length ? `
            <div class="detail-section">
                <h3>Field References</h3>
                <div class="tag-list">
                    ${p.field_references.map(f => `<span class="tag field-tag">${escapeHtml(f)}</span>`).join('')}
                </div>
            </div>` : ''}

            <div class="detail-section">
                <h3>Tags</h3>
                <div class="tag-list">
                    ${p.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
                </div>
            </div>

            <div class="detail-section">
                <h3>Structure</h3>
                <pre class="structure-json">${escapeHtml(JSON.stringify(p.structure, null, 2))}</pre>
            </div>

            <div class="detail-actions">
                <button class="btn btn-copy" onclick="copyStructure(${p.id})">Copy JSON</button>
                <button class="btn btn-fav" onclick="toggleFav(${p.id})">
                    ${p.favorited ? 'Unfavorite' : 'Favorite'}
                </button>
            </div>
        `;
    } catch (e) {
        content.innerHTML = `<p class="error">Error loading pattern: ${e.message}</p>`;
    }
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
}

// ── Ingest Modal ──
async function showIngestModal() {
    const overlay = document.getElementById('modal-overlay');
    const content = document.getElementById('modal-content');

    content.innerHTML = `
        <h2>Ingest SFDX Project</h2>
        <p>Enter the path to an SFDX project directory to scan and extract patterns.</p>

        <div class="ingest-form">
            <input type="text" id="ingest-path" placeholder="D:\\sfdx\\bin\\MyProject"
                   value="D:\\sfdx\\bin\\" class="input-path" />
            <button class="btn btn-primary" id="btn-start-ingest" onclick="startIngest()">
                Scan & Extract
            </button>
        </div>

        <div id="project-list" class="project-list">
            <p class="loading">Loading available projects...</p>
        </div>

        <div id="ingest-progress" class="ingest-progress" style="display:none">
            <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
            <p id="progress-text">Starting...</p>
        </div>
    `;

    overlay.classList.add('active');

    // Load available projects
    try {
        const projects = await API.getProjects();
        const list = document.getElementById('project-list');
        if (projects.length === 0) {
            list.innerHTML = '<p>No SFDX projects found.</p>';
            return;
        }
        list.innerHTML = '<h3>Available Projects</h3>';
        for (const proj of projects) {
            const item = document.createElement('div');
            item.className = 'project-item';
            item.innerHTML = `
                <span class="project-name">${escapeHtml(proj.name)}</span>
                <button class="btn btn-sm" onclick="selectProject('${escapeHtml(proj.path.replace(/\\/g, '\\\\'))}')">Select</button>
            `;
            list.appendChild(item);
        }
    } catch (e) {
        document.getElementById('project-list').innerHTML =
            `<p>Could not load projects: ${e.message}</p>`;
    }
}

function selectProject(path) {
    document.getElementById('ingest-path').value = path;
}

async function startIngest() {
    const path = document.getElementById('ingest-path').value.trim();
    if (!path) return;

    const btn = document.getElementById('btn-start-ingest');
    btn.disabled = true;
    btn.textContent = 'Scanning...';

    const progressDiv = document.getElementById('ingest-progress');
    progressDiv.style.display = 'block';
    document.getElementById('progress-text').textContent = 'Scanning project...';

    try {
        const result = await API.ingestProject(path);

        document.getElementById('progress-fill').style.width = '100%';
        document.getElementById('progress-text').innerHTML = `
            <strong>Done!</strong> Extracted ${result.patterns_found.toLocaleString()} patterns.
            ${result.errors.length ? `<br>${result.errors.length} errors encountered.` : ''}
        `;

        // Refresh the main view
        await loadFilters();
        await loadStats();
        await loadPatterns();
    } catch (e) {
        document.getElementById('progress-text').innerHTML =
            `<span class="error">Error: ${e.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Scan & Extract';
    }
}

// ── AI Search ──
async function runAISearch() {
    const searchInput = document.getElementById('search-input');
    const query = searchInput.value.trim();
    if (!query) return;

    const btn = document.getElementById('ai-search-btn');
    const searchBox = document.querySelector('.search-box');
    const grid = document.getElementById('pattern-grid');

    // UI feedback
    btn.disabled = true;
    btn.innerHTML = '<span class="ai-icon">&#x23F3;</span> Thinking...';
    searchBox.classList.add('ai-mode');
    grid.innerHTML = '<div class="loading">AI is searching your patterns...</div>';

    try {
        const data = await API.searchNL(query);

        if (data.results && data.results.length > 0) {
            grid.innerHTML = '';
            data.results.forEach((pattern, idx) => {
                const block = createPatternBlock(pattern);
                // Add AI rank badge
                const rankBadge = document.createElement('span');
                rankBadge.className = 'ai-rank';
                rankBadge.textContent = `#${idx + 1}`;
                block.appendChild(rankBadge);
                grid.appendChild(block);
            });
            // Update pagination area with AI result info
            document.getElementById('pagination').innerHTML =
                `<span class="page-info">${data.total} patterns found</span>` +
                `<span class="search-method ai">AI Search</span>`;
        } else {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#x2728;</div>
                    <h3>No AI matches found</h3>
                    <p>Try rephrasing your query, or use keyword search for broader results.</p>
                </div>`;
            document.getElementById('pagination').innerHTML = '';
        }
    } catch (e) {
        grid.innerHTML = `
            <div class="empty-state">
                <p class="error">${escapeHtml(e.message)}</p>
                <p style="margin-top:10px;color:var(--text-muted)">
                    AI search requires an Anthropic API key.<br>
                    Set ANTHROPIC_API_KEY environment variable and restart.
                </p>
            </div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="ai-icon">&#x2728;</span> Ask AI';
        searchBox.classList.remove('ai-mode');
    }
}

// ── Actions ──
async function toggleFav(id, el) {
    try {
        const result = await API.toggleFavorite(id);
        if (el) {
            el.classList.toggle('active', result.favorited);
        }
    } catch (e) {
        console.error('Failed to toggle favorite:', e);
    }
}

async function copyStructure(id) {
    try {
        const p = await API.getPattern(id);
        await navigator.clipboard.writeText(JSON.stringify(p.structure, null, 2));
        // Brief visual feedback
        const btn = document.querySelector('.btn-copy');
        if (btn) {
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = 'Copy JSON', 1500);
        }
    } catch (e) {
        console.error('Copy failed:', e);
    }
}

// ── Pagination ──
function updatePagination(data) {
    const pag = document.getElementById('pagination');
    if (data.pages <= 1) {
        pag.innerHTML = '';
        return;
    }

    let html = '';
    if (data.page > 1) {
        html += `<button class="btn btn-sm" onclick="goPage(${data.page - 1})">Prev</button>`;
    }
    html += `<span class="page-info">Page ${data.page} of ${data.pages} (${data.total.toLocaleString()} patterns)</span>`;
    if (data.page < data.pages) {
        html += `<button class="btn btn-sm" onclick="goPage(${data.page + 1})">Next</button>`;
    }
    pag.innerHTML = html;
}

function goPage(page) {
    currentPage = page;
    loadPatterns();
    window.scrollTo(0, 0);
}

// ── Utilities ──
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;');
}

function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '...' : str;
}
