// Color scheme for node types – matches Matplotlib palette
const NODE_COLOR_MAP = {
    "User": "#FF7043",
    "JobPosting": "#FFA726",
    "JobRoleCanonical": "#B0BEC5",
    "JobRoleRaw": "#CFD8DC",
    "Company": "#90CAF9",
    "Location": "#81C784",
    "ExperienceBucket": "#F48FB1",
    "SalaryBucket": "#BA68C8",
    "Skill": "#FFD54F",
    "SkillRaw": "#FFEB3B"
};

// Important edges for highlighting
const IMPORTANT_EDGES = {
    "MATCHES_JOB": true,
    "SIMILAR_TO": true,
    "HAS_SKILL": true,
    "REQUIRES_SKILL": true,
    "LOCATED_IN": true,
    "POSTED_BY": true,
    "HAS_ROLE_CANONICAL": true
};

document.addEventListener('DOMContentLoaded', () => {
    const graphTab = document.querySelector('[data-tab="graph"]');
    if (graphTab) {
        graphTab.addEventListener('click', initializeGraph);
    }
});

let graphInitialized = false;
let network = null;

function initGraphTab() {
    const graphTab = document.querySelector('[onclick*="Graph"]');
    if (graphTab) {
        graphTab.addEventListener('click', function () {
            setTimeout(initializeGraph, 100);
        });
    }
}

document.addEventListener('DOMContentLoaded', initGraphTab);

// Simple debounce - prevent spam refresh
let refreshTimeout = null;

function debounceRefresh() {
    if (refreshTimeout) clearTimeout(refreshTimeout);
    refreshTimeout = setTimeout(() => initializeGraph(true), 500);
}

async function initializeGraph(force = false) {
    const shouldForce = force === true;

    if (!shouldForce && graphInitialized && network) {
        return;
    }

    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) {
        console.error('graph-container not found');
        return;
    }

    if (typeof vis === 'undefined') {
        graphContainer.innerHTML = `
            <div style="padding: 20px; text-align: center;">
                <i class="bi bi-graph-up-arrow fs-1 text-danger mb-3"></i>
                <h5 style="color: red;">Vis.js library failed to load</h5>
                <p>Please refresh the page (F5) or check your internet connection.</p>
                <button class="btn btn-primary btn-sm" onclick="location.reload()">
                    <i class="bi bi-arrow-clockwise me-1"></i>Retry
                </button>
            </div>`;
        return;
    }

    graphContainer.innerHTML = '<div style="padding: 20px;">Loading graph visualization...</div>';

    try {
        const response = await fetch('/graph');

        if (!response.ok) {
            let detail = '';
            try {
                const errData = await response.json();
                detail = errData?.error ? `: ${errData.error}` : '';
            } catch (_) {
                // Keep generic message when backend does not return JSON.
            }
            graphContainer.innerHTML = `<div style="padding: 20px; color: red;">Failed to load graph (${response.status})${detail}</div>`;
            return;
        }

        const data = await response.json();

        if (data.error) {
            graphContainer.innerHTML = `<div style="padding: 20px; color: red;">${data.error}</div>`;
            return;
        }

        if (!data.nodes || data.nodes.length === 0) {
            graphContainer.innerHTML = '<div style="padding: 20px;">No graph data available. Please upload a CV first.</div>';
            return;
        }

        console.log(`Rendering graph: ${data.nodes_count} nodes, ${data.links_count} edges`);

        graphContainer.innerHTML = '';

        // ── Scale factor for layout ──
        const SCALE = 550;

        function isColorDark(hexcolor) {
            if (!hexcolor || hexcolor.length < 7) return false;
            try {
                const r = parseInt(hexcolor.slice(1, 3), 16);
                const g = parseInt(hexcolor.slice(3, 5), 16);
                const b = parseInt(hexcolor.slice(5, 7), 16);
                const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
                return (yiq < 128);
            } catch (e) {
                return false;
            }
        }

        // ── Process nodes ──
        const visNodes = data.nodes.map(node => {
            const nodeType = node.ntype || "Other";
            let color = node.color || NODE_COLOR_MAP[nodeType] || "#E0E0E0";

            // Node size by type
            let size = 22;
            if (nodeType === "User")       size = 45;
            if (nodeType === "JobPosting") size = 38; // Slightly larger for jobs
            if (nodeType === "Skill")      size = 24;
            if (nodeType === "Company")    size = 28;
            if (nodeType === "Location")   size = 24;

            return {
                id: node.id,
                label: nodeType === 'JobPosting'
                    ? (node.label || node.full_title || 'Job')
                    : (node.label || ''),
                title: `${nodeType}: ${node.full_title || node.label || ''}${node.score ? ' (Score: ' + (node.score*100).toFixed(0) + '%)' : ''}`,
                size: size,
                color: {
                    background: color,
                    border: nodeType === 'User' ? '#d32f2f' : (node.shadow || '#555'),
                    highlight: { background: color, border: '#14f30c' }
                },
                x:  node.x * SCALE,
                y: -node.y * SCALE,
                fixed: { x: true, y: true },
                font: {
                    // Job titles: always black text per request. Node background remains heatmap-driven.
                    color: nodeType === 'User' ? '#ffffff' : (nodeType === 'JobPosting' ? '#000000' : '#333333'),
                    face: 'Arial',
                    background: 'transparent',
                    strokeWidth: 0,
                    strokeColor: 'transparent'
                },
                borderWidth: nodeType === 'User' ? 3 : 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.15)',
                    size: 8,
                    x: 3,
                    y: 3
                }
            };
        });

        // ── Process edges ──
        const visEdges = data.links.map(edge => {
            const rel = edge.rel.replace(/_/g, ' ');

            // Label: show score for all important relationships
            let label = '';
            if (edge.rel === 'MATCHES_JOB' && edge.score != null) {
                label = `MATCH (${edge.score.toFixed(3)})`;
            } else if (edge.rel === 'SIMILAR_TO' && edge.score != null) {
                label = `SIMILAR (${edge.score.toFixed(3)})`;
            } else if (edge.rel === 'HAS_SKILL' && edge.prob != null) {
                label = `${rel} (${edge.prob.toFixed(3)})`;
            } else if (edge.rel === 'REQUIRES_SKILL' && edge.prob != null) {
                label = `${rel} (${edge.prob.toFixed(3)})`;
            } else {
                label = rel;
            }

            // Style per edge type
            let color = '#aaa';
            let width = 1;
            let fontSize = 9;
            let dashes = [5, 5];  // default: thin dashed

            if (edge.rel === 'MATCHES_JOB') {
                color = '#000';
                width = 5;
                fontSize = 12;
                dashes = false;           // solid thick
            } else if (edge.rel === 'SIMILAR_TO') {
                color = '#555';
                width = 3;
                fontSize = 11;
                dashes = false;           // solid medium
            } else if (edge.rel === 'REQUIRES_SKILL' || edge.rel === 'HAS_SKILL') {
                color = '#f57f17';
                width = 2;
                fontSize = 10;
                dashes = [3, 3];
            } else {
                // All other relationships: thin dashed grey
                color = '#999';
                width = 1.2;
                fontSize = 9;
                dashes = [5, 5];
            }

            return {
                from: edge.source,
                to: edge.target,
                label: label,
                title: rel,
                font: {
                    align: 'middle',
                    size: fontSize,
                    color: '#333',
                    face: 'Arial',
                    background: '#ffffff',
                    strokeWidth: 0
                },
                color: { color: color, highlight: '#e53935' },
                width: width,
                // No arrows – undirected look like Matplotlib
                arrows: { to: { enabled: false } },
                dashes: dashes,
                // Straight lines, no curves
                smooth: false
            };
        });

        const nodes = new vis.DataSet(visNodes);
        const edges = new vis.DataSet(visEdges);

        const networkData = { nodes, edges };
        const options = {
            layout: { hierarchical: false },
            physics: {
                enabled: false,
                stabilization: { iterations: 0 }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                zoomView: true,
                dragView: true,
                navigationButtons: true,
                keyboard: true
            },
            nodes: {
                shape: 'dot',
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.12)',
                    size: 8,
                    x: 3,
                    y: 3
                }
            },
            edges: {
                shadow: false,
                font: {
                    strokeWidth: 0,
                    background: '#ffffff'
                }
            }
        };

        network = new vis.Network(graphContainer, networkData, options);

        graphInitialized = true;
        console.log('Graph visualization initialized successfully');
        console.log(`Total nodes in graph: ${data.total_nodes}, Total edges: ${data.total_edges}`);

    } catch (error) {
        console.error('Graph error:', error);
        graphContainer.innerHTML = `<div style="padding: 20px; color: red;">Error: ${error.message}</div>`;
    }
}
