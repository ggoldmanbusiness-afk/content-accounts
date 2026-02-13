import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def generate_dashboard(reports: dict, output_dir: Path = None) -> Path:
    """Generate a self-contained HTML dashboard from analysis reports."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    output_path = output_dir / f"dashboard_{timestamp}.html"

    accounts_json = json.dumps(reports, default=str)
    generated_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-deep: #0a0a0c;
            --bg-surface: #111114;
            --bg-card: #18181c;
            --bg-elevated: #1f1f24;
            --border-subtle: #2a2a30;
            --border-accent: #3d3d44;
            --text-primary: #f0efe8;
            --text-secondary: #9a9a9e;
            --text-muted: #5c5c62;
            --accent-warm: #e8c37e;
            --accent-warm-dim: #c4a05a;
            --accent-rose: #d4756a;
            --accent-sage: #7eb89a;
            --accent-blue: #6a9fd4;
            --accent-lavender: #a488c7;
            --chart-1: #e8c37e;
            --chart-2: #7eb89a;
            --chart-3: #6a9fd4;
            --chart-4: #d4756a;
            --chart-5: #a488c7;
            --chart-6: #c4a05a;
            --serif: 'Instrument Serif', Georgia, serif;
            --sans: 'DM Sans', -apple-system, sans-serif;
            --mono: 'JetBrains Mono', monospace;
            --radius: 2px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: var(--sans);
            background: var(--bg-deep);
            color: var(--text-primary);
            font-size: 14px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        /* --- HEADER --- */
        .masthead {{
            border-bottom: 1px solid var(--border-subtle);
            padding: 2rem 3rem 1.5rem;
        }}
        .masthead-inner {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}
        .masthead h1 {{
            font-family: var(--serif);
            font-size: 2rem;
            font-weight: 400;
            letter-spacing: -0.02em;
            color: var(--text-primary);
        }}
        .masthead h1 em {{
            color: var(--accent-warm);
        }}
        .masthead-meta {{
            font-family: var(--mono);
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}

        /* --- LAYOUT --- */
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 3rem 4rem;
        }}

        /* --- TABS --- */
        .tab-strip {{
            display: flex;
            gap: 0;
            border-bottom: 1px solid var(--border-subtle);
            margin-top: 0;
            padding: 0;
            overflow-x: auto;
        }}
        .tab {{
            padding: 1rem 1.5rem 0.85rem;
            font-family: var(--mono);
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
            white-space: nowrap;
        }}
        .tab:hover {{ color: var(--text-secondary); }}
        .tab.active {{
            color: var(--accent-warm);
            border-bottom-color: var(--accent-warm);
        }}

        /* --- STAT CARDS --- */
        .stat-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1px;
            background: var(--border-subtle);
            border: 1px solid var(--border-subtle);
            margin-top: 2.5rem;
        }}
        .stat-card {{
            background: var(--bg-surface);
            padding: 1.5rem 1.75rem;
        }}
        .stat-label {{
            font-family: var(--mono);
            font-size: 10px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}
        .stat-value {{
            font-family: var(--serif);
            font-size: 2.2rem;
            font-weight: 400;
            color: var(--text-primary);
            letter-spacing: -0.02em;
            line-height: 1.1;
        }}
        .stat-value.accent {{ color: var(--accent-warm); }}
        .stat-sub {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 0.35rem;
        }}

        /* --- SECTION HEADERS --- */
        .section-header {{
            margin-top: 3rem;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: baseline;
            gap: 1rem;
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: 0.75rem;
        }}
        .section-header h2 {{
            font-family: var(--serif);
            font-size: 1.4rem;
            font-weight: 400;
            letter-spacing: -0.01em;
        }}
        .section-header .section-tag {{
            font-family: var(--mono);
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
        }}

        /* --- CHARTS --- */
        .chart-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1px;
            background: var(--border-subtle);
            border: 1px solid var(--border-subtle);
        }}
        .chart-cell {{
            background: var(--bg-surface);
            padding: 1.75rem;
        }}
        .chart-cell-full {{
            grid-column: 1 / -1;
        }}
        .chart-title {{
            font-family: var(--mono);
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 1.25rem;
        }}
        .chart-container {{
            position: relative;
            height: 260px;
        }}

        /* --- TABLES --- */
        .data-table-wrapper {{
            border: 1px solid var(--border-subtle);
            overflow: hidden;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        thead th {{
            font-family: var(--mono);
            font-size: 10px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
            text-align: left;
            padding: 0.85rem 1.25rem;
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border-subtle);
            font-weight: 500;
        }}
        thead th:not(:first-child) {{ text-align: right; }}
        tbody td {{
            padding: 0.75rem 1.25rem;
            border-bottom: 1px solid var(--bg-elevated);
            color: var(--text-secondary);
            font-size: 13px;
        }}
        tbody td:not(:first-child) {{
            text-align: right;
            font-family: var(--mono);
            font-size: 12px;
        }}
        tbody tr:hover {{ background: var(--bg-surface); }}
        tbody td:first-child {{
            color: var(--text-primary);
            font-weight: 400;
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: var(--radius);
            font-family: var(--mono);
            font-size: 10px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .badge-warm {{ background: rgba(232, 195, 126, 0.15); color: var(--accent-warm); }}
        .badge-sage {{ background: rgba(126, 184, 154, 0.15); color: var(--accent-sage); }}
        .badge-rose {{ background: rgba(212, 117, 106, 0.15); color: var(--accent-rose); }}
        .badge-blue {{ background: rgba(106, 159, 212, 0.15); color: var(--accent-blue); }}
        .badge-lavender {{ background: rgba(164, 136, 199, 0.15); color: var(--accent-lavender); }}

        /* --- PARETO INSIGHT --- */
        .insight-bar {{
            margin-top: 2.5rem;
            border: 1px solid var(--accent-warm-dim);
            background: rgba(232, 195, 126, 0.04);
            padding: 1.5rem 1.75rem;
            display: flex;
            align-items: baseline;
            gap: 1rem;
        }}
        .insight-bar .insight-icon {{
            font-family: var(--serif);
            font-size: 1.6rem;
            color: var(--accent-warm);
            line-height: 1;
        }}
        .insight-bar .insight-text {{
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.6;
        }}
        .insight-bar .insight-text strong {{
            color: var(--accent-warm);
            font-weight: 500;
        }}

        /* --- ACCOUNT SECTIONS --- */
        .account-section {{ display: none; }}
        .account-section.active {{ display: block; }}

        /* --- EMPTY STATE --- */
        .empty-state {{
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
            font-family: var(--serif);
            font-size: 1.1rem;
            font-style: italic;
        }}

        /* --- RESPONSIVE --- */
        @media (max-width: 900px) {{
            .container {{ padding: 0 1.5rem 3rem; }}
            .masthead {{ padding: 1.5rem; }}
            .stat-row {{ grid-template-columns: repeat(2, 1fr); }}
            .chart-grid {{ grid-template-columns: 1fr; }}
        }}

        /* --- NOISE TEXTURE --- */
        body::before {{
            content: '';
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            pointer-events: none;
            z-index: 9999;
            opacity: 0.025;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        }}
    </style>
</head>
<body>

<header class="masthead">
    <div class="masthead-inner">
        <h1>Content <em>Analytics</em></h1>
        <div class="masthead-meta">{generated_date}</div>
    </div>
</header>

<div class="container">
    <nav class="tab-strip" id="tabs"></nav>
    <div id="content"></div>
</div>

<script>
const CHART_COLORS = ['#e8c37e', '#7eb89a', '#6a9fd4', '#d4756a', '#a488c7', '#c4a05a'];
const BADGE_CLASSES = ['badge-warm', 'badge-sage', 'badge-blue', 'badge-rose', 'badge-lavender'];
const data = {accounts_json};
const accounts = Object.keys(data);

Chart.defaults.color = '#5c5c62';
Chart.defaults.borderColor = '#2a2a30';
Chart.defaults.font.family = "'DM Sans', sans-serif";
Chart.defaults.font.size = 11;

// Build tabs
const tabBar = document.getElementById('tabs');
accounts.forEach((name, i) => {{
    const tab = document.createElement('div');
    tab.className = 'tab' + (i === 0 ? ' active' : '');
    tab.textContent = name.replace(/_/g, ' ');
    tab.dataset.account = name;
    tab.onclick = (e) => {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.account-section').forEach(s => s.classList.remove('active'));
        e.target.classList.add('active');
        document.getElementById('section-' + e.target.dataset.account).classList.add('active');
    }};
    tabBar.appendChild(tab);
}});

const content = document.getElementById('content');
const formatBadgeMap = {{}};

function fmt(n) {{ return n == null ? '—' : Number(n).toLocaleString(); }}
function pct(n) {{ return n == null ? '—' : (Number(n) * 100).toFixed(1) + '%'; }}
function getBadge(format) {{
    if (!formatBadgeMap[format]) {{
        const idx = Object.keys(formatBadgeMap).length % BADGE_CLASSES.length;
        formatBadgeMap[format] = BADGE_CLASSES[idx];
    }}
    return `<span class="badge ${{formatBadgeMap[format]}}">${{format || '?'}}</span>`;
}}

accounts.forEach((name, idx) => {{
    const report = data[name];
    const summary = report.summary || {{}};
    const formats = report.formats || {{}};
    const pillars = report.pillars || {{}};
    const topPosts = report.top_posts || [];
    const bottomPosts = report.bottom_posts || [];
    const pareto = report.pareto || {{}};
    const hookCorr = report.hook_correlation || [];
    const slideCounts = report.slide_count || [];

    const section = document.createElement('div');
    section.id = 'section-' + name;
    section.className = 'account-section' + (idx === 0 ? ' active' : '');

    const totalPosts = summary.total_posts || 0;
    const avgViews = summary.avg_views || 0;
    const totalViews = summary.total_views || 0;
    const avgEng = summary.avg_engagement_rate || 0;
    const bestViews = summary.best_views || 0;

    if (totalPosts === 0) {{
        section.innerHTML = '<div class="empty-state">No performance data yet. Run a scrape first.</div>';
        content.appendChild(section);
        return;
    }}

    // Pareto insight
    const topFormats = (pareto.top_formats || []);
    const topPillars = (pareto.top_pillars || []);
    let insightHTML = '';
    if (topFormats.length > 0) {{
        const best = topFormats[0];
        const worst = topFormats[topFormats.length - 1];
        if (topFormats.length > 1 && best.format !== worst.format) {{
            const ratio = (best.avg_views / (worst.avg_views || 1)).toFixed(1);
            insightHTML = `
                <div class="insight-bar">
                    <div class="insight-icon">&para;</div>
                    <div class="insight-text">
                        <strong>${{best.format}}</strong> outperforms <strong>${{worst.format}}</strong> by
                        <strong>${{ratio}}x</strong> on average views across ${{best.post_count + worst.post_count}} posts.
                        ${{topPillars.length > 0 ? 'Top pillar: <strong>' + topPillars[0].pillar + '</strong>.' : ''}}
                    </div>
                </div>`;
        }}
    }}

    section.innerHTML = `
        <!-- STATS -->
        <div class="stat-row">
            <div class="stat-card">
                <div class="stat-label">Total Posts</div>
                <div class="stat-value">${{totalPosts}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Views</div>
                <div class="stat-value accent">${{fmt(Math.round(avgViews))}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Views</div>
                <div class="stat-value">${{fmt(totalViews)}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Engagement</div>
                <div class="stat-value">${{pct(avgEng)}}</div>
                <div class="stat-sub">Best: ${{fmt(bestViews)}} views</div>
            </div>
        </div>

        ${{insightHTML}}

        <!-- CHARTS -->
        <div class="section-header">
            <h2>Performance</h2>
            <span class="section-tag">Charts</span>
        </div>
        <div class="chart-grid">
            <div class="chart-cell">
                <div class="chart-title">Views by Format</div>
                <div class="chart-container"><canvas id="chart-views-${{name}}"></canvas></div>
            </div>
            <div class="chart-cell">
                <div class="chart-title">Saves by Format</div>
                <div class="chart-container"><canvas id="chart-saves-${{name}}"></canvas></div>
            </div>
            <div class="chart-cell">
                <div class="chart-title">Engagement Rate by Format</div>
                <div class="chart-container"><canvas id="chart-eng-${{name}}"></canvas></div>
            </div>
            <div class="chart-cell">
                <div class="chart-title">${{Object.keys(pillars).length > 0 ? 'Pillar Performance' : 'Hook Score vs Views'}}</div>
                <div class="chart-container"><canvas id="chart-secondary-${{name}}"></canvas></div>
            </div>
        </div>

        <!-- FORMAT TABLE -->
        <div class="section-header">
            <h2>Formats</h2>
            <span class="section-tag">Breakdown</span>
        </div>
        <div class="data-table-wrapper">
            <table>
                <thead><tr><th>Format</th><th>Posts</th><th>Avg Views</th><th>Avg Saves</th><th>Engagement</th></tr></thead>
                <tbody id="format-table-${{name}}"></tbody>
            </table>
        </div>

        <!-- TOP POSTS -->
        <div class="section-header">
            <h2>Top Posts</h2>
            <span class="section-tag">Winners</span>
        </div>
        <div class="data-table-wrapper">
            <table>
                <thead><tr><th>Hook</th><th>Format</th><th>Views</th><th>Saves</th><th>Engagement</th></tr></thead>
                <tbody id="top-table-${{name}}"></tbody>
            </table>
        </div>

        <!-- BOTTOM POSTS -->
        <div class="section-header">
            <h2>Bottom Posts</h2>
            <span class="section-tag">Failure Analysis</span>
        </div>
        <div class="data-table-wrapper">
            <table>
                <thead><tr><th>Hook</th><th>Format</th><th>Views</th><th>Saves</th><th>Engagement</th></tr></thead>
                <tbody id="bottom-table-${{name}}"></tbody>
            </table>
        </div>
    `;
    content.appendChild(section);

    // --- CHARTS ---
    const fmtNames = Object.keys(formats);
    const chartOpts = (horizontal = false) => ({{
        responsive: true, maintainAspectRatio: false, indexAxis: horizontal ? 'y' : 'x',
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ grid: {{ color: '#1f1f24' }}, ticks: {{ font: {{ family: "'DM Sans'" }} }} }},
            y: {{ grid: {{ color: '#1f1f24' }}, ticks: {{ font: {{ family: "'DM Sans'" }} }} }}
        }}
    }});

    if (fmtNames.length > 0) {{
        // Views
        new Chart(document.getElementById('chart-views-' + name), {{
            type: 'bar', data: {{
                labels: fmtNames,
                datasets: [{{ data: fmtNames.map(f => Math.round(formats[f].avg_views || 0)),
                    backgroundColor: fmtNames.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
                    borderRadius: 1, barPercentage: 0.7 }}]
            }}, options: chartOpts()
        }});
        // Saves
        new Chart(document.getElementById('chart-saves-' + name), {{
            type: 'bar', data: {{
                labels: fmtNames,
                datasets: [{{ data: fmtNames.map(f => Math.round(formats[f].avg_saves || 0)),
                    backgroundColor: fmtNames.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
                    borderRadius: 1, barPercentage: 0.7 }}]
            }}, options: chartOpts()
        }});
        // Engagement
        new Chart(document.getElementById('chart-eng-' + name), {{
            type: 'bar', data: {{
                labels: fmtNames,
                datasets: [{{ data: fmtNames.map(f => ((formats[f].avg_engagement_rate || 0) * 100).toFixed(1)),
                    backgroundColor: fmtNames.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
                    borderRadius: 1, barPercentage: 0.7 }}]
            }}, options: {{ ...chartOpts(), scales: {{ ...chartOpts().scales,
                y: {{ ...chartOpts().scales.y, ticks: {{ callback: v => v + '%', font: {{ family: "'DM Sans'" }} }} }} }} }}
        }});
    }}

    // Secondary chart: pillars or hook correlation
    const pillarNames = Object.keys(pillars);
    if (pillarNames.length > 0) {{
        new Chart(document.getElementById('chart-secondary-' + name), {{
            type: 'bar', data: {{
                labels: pillarNames.map(p => p.replace(/_/g, ' ')),
                datasets: [{{ data: pillarNames.map(p => Math.round(pillars[p].avg_views || 0)),
                    backgroundColor: pillarNames.map((_, i) => CHART_COLORS[i % CHART_COLORS.length]),
                    borderRadius: 1, barPercentage: 0.7 }}]
            }}, options: chartOpts()
        }});
    }} else if (hookCorr.length > 0) {{
        new Chart(document.getElementById('chart-secondary-' + name), {{
            type: 'scatter', data: {{
                datasets: [{{ data: hookCorr.map(h => ({{ x: h.hook_score, y: h.avg_views }})),
                    backgroundColor: '#e8c37e', pointRadius: 6, pointHoverRadius: 8 }}]
            }}, options: {{ responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ title: {{ display: true, text: 'Hook Score', color: '#5c5c62' }}, grid: {{ color: '#1f1f24' }} }},
                    y: {{ title: {{ display: true, text: 'Avg Views', color: '#5c5c62' }}, grid: {{ color: '#1f1f24' }} }}
                }}
            }}
        }});
    }}

    // --- TABLES ---
    const fmtBody = document.getElementById('format-table-' + name);
    const sorted = [...fmtNames].sort((a, b) => (formats[b].avg_views || 0) - (formats[a].avg_views || 0));
    sorted.forEach(f => {{
        const d = formats[f];
        fmtBody.innerHTML += `<tr>
            <td>${{getBadge(f)}}</td>
            <td>${{d.post_count}}</td>
            <td>${{fmt(Math.round(d.avg_views))}}</td>
            <td>${{fmt(Math.round(d.avg_saves))}}</td>
            <td>${{pct(d.avg_engagement_rate)}}</td>
        </tr>`;
    }});

    const topBody = document.getElementById('top-table-' + name);
    topPosts.slice(0, 8).forEach(p => {{
        topBody.innerHTML += `<tr>
            <td>${{(p.hook_text || '').slice(0, 70)}}</td>
            <td>${{getBadge(p.format)}}</td>
            <td>${{fmt(p.views)}}</td>
            <td>${{fmt(p.saves)}}</td>
            <td>${{pct(p.engagement_rate)}}</td>
        </tr>`;
    }});

    const bottomBody = document.getElementById('bottom-table-' + name);
    bottomPosts.slice(0, 8).forEach(p => {{
        bottomBody.innerHTML += `<tr>
            <td>${{(p.hook_text || '').slice(0, 70)}}</td>
            <td>${{getBadge(p.format)}}</td>
            <td>${{fmt(p.views)}}</td>
            <td>${{fmt(p.saves)}}</td>
            <td>${{pct(p.engagement_rate)}}</td>
        </tr>`;
    }});
}});
</script>
</body>
</html>"""

    output_path.write_text(html)
    return output_path
