import * as vscode from 'vscode';

// ── API Client ──

function getServerUrl(): string {
    return vscode.workspace.getConfiguration('blackboxaf').get('serverUrl', 'http://localhost:8000');
}

async function apiGet(path: string): Promise<any> {
    const url = `${getServerUrl()}${path}`;
    const res = await fetch(url);
    if (!res.ok) {
        const err: any = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `API error: ${res.status}`);
    }
    return res.json();
}

async function apiPost(path: string, body?: any): Promise<any> {
    const url = `${getServerUrl()}${path}`;
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
        const err: any = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `API error: ${res.status}`);
    }
    return res.json();
}


// ── Extension Activation ──

export function activate(context: vscode.ExtensionContext) {
    // Register the webview provider for the sidebar
    const provider = new PatternBrowserProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('blackboxaf.patternBrowser', provider)
    );

    // Register the favorites tree view
    const favoritesProvider = new FavoritesTreeProvider();
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('blackboxaf.favorites', favoritesProvider)
    );

    // Commands
    context.subscriptions.push(
        vscode.commands.registerCommand('blackboxaf.searchPatterns', async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Search patterns...',
                placeHolder: 'e.g., approval flow, opportunity validation, account fields',
            });
            if (query) {
                provider.search(query);
            }
        }),

        vscode.commands.registerCommand('blackboxaf.insertPattern', async (patternId?: number) => {
            if (!patternId) {
                const idStr = await vscode.window.showInputBox({
                    prompt: 'Enter pattern ID to insert',
                    placeHolder: '42',
                });
                if (!idStr) { return; }
                patternId = parseInt(idStr, 10);
            }
            await insertPatternAtCursor(patternId);
        }),

        vscode.commands.registerCommand('blackboxaf.composeFlowSolution', async () => {
            const requirement = await vscode.window.showInputBox({
                prompt: 'Describe what you need (Agentforce-style)',
                placeHolder: 'e.g., Build approval process for Opportunity with manager notification',
            });
            if (!requirement) { return; }

            const targetObject = await vscode.window.showInputBox({
                prompt: 'Target Salesforce object',
                placeHolder: 'Opportunity',
                value: vscode.workspace.getConfiguration('blackboxaf').get('defaultObject', ''),
            });
            if (!targetObject) { return; }

            await composeSolution(requirement, targetObject);
        }),

        vscode.commands.registerCommand('blackboxaf.refreshPatterns', () => {
            provider.refresh();
            favoritesProvider.refresh();
        }),

        vscode.commands.registerCommand('blackboxaf.setServerUrl', async () => {
            const url = await vscode.window.showInputBox({
                prompt: 'BlackBoxAF server URL',
                value: getServerUrl(),
            });
            if (url) {
                await vscode.workspace.getConfiguration('blackboxaf').update('serverUrl', url, true);
                provider.refresh();
            }
        })
    );
}

export function deactivate() {}


// ── Insert Pattern ──

async function insertPatternAtCursor(patternId: number) {
    try {
        const pattern = await apiGet(`/api/patterns/${patternId}`);
        const editor = vscode.window.activeTextEditor;

        if (!editor) {
            // No editor open - show in new document
            const doc = await vscode.workspace.openTextDocument({
                content: JSON.stringify(pattern.structure, null, 2),
                language: 'json',
            });
            await vscode.window.showTextDocument(doc);
            return;
        }

        const structureJson = JSON.stringify(pattern.structure, null, 2);

        // Determine format based on file type
        const fileName = editor.document.fileName;
        let content: string;

        if (fileName.endsWith('.cls') || fileName.endsWith('.trigger')) {
            // Apex - insert as comment + structure reference
            content = `// Pattern: ${pattern.name} (BlackBoxAF #${pattern.id})\n` +
                      `// Category: ${pattern.category} | Complexity: ${pattern.complexity_score}/5\n` +
                      `// Fields: ${pattern.field_references.join(', ')}\n` +
                      `/*\n${structureJson}\n*/\n`;
        } else if (fileName.endsWith('.xml') || fileName.endsWith('-meta.xml')) {
            // XML metadata - insert structure as XML comment
            content = `<!-- Pattern: ${pattern.name} (BlackBoxAF #${pattern.id}) -->\n` +
                      `<!-- ${pattern.description} -->\n` +
                      `<!-- Structure:\n${structureJson}\n-->\n`;
        } else {
            // Default JSON
            content = structureJson;
        }

        await editor.edit(editBuilder => {
            editBuilder.insert(editor.selection.active, content);
        });

        vscode.window.showInformationMessage(
            `Inserted pattern: ${pattern.name}`
        );
    } catch (e: any) {
        vscode.window.showErrorMessage(`Failed to insert pattern: ${e.message}`);
    }
}


// ── Compose Solution ──

async function composeSolution(requirement: string, targetObject: string) {
    await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: 'BlackBoxAF: Composing solution...' },
        async () => {
            try {
                // Search across categories
                const categories = ['Flow Logic', 'Data Validation', 'Data Model', 'Page Layout'];
                const allResults: any[] = [];

                for (const cat of categories) {
                    const data = await apiGet(
                        `/api/patterns?category=${encodeURIComponent(cat)}` +
                        `&q=${encodeURIComponent(requirement)}` +
                        `&page_size=5`
                    );
                    for (const p of data.patterns) {
                        allResults.push({ ...p, _category: cat });
                    }
                }

                // Also search by target object
                const objData = await apiGet(
                    `/api/patterns?source_object=${encodeURIComponent(targetObject)}&page_size=10`
                );
                for (const p of objData.patterns) {
                    if (!allResults.find(r => r.id === p.id)) {
                        allResults.push({ ...p, _category: p.category });
                    }
                }

                if (allResults.length === 0) {
                    vscode.window.showWarningMessage('No matching patterns found for this requirement.');
                    return;
                }

                // Create solution document
                const lines: string[] = [
                    `# BlackBoxAF Solution Blueprint`,
                    `## Requirement: ${requirement}`,
                    `## Target Object: ${targetObject}`,
                    ``,
                    `Found ${allResults.length} relevant patterns:`,
                    ``,
                ];

                let currentCat = '';
                for (const p of allResults) {
                    if (p._category !== currentCat) {
                        currentCat = p._category;
                        lines.push(`### ${currentCat}`, '');
                    }
                    lines.push(
                        `- **[${p.id}] ${p.name}** (${p.source_object}, complexity ${p.complexity_score}/5)`,
                        `  ${p.description || ''}`,
                        `  Tags: ${(p.tags || []).join(', ')}`,
                        ''
                    );
                }

                lines.push(
                    '',
                    '---',
                    '## Next Steps',
                    '1. Review patterns above and select the ones that fit your requirement',
                    '2. Use `BlackBoxAF: Insert Pattern at Cursor` (Ctrl+Shift+B) to insert pattern structures',
                    '3. Adapt field references to your target org',
                    '4. Deploy via SFDX',
                );

                const doc = await vscode.workspace.openTextDocument({
                    content: lines.join('\n'),
                    language: 'markdown',
                });
                await vscode.window.showTextDocument(doc);

            } catch (e: any) {
                vscode.window.showErrorMessage(`Compose failed: ${e.message}`);
            }
        }
    );
}


// ── Sidebar Webview Provider ──

class PatternBrowserProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    resolveWebviewView(view: vscode.WebviewView) {
        this._view = view;

        view.webview.options = {
            enableScripts: true,
        };

        view.webview.html = this._getHtml();

        // Handle messages from webview
        view.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.type) {
                case 'search':
                    await this._handleSearch(msg.query);
                    break;
                case 'getPattern':
                    await this._handleGetPattern(msg.id);
                    break;
                case 'insertPattern':
                    await insertPatternAtCursor(msg.id);
                    break;
                case 'refresh':
                    await this._loadInitialData();
                    break;
            }
        });

        // Load initial data
        this._loadInitialData();
    }

    search(query: string) {
        this._view?.webview.postMessage({ type: 'search', query });
    }

    refresh() {
        this._loadInitialData();
    }

    private async _loadInitialData() {
        try {
            const [stats, filters] = await Promise.all([
                apiGet('/api/stats'),
                apiGet('/api/filters'),
            ]);
            this._view?.webview.postMessage({ type: 'init', stats, filters });

            const patterns = await apiGet('/api/patterns?page_size=30');
            this._view?.webview.postMessage({ type: 'patterns', data: patterns });
        } catch (e: any) {
            this._view?.webview.postMessage({
                type: 'error',
                message: `Cannot connect to BlackBoxAF server at ${getServerUrl()}. Is it running?`
            });
        }
    }

    private async _handleSearch(query: string) {
        try {
            const data = await apiGet(`/api/patterns?q=${encodeURIComponent(query)}&page_size=30`);
            this._view?.webview.postMessage({ type: 'patterns', data });
        } catch (e: any) {
            this._view?.webview.postMessage({ type: 'error', message: e.message });
        }
    }

    private async _handleGetPattern(id: number) {
        try {
            const pattern = await apiGet(`/api/patterns/${id}`);
            this._view?.webview.postMessage({ type: 'patternDetail', pattern });
        } catch (e: any) {
            this._view?.webview.postMessage({ type: 'error', message: e.message });
        }
    }

    private _getHtml(): string {
        return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    :root {
        --orange: #F08734;
        --dark: #171717;
        --gray: #8E8E8E;
    }
    body {
        font-family: var(--vscode-font-family);
        font-size: var(--vscode-font-size);
        color: var(--vscode-foreground);
        background: var(--vscode-sideBar-background);
        padding: 0;
        margin: 0;
    }
    .header {
        padding: 8px 12px;
        border-bottom: 1px solid var(--vscode-panel-border);
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .header .logo {
        font-weight: bold;
        font-size: 13px;
    }
    .header .logo span { color: var(--orange); }
    .stats {
        font-size: 11px;
        color: var(--vscode-descriptionForeground);
        padding: 4px 12px;
    }
    .search-container {
        padding: 8px 12px;
    }
    .search-container input {
        width: 100%;
        box-sizing: border-box;
        padding: 6px 8px;
        border: 1px solid var(--vscode-input-border);
        background: var(--vscode-input-background);
        color: var(--vscode-input-foreground);
        border-radius: 3px;
        font-size: 12px;
    }
    .search-container input:focus {
        outline: 1px solid var(--orange);
        border-color: var(--orange);
    }
    .filter-bar {
        padding: 0 12px 8px;
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
    }
    .filter-bar select {
        font-size: 11px;
        padding: 3px 4px;
        background: var(--vscode-dropdown-background);
        color: var(--vscode-dropdown-foreground);
        border: 1px solid var(--vscode-dropdown-border);
        border-radius: 3px;
        flex: 1;
        min-width: 0;
    }
    .pattern-list {
        overflow-y: auto;
        max-height: calc(100vh - 180px);
    }
    .pattern-item {
        padding: 8px 12px;
        border-bottom: 1px solid var(--vscode-panel-border);
        cursor: pointer;
        display: flex;
        gap: 8px;
        align-items: flex-start;
    }
    .pattern-item:hover {
        background: var(--vscode-list-hoverBackground);
    }
    .pattern-icon {
        font-size: 18px;
        flex-shrink: 0;
        width: 24px;
        text-align: center;
    }
    .pattern-info {
        flex: 1;
        min-width: 0;
    }
    .pattern-name {
        font-size: 12px;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .pattern-meta {
        font-size: 10px;
        color: var(--vscode-descriptionForeground);
        margin-top: 2px;
    }
    .pattern-badge {
        display: inline-block;
        padding: 1px 5px;
        border-radius: 3px;
        font-size: 10px;
        margin-right: 4px;
    }
    .pattern-actions {
        display: flex;
        gap: 4px;
        flex-shrink: 0;
    }
    .btn-insert {
        background: var(--orange);
        color: #fff;
        border: none;
        padding: 3px 8px;
        border-radius: 3px;
        font-size: 10px;
        cursor: pointer;
    }
    .btn-insert:hover { opacity: 0.85; }
    .complexity {
        font-size: 10px;
        letter-spacing: 1px;
    }
    .detail-panel {
        padding: 12px;
        display: none;
        border-top: 2px solid var(--orange);
    }
    .detail-panel.active { display: block; }
    .detail-panel h3 {
        margin: 0 0 8px;
        font-size: 13px;
    }
    .detail-panel pre {
        font-size: 11px;
        background: var(--vscode-textCodeBlock-background);
        padding: 8px;
        border-radius: 4px;
        overflow-x: auto;
        max-height: 300px;
    }
    .detail-back {
        cursor: pointer;
        color: var(--orange);
        font-size: 11px;
        margin-bottom: 8px;
        display: inline-block;
    }
    .tag {
        display: inline-block;
        padding: 1px 6px;
        margin: 2px;
        border-radius: 3px;
        font-size: 10px;
        background: var(--vscode-badge-background);
        color: var(--vscode-badge-foreground);
    }
    .empty {
        text-align: center;
        padding: 24px 12px;
        color: var(--vscode-descriptionForeground);
    }
    .empty .icon { font-size: 32px; margin-bottom: 8px; }
    .error-msg {
        color: var(--vscode-errorForeground);
        padding: 12px;
        font-size: 12px;
    }
</style>
</head>
<body>

<div class="header">
    <span class="logo">BlackBox<span>AF</span></span>
</div>

<div class="stats" id="stats"></div>

<div class="search-container">
    <input type="text" id="search" placeholder="Search patterns... (Ctrl+Shift+B)">
</div>

<div class="filter-bar">
    <select id="filter-category"><option value="">All Categories</option></select>
    <select id="filter-object"><option value="">All Objects</option></select>
</div>

<div id="detail-panel" class="detail-panel"></div>
<div id="pattern-list" class="pattern-list">
    <div class="empty">
        <div class="icon">\u23F3</div>
        Connecting to BlackBoxAF...
    </div>
</div>

<script>
const vscode = acquireVsCodeApi();

const ICONS = {
    'Flow Logic': '\u26A1', 'Data Validation': '\u2714',
    'Data Model': '\u2B22', 'UI Component': '\u25A3',
    'Reporting': '\u2637', 'Page Layout': '\u2B1A', 'Apex Logic': '\u2699',
};

let currentFilters = {};
let allPatterns = [];
let colors = {};

// Search
const searchInput = document.getElementById('search');
let searchTimer;
searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        vscode.postMessage({ type: 'search', query: searchInput.value });
    }, 300);
});

// Filters
document.getElementById('filter-category').addEventListener('change', (e) => {
    currentFilters.category = e.target.value;
    doSearch();
});
document.getElementById('filter-object').addEventListener('change', (e) => {
    currentFilters.source_object = e.target.value;
    doSearch();
});

function doSearch() {
    vscode.postMessage({
        type: 'search',
        query: searchInput.value,
        ...currentFilters,
    });
}

// Render patterns
function renderPatterns(data) {
    const list = document.getElementById('pattern-list');
    if (!data.patterns || data.patterns.length === 0) {
        list.innerHTML = '<div class="empty"><div class="icon">\u2B22</div>No patterns found</div>';
        return;
    }

    allPatterns = data.patterns;
    list.innerHTML = '';

    for (const p of data.patterns) {
        const color = colors[p.category] || '#888';
        const icon = ICONS[p.category] || '\u2B22';
        const dots = '\u25CF'.repeat(p.complexity_score) + '\u25CB'.repeat(5 - p.complexity_score);

        const item = document.createElement('div');
        item.className = 'pattern-item';
        item.innerHTML = \`
            <span class="pattern-icon" style="color:\${color}">\${icon}</span>
            <div class="pattern-info">
                <div class="pattern-name">\${esc(p.name)}</div>
                <div class="pattern-meta">
                    <span class="pattern-badge" style="background:\${color}22;color:\${color}">\${p.pattern_type.replace(/_/g, ' ')}</span>
                    \${esc(p.source_object)}
                    <span class="complexity">\${dots}</span>
                </div>
            </div>
            <div class="pattern-actions">
                <button class="btn-insert" data-id="\${p.id}" title="Insert into editor">\u2B9E</button>
            </div>
        \`;

        item.querySelector('.pattern-info').addEventListener('click', () => {
            vscode.postMessage({ type: 'getPattern', id: p.id });
        });

        item.querySelector('.btn-insert').addEventListener('click', (e) => {
            e.stopPropagation();
            vscode.postMessage({ type: 'insertPattern', id: p.id });
        });

        list.appendChild(item);
    }
}

// Render detail
function renderDetail(pattern) {
    const panel = document.getElementById('detail-panel');
    const list = document.getElementById('pattern-list');
    const color = colors[pattern.category] || '#888';

    panel.innerHTML = \`
        <span class="detail-back" id="back-btn">\u2190 Back to list</span>
        <h3 style="border-left:3px solid \${color};padding-left:8px">\${esc(pattern.name)}</h3>
        <div class="pattern-meta" style="margin-bottom:8px">
            <span class="pattern-badge" style="background:\${color}22;color:\${color}">\${pattern.category}</span>
            <span class="pattern-badge">\${pattern.pattern_type.replace(/_/g, ' ')}</span>
            Object: \${esc(pattern.source_object)} | Complexity: \${pattern.complexity_score}/5
        </div>
        <p style="font-size:12px">\${esc(pattern.description)}</p>
        \${pattern.field_references.length ? \`
            <div style="margin:8px 0">
                <strong style="font-size:11px">Fields:</strong><br>
                \${pattern.field_references.map(f => \`<span class="tag">\${esc(f)}</span>\`).join('')}
            </div>
        \` : ''}
        <div style="margin:8px 0">
            <strong style="font-size:11px">Tags:</strong><br>
            \${pattern.tags.map(t => \`<span class="tag">\${esc(t)}</span>\`).join('')}
        </div>
        <div style="margin:8px 0">
            <strong style="font-size:11px">Structure:</strong>
            <pre>\${esc(JSON.stringify(pattern.structure, null, 2))}</pre>
        </div>
        <button class="btn-insert" style="padding:6px 16px;font-size:12px" id="detail-insert">
            \u2B9E Insert at Cursor
        </button>
    \`;

    panel.classList.add('active');
    list.style.display = 'none';

    document.getElementById('back-btn').addEventListener('click', () => {
        panel.classList.remove('active');
        list.style.display = 'block';
    });

    document.getElementById('detail-insert').addEventListener('click', () => {
        vscode.postMessage({ type: 'insertPattern', id: pattern.id });
    });
}

function populateDropdown(id, options) {
    const select = document.getElementById(id);
    while (select.options.length > 1) select.remove(1);
    for (const opt of options) {
        const el = document.createElement('option');
        el.value = opt;
        el.textContent = opt;
        select.appendChild(el);
    }
}

function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// Handle messages from extension
window.addEventListener('message', (event) => {
    const msg = event.data;
    switch (msg.type) {
        case 'init':
            document.getElementById('stats').textContent =
                msg.stats.total_patterns.toLocaleString() + ' patterns in vault';
            populateDropdown('filter-category', msg.filters.categories);
            populateDropdown('filter-object', msg.filters.objects);
            colors = msg.filters.colors || {};
            break;
        case 'patterns':
            renderPatterns(msg.data);
            break;
        case 'patternDetail':
            renderDetail(msg.pattern);
            break;
        case 'search':
            searchInput.value = msg.query;
            doSearch();
            break;
        case 'error':
            document.getElementById('pattern-list').innerHTML =
                '<div class="error-msg">' + esc(msg.message) + '</div>';
            break;
    }
});
</script>
</body>
</html>`;
    }
}


// ── Favorites Tree View ──

class FavoritesTreeProvider implements vscode.TreeDataProvider<PatternTreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<PatternTreeItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    refresh() {
        this._onDidChangeTreeData.fire(undefined);
    }

    async getChildren(): Promise<PatternTreeItem[]> {
        try {
            const data = await apiGet('/api/patterns?favorited=true&page_size=50');
            return data.patterns.map((p: any) =>
                new PatternTreeItem(p.id, p.name, p.category, p.source_object, p.complexity_score)
            );
        } catch {
            return [];
        }
    }

    getTreeItem(element: PatternTreeItem): vscode.TreeItem {
        return element;
    }
}

const CATEGORY_ICONS: Record<string, string> = {
    'Flow Logic': '\u26A1',
    'Data Validation': '\u2714',
    'Data Model': '\u2B22',
    'UI Component': '\u25A3',
    'Reporting': '\u2637',
    'Page Layout': '\u2B1A',
    'Apex Logic': '\u2699',
};

class PatternTreeItem extends vscode.TreeItem {
    constructor(
        public readonly patternId: number,
        public readonly patternName: string,
        public readonly category: string,
        public readonly sourceObject: string,
        public readonly complexity: number,
    ) {
        super(patternName, vscode.TreeItemCollapsibleState.None);
        const icon = CATEGORY_ICONS[category] || '\u2B22';
        this.description = `${sourceObject} ${'*'.repeat(complexity)}`;
        this.tooltip = `${icon} ${patternName}\n${category} | ${sourceObject} | Complexity: ${complexity}/5`;
        this.command = {
            command: 'blackboxaf.insertPattern',
            title: 'Insert Pattern',
            arguments: [patternId],
        };
    }
}
