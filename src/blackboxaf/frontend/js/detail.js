/**
 * Pattern detail page logic (standalone view)
 */
document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (!id) {
        document.getElementById('detail-root').innerHTML = '<p>No pattern ID specified.</p>';
        return;
    }

    try {
        const pattern = await API.getPattern(id);
        renderDetail(pattern);
    } catch (e) {
        document.getElementById('detail-root').innerHTML = `<p>Error: ${e.message}</p>`;
    }
});

function renderDetail(p) {
    document.title = `${p.name} - BlackBoxAF`;
    document.getElementById('detail-root').innerHTML = `
        <h1>${p.name}</h1>
        <p>${p.description}</p>
        <pre>${JSON.stringify(p.structure, null, 2)}</pre>
    `;
}
