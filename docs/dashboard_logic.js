/**
 * Clan Dashboard Logic
 * Handles data loading, chart rendering, and interactions.
 */

// Global State
let dashboardData = null;
let charts = {};
let currentPeriod = '7d'; // Default timeframe

// Global Error Handler
window.onerror = function (msg, url, lineNo, columnNo, error) {
    console.error("Global Error: " + msg, error);
    const el = document.getElementById('updated-time');
    if (el) el.innerHTML = `<span style="color:red">Error: ${msg}</span>`;
    return false;
};

// Global Timeframe Switcher
window.switchTimeframe = function (period) {
    if (period === currentPeriod) return;
    currentPeriod = period;
    console.log("Switched timeframe to:", currentPeriod);

    // Update Buttons
    document.querySelectorAll('.time-toggle').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`btn-${period}`);
    if (activeBtn) activeBtn.classList.add('active');

    // Update Label
    const lbl = document.getElementById('lbl-xp-period');
    if (lbl) lbl.innerText = `(${period})`;

    // Re-render Affected Sections
    if (dashboardData) {
        safelyRun(() => renderGeneralStats(dashboardData), "renderGeneralStats");
        // Re-render charts that depend on this (like Top XP)
        safelyRun(() => renderTopXPChart(), "renderTopXPChart");
    }
};

// Global Tab Switcher (Exposed for HTML onclick)
window.switchSection = function (sectionId) {
    console.log("Switching to section:", sectionId);

    // 1. Hide all sections
    document.querySelectorAll('.section').forEach(el => {
        el.classList.remove('active');
        el.style.display = 'none'; // Ensure hidden
    });

    // 2. Show target section
    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.add('active');
        target.style.display = 'block';
    } else {
        console.warn("Target section not found:", sectionId);
    }

    // 3. Update Sidebar Active State
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.remove('active');
        // Check matching onclick or data attribute
        const clickAttr = el.getAttribute('onclick');
        if (clickAttr && clickAttr.includes(`'${sectionId}'`)) {
            el.classList.add('active');
        }
    });

    // 4. Trigger Resize for Charts (Fixes rendering if hidden)
    if (typeof Chart !== 'undefined') {
        Object.values(Chart.instances).forEach(chart => chart.resize());
    }
};

// Wait for DOM
document.addEventListener('DOMContentLoaded', async () => {
    console.log("Dashboard initializing...");

    try {
        // 1. Load Data
        if (window.dashboardData) {
            dashboardData = window.dashboardData;
            console.log("Loaded data from window.dashboardData");
        } else {
            try {
                const resp = await fetch('clan_data.json');
                if (!resp.ok) throw new Error("Failed to fetch clan_data.json");
                dashboardData = await resp.json();
                console.log("Loaded data from clan_data.json");
            } catch (e) {
                console.warn("Could not load data:", e);
                if (window.dashboardData) {
                    dashboardData = window.dashboardData;
                } else {
                    throw new Error("Data load failed. " + e.message);
                }
            }
        }

        if (!dashboardData) throw new Error("Dashboard Data is null");

        // Fallback for topXPGainers if missing
        if (!dashboardData.topXPGainers && dashboardData.allMembers) {
            console.warn("Generating topXPGainers from allMembers");
            dashboardData.topXPGainers = [...dashboardData.allMembers]
                .sort((a, b) => b.xp_7d - a.xp_7d);
        }

        // Indicate Data Loaded
        const updateEl = document.getElementById('updated-time');
        if (updateEl) updateEl.innerText = "Data Loaded. Rendering...";

        // 2. Initial Render
        safelyRun(() => renderLastUpdated(dashboardData.generated_at), "renderLastUpdated");
        safelyRun(() => renderGeneralStats(dashboardData), "renderGeneralStats");
        safelyRun(() => renderAlertCards(dashboardData.allMembers), "renderAlertCards");
        // safelyRun(() => renderBingoGrid(), "renderBingoGrid"); // REMOVED
        safelyRun(() => renderRecentActivity(dashboardData.allMembers), "renderRecentActivity");
        safelyRun(() => renderRecentActivity(dashboardData.allMembers), "renderRecentActivity");
        safelyRun(() => renderInactiveWatchlist(dashboardData.allMembers), "renderInactiveWatchlist");

        // New Render Functions
        safelyRun(() => renderFullRoster(dashboardData.allMembers), "renderFullRoster");
        safelyRun(() => renderMessagesSection(dashboardData.allMembers), "renderMessagesSection");
        safelyRun(() => renderXpSection(dashboardData.allMembers), "renderXpSection");
        safelyRun(() => renderBossesSection(dashboardData.allMembers), "renderBossesSection");
        safelyRun(() => renderOutliersSection(dashboardData.allMembers), "renderOutliersSection");

        // 3. Render Charts
        safelyRun(() => renderAllCharts(), "renderAllCharts");

        // 4. Setup Search (Header search boxes)
        safelyRun(() => renderNewsTicker(dashboardData.allMembers), "renderNewsTicker");
        safelyRun(() => setupSearch(), "setupSearch");

    } catch (criticalError) {
        console.error("CRITICAL INIT ERROR:", criticalError);
        const headerInfo = document.querySelector('.header-info');
        // Ensure headerInfo exists, if not try updated-time id
        const el = headerInfo || document.getElementById('updated-time');
        if (el) el.innerHTML = `<span style="color:red; font-size: 0.8em;">INIT ERROR: ${criticalError.message}</span>`;
    }
});

// Table Sorting Logic
window.sortTable = function (n) {
    const table = document.getElementById("roster-table");
    if (!table) return;

    // Toggle Sort Direction
    if (!table.dataset.sortDir) table.dataset.sortDir = "asc";
    let dir = table.dataset.sortDir === "asc" ? "desc" : "asc";
    table.dataset.sortDir = dir;

    let switching = true;
    let shouldSwitch;
    let i;

    while (switching) {
        switching = false;
        const rows = table.rows;

        // Loop through all table rows (except the first, which contains table headers)
        for (i = 1; i < (rows.length - 1); i++) {
            shouldSwitch = false;

            const x = rows[i].getElementsByTagName("TD")[n];
            const y = rows[i + 1].getElementsByTagName("TD")[n];

            let xVal = x.textContent || x.innerText;
            let yVal = y.textContent || y.innerText;

            // Clean numbers (remove k, M, commas)
            // If column is Ratio (idx 7) or Days (idx 8), treat as number
            // XP (1,2), Boss (3,4), Msgs (5,6) are also numbers
            // Name (0) is string

            const isNumeric = n !== 0;

            let xNum = parseFloat(xVal.replace(/[+,kM\s]/g, ''));
            let yNum = parseFloat(yVal.replace(/[+,kM\s]/g, ''));

            // Handle multipliers if needed (k=1000, M=1000000) - simplified here as formatNumber puts them back
            // Actually, sorting pre-formatted numbers (1.2k vs 900) requires parsing suffixes
            if (xVal.includes('M')) xNum = parseFloat(xVal) * 1000000;
            else if (xVal.includes('k')) xNum = parseFloat(xVal) * 1000;

            if (yVal.includes('M')) yNum = parseFloat(yVal) * 1000000;
            else if (yVal.includes('k')) yNum = parseFloat(yVal) * 1000;

            if (dir == "asc") {
                if (isNumeric) {
                    if (xNum > yNum) shouldSwitch = true;
                } else {
                    if (xVal.toLowerCase() > yVal.toLowerCase()) shouldSwitch = true;
                }
            } else {
                if (isNumeric) {
                    if (xNum < yNum) shouldSwitch = true;
                } else {
                    if (xVal.toLowerCase() < yVal.toLowerCase()) shouldSwitch = true;
                }
            }

            if (shouldSwitch) {
                rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                switching = true;
                break;
            }
        }
    }

    // Update Icons
    document.querySelectorAll("th i").forEach(i => i.className = "fas fa-sort");
    const header = table.getElementsByTagName("TH")[n];
    const icon = header.querySelector("i");
    if (icon) icon.className = dir === "asc" ? "fas fa-sort-up" : "fas fa-sort-down";
};

function safelyRun(fn, name) {
    try {
        fn();
    } catch (e) {
        console.error(`Error in ${name}:`, e);
    }
}

function renderLastUpdated(isoDate) {
    const el = document.getElementById('updated-time');
    if (el && isoDate) {
        const d = new Date(isoDate);
        el.innerText = d.toLocaleString('en-GB').replace(/\//g, '-');
    }
}

function renderGeneralStats(data) {
    // Helper to generic card specific HTML
    const setHtml = (id, html) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    };

    // Determine Property Keys based on Current Period
    const xpKey = currentPeriod === '30d' ? 'xp_30d' : 'xp_7d';
    const msgKey = currentPeriod === '30d' ? 'msgs_30d' : 'msgs_7d';
    // Boss data might not be distinctly split in basic summary object, but let's see if we can derive top killer dynamically if needed.
    // For now, "Top Boss Killer" in root JSON is likely 7d default. If we want dynamic, we need to sort allMembers.

    // 1. Dynamic Sorting for Top Stats
    const members = data.allMembers;

    // Top XP
    const topXpMember = [...members].sort((a, b) => b[xpKey] - a[xpKey])[0];
    if (topXpMember) {
        setHtml('stat-top-xp', `
             <div style="display:flex;align-items:center;justify-content:center;gap:10px;">
                <img src="assets/${topXpMember.rank_img || 'rank_minion.png'}" style="width:30px;height:auto;object-fit:contain;">
                <span>${topXpMember.username} <span style="color:var(--neon-gold);font-size:0.9em">(${formatNumber(topXpMember[xpKey])})</span></span>
            </div>
        `);
    }

    // Top Messenger
    const topMsgMember = [...members].sort((a, b) => b[msgKey] - a[msgKey])[0];
    if (topMsgMember) {
        setHtml('stat-top-msg', `
            <div style="display:flex;align-items:center;justify-content:center;gap:10px;">
                <img src="assets/${topMsgMember.rank_img || 'rank_minion.png'}" style="width:30px;height:auto;object-fit:contain;">
                <span>${topMsgMember.username} <span style="color:var(--neon-green);font-size:0.9em">(${formatNumber(topMsgMember[msgKey])})</span></span>
            </div>
        `);
    }

    // Rising Star (Always based on a ratio or specific metric, let's keep it static or use 7d msg as proxy for now)
    if (data.risingStar) {
        const m = data.risingStar;
        setHtml('stat-rising-star', `
             <div style="display:flex;align-items:center;justify-content:center;gap:10px;">
                <img src="assets/${m.rank_img || 'rank_minion.png'}" style="width:30px;height:auto;object-fit:contain;">
                <span>${m.name} <span style="color:var(--neon-blue);font-size:0.9em">(${formatNumber(m.msgs)})</span></span>
            </div>
        `);
    }

    // Top Boss (Default to static if no dynamic boss data available for 30d, or sort by boss_score if available)
    if (data.topBossKiller) {
        const m = data.topBossKiller;
        // Try to find full member data
        const fullMember = members.find(p => p.username === m.name);
        const bossImg = fullMember && fullMember.favorite_boss_img ? fullMember.favorite_boss_img : (m.rank_img || 'rank_minion.png');

        setHtml('stat-top-boss', `
             <div style="display:flex;align-items:center;justify-content:center;gap:10px;">
                <img src="assets/${bossImg}" style="width:30px;height:auto;object-fit:contain;" onerror="this.src='assets/rank_minion.png';this.onerror=null;">
                <span>${m.name} <span style="color:var(--neon-red);font-size:0.9em">(${formatNumber(m.kills)})</span></span>
            </div>
        `);
    }
}

function renderNewsTicker(members) {
    const tickerContainer = document.getElementById('news-ticker');
    if (!tickerContainer) return;

    // Generate News Items
    const news = [];

    // 1. Big XP Gains
    const topXp = [...members].sort((a, b) => b.xp_7d - a.xp_7d).slice(0, 3);
    topXp.forEach(m => {
        if (m.xp_7d > 1000000) news.push(`🏆 <b>${m.username}</b> gained ${formatNumber(m.xp_7d)} XP this week!`);
    });

    // 2. Boss Killers
    const topBoss = [...members].sort((a, b) => b.boss_7d - a.boss_7d).slice(0, 3);
    topBoss.forEach(m => {
        if (m.boss_7d > 50) news.push(`⚔️ <b>${m.username}</b> slew ${m.boss_7d} bosses recently.`);
    });

    // 3. Chatters
    const topMsg = [...members].sort((a, b) => b.msgs_7d - a.msgs_7d)[0];
    if (topMsg && topMsg.msgs_7d > 100) news.push(`💬 <b>${topMsg.username}</b> is the chatterbox of the week with ${topMsg.msgs_7d} messages.`);

    // 4. Random Flavour
    const totalXp = members.reduce((sum, m) => sum + (m.xp_7d || 0), 0);
    news.push(`📈 Clan Total XP Gained: ${formatNumber(totalXp)}`);

    // Duplicate string to ensure smooth infinite loop if short
    let finalHtml = news.join(' &nbsp;&bull;&nbsp; ');
    if (news.length < 5) finalHtml += ' &nbsp;&bull;&nbsp; ' + finalHtml;

    tickerContainer.innerHTML = finalHtml;
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function formatNumber(num) {
    if (num === undefined || num === null) return "0";
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function renderAlertCards(members) {
    const alertsContainer = document.getElementById('alert-cards-container');
    if (!alertsContainer) return;

    alertsContainer.innerHTML = '';

    // Logic: Inactive but high rank? Or 0 activity?
    // Let's pick 3 "At Risk" members (low XP, not new)
    const atRisk = members
        .filter(m => m.xp_7d === 0 && m.boss_7d === 0 && m.msgs_7d === 0)
        .slice(0, 4);

    if (atRisk.length === 0) {
        alertsContainer.innerHTML = '<div class="glass-card" style="padding:20px;grid-column:1/-1;text-align:center;color:#4fec4f">No immediate risks detected.</div>';
        return;
    }

    atRisk.forEach(m => {
        const card = document.createElement('div');
        card.className = 'alert-card';
        card.innerHTML = `
            <div class="alert-header" style="display:flex;align-items:center;gap:10px;margin-bottom:10px;color:var(--neon-red)">
                <i class="fas fa-exclamation-triangle"></i>
                <span style="font-family:'Cinzel'">Inactivity Risk</span>
            </div>
            <div class="player-info" style="display:flex;align-items:center;gap:15px">
                <img src="assets/${m.rank_img || 'rank_minion.png'}" style="width:40px;height:auto;" onerror="this.src='assets/rank_minion.png'">
                <div class="player-details">
                    <div class="player-name" style="color:#fff;font-weight:bold">${m.username}</div>
                    <div class="player-role" style="color:#888;font-size:0.8em">${m.role}</div>
                </div>
            </div>
            <div class="alert-metric" style="margin-top:15px;display:flex;justify-content:space-between;border-top:1px solid rgba(255,255,255,0.1);padding-top:10px">
                <span style="color:#888">7d Activity</span>
                <span style="color:var(--neon-red)">0 XP</span>
            </div>
        `;
        alertsContainer.appendChild(card);
    });
}

function renderRecentActivity(members) {
    // Populate "Recent Activity" Table (Top 5 by XP or Msgs)
    const tbody = document.querySelector('#recent-activity-table tbody');
    if (!tbody) return;

    // Sort by recent Messages (High to Low)
    const recent = [...members].sort((a, b) => b.msgs_7d - a.msgs_7d).slice(0, 10);

    let html = '';
    recent.forEach((m, i) => {
        html += `
            <tr>
                <td style="color:${i < 3 ? 'var(--neon-gold)' : '#fff'}">#${i + 1}</td>
                <td style="display:flex;align-items:center;gap:10px">
                     <img src="assets/${m.rank_img}" width="20" onerror="this.style.display='none'">
                     ${m.username}
                </td>
                <td>${m.msgs_7d}</td>
                <td style="color:var(--neon-green)">+${formatNumber(m.xp_7d)}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function renderInactiveWatchlist(members) {
    const container = document.getElementById('inactive-watchlist');
    if (!container) return;

    // Filter: 0 msgs in last 30d (and joined > 30d ago? optional)
    const inactive = members.filter(m => m.msgs_30d === 0 && m.days_in_clan > 30).slice(0, 20);

    if (inactive.length === 0) {
        container.innerHTML = '<span style="color:#888">All systems active.</span>';
        return;
    }

    let html = '';
    inactive.forEach(m => {
        html += `<span class="inactive-tag">${m.username}</span>`;
    });
    container.innerHTML = html;
}


// ---------------------------------------------------------
// NEW VISUALIZATION FUNCTIONS (Replaces Bingo)
// ---------------------------------------------------------

function renderScatterInteraction() {
    const ctx = document.getElementById('chart-scatter-interaction');
    if (!ctx) return;
    if (charts.scatterInt) charts.scatterInt.destroy();

    const members = dashboardData.allMembers;

    // x: Messages (30d), y: XP (30d)
    const dataPoints = members
        .filter(m => m.msgs_30d > 0 || m.xp_30d > 0)
        .map(m => ({
            x: m.msgs_30d,
            y: m.xp_30d,
            r: 5,
            player: m.username,
            role: m.role
        }));

    // Split into Quadrants logic could be visual annotations
    // Color coding by Role maybe?

    charts.scatterInt = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Members',
                data: dataPoints,
                borderColor: '#ffffff',
                borderWidth: 1,
                pointHoverRadius: 8,
                backgroundColor: function (context) {
                    const val = context.raw;
                    if (!val) return 'rgba(136, 136, 136, 0.5)';
                    const avgMsg = 50;
                    const avgXP = 500000;

                    if (val.x > avgMsg && val.y > avgXP) return 'rgba(51, 255, 51, 0.7)'; // Green
                    if (val.x > avgMsg) return 'rgba(0, 212, 255, 0.7)'; // Blue
                    if (val.y > avgXP) return 'rgba(255, 215, 0, 0.7)'; // Gold
                    return 'rgba(136, 136, 136, 0.5)'; // Grey
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    title: { display: true, text: 'Messages (30d)', color: '#888' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    title: { display: true, text: 'XP Gained (30d)', color: '#888' },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { callback: function (val) { return formatNumber(val); } }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const p = context.raw;
                            return `${p.player}: ${p.x} msgs, ${formatNumber(p.y)} XP`;
                        }
                    }
                },
                legend: { display: false },
                annotation: {
                    annotations: {
                        label1: {
                            type: 'label',
                            xValue: 'max',
                            yValue: 'max',
                            content: ['MVP Zone'],
                            font: { size: 12 },
                            color: 'rgba(255,255,255,0.3)'
                        }
                    }
                }
            }
        }
    });
}

function renderBossDiversity() {
    const ctx = document.getElementById('chart-boss-diversity');
    if (!ctx) return;
    const data = dashboardData.chart_boss_diversity;
    if (!data) return;

    if (charts.bossDiv) charts.bossDiv.destroy();

    charts.bossDiv = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.datasets[0].data,
                backgroundColor: [
                    '#FFD700', '#00d4ff', '#33FF33', '#FF3333',
                    '#FF00FF', '#FFA500', '#008080', '#555555'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#ccc', boxWidth: 10 } }
            }
        }
    });
}

function renderRaidsPerformance() {
    const ctx = document.getElementById('chart-raids-performance');
    if (!ctx) return;
    const data = dashboardData.chart_raids;
    if (!data) return;

    if (charts.raids) charts.raids.destroy();

    charts.raids = new Chart(ctx, {
        type: 'bar', // Stacked bar usually requires multiple datasets, but here comparing Total Kills across raids is fine as regular bar
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Total Kills',
                data: data.datasets[0].data,
                backgroundColor: [
                    '#55FF55', '#228822', // CoX
                    '#FF5555', '#882222', // ToB
                    '#FFFF55', '#888822'  // ToA
                ],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function renderSkillMastery() {
    const ctx = document.getElementById('chart-skill-mastery');
    if (!ctx) return;
    const data = dashboardData.chart_skills;
    if (!data) return;

    if (charts.skills) charts.skills.destroy();

    // Top 10 skills
    const labels = data.labels.slice(0, 10);
    const values = data.datasets[0].data.slice(0, 10);

    charts.skills = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Level 99s',
                data: values,
                backgroundColor: '#FFA500',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // Horizontal Bar
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function renderBossTrend() {
    const ctx = document.getElementById('chart-boss-trend');
    if (!ctx) return;
    const data = dashboardData.chart_boss_trend;
    if (!data) return;

    // Update Name
    const nameEl = document.getElementById('trending-boss-name');
    if (nameEl) nameEl.innerText = `${data.boss_name} (+${formatNumber(data.total_gain)})`;

    if (charts.bossTrend) charts.bossTrend.destroy();

    charts.bossTrend = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.chart_data.labels,
            datasets: [{
                label: `Daily ${data.boss_name} Kills`,
                data: data.chart_data.datasets[0].data,
                borderColor: '#FFD700',
                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { display: false } // Hide dates to keep it clean, hover for info
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}


/**
 * Chart.js Rendering
 */
function renderAllCharts() {
    if (typeof Chart === 'undefined') {
        console.error("Chart.js not loaded");
        return;
    }

    Chart.defaults.color = '#888';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
    Chart.defaults.font.family = "'Outfit', sans-serif";

    renderActivityHealthChart();
    renderTopXPChart();
    renderTrendChart();

    // NEW CHARTS
    renderScatterInteraction();
    renderBossDiversity();
    renderRaidsPerformance();
    renderSkillMastery();
    renderBossTrend();

    // MISSING CHARTS ADDED
    renderPlayerRadar();
    renderLeaderboardChart();
    initComparator();
}

function renderActivityHealthChart() {
    const ctx = document.getElementById('activity-health-chart');
    if (!ctx) return;

    if (charts.health) charts.health.destroy();

    const members = dashboardData.allMembers;
    const high = members.filter(m => m.xp_7d > 1000000).length;
    const med = members.filter(m => m.xp_7d > 100000 && m.xp_7d <= 1000000).length;
    const low = members.filter(m => m.xp_7d > 0 && m.xp_7d <= 100000).length;
    const inactive = members.filter(m => m.xp_7d === 0).length;

    charts.health = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Activity', 'Moderate', 'Low', 'Inactive'],
            datasets: [{
                data: [high, med, low, inactive],
                backgroundColor: ['#33FF33', '#00d4ff', '#FFD700', '#FF3333'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#ccc' } }
            }
        }
    });
}

function renderTopXPChart() {
    const ctx = document.getElementById('top-xp-contributors-chart');
    if (!ctx) return;
    if (charts.topXP) charts.topXP.destroy();

    const xpKey = currentPeriod === '30d' ? 'xp_30d' : 'xp_7d';
    const top5 = [...dashboardData.allMembers].sort((a, b) => b[xpKey] - a[xpKey]).slice(0, 5); // Recalculate based on period

    charts.topXP = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top5.map(m => m.username),
            datasets: [{
                label: `XP Gained (${currentPeriod})`,
                data: top5.map(m => m[xpKey]),
                backgroundColor: '#00d4ff',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function renderTrendChart() {
    const ctx = document.getElementById('activity-trend-chart');
    if (!ctx) return;
    if (charts.trend) charts.trend.destroy();

    // Use Real Data if available, fallback to dummy only if absolutely necessary
    const history = dashboardData.history || [];

    let labels, xpData, msgData;

    if (history.length > 0) {
        // Sort by date just in case
        history.sort((a, b) => new Date(a.date) - new Date(b.date));
        labels = history.map(d => {
            const date = new Date(d.date);
            return `${date.getDate()}/${date.getMonth() + 1}`;
        });
        xpData = history.map(d => d.xp);
        msgData = history.map(d => d.msgs);
    } else {
        // Fallback (should rarely happen if DB is populated)
        labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        xpData = [0, 0, 0, 0, 0, 0, 0];
        msgData = [0, 0, 0, 0, 0, 0, 0];
    }

    charts.trend = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total XP Gained',
                    data: xpData,
                    borderColor: '#FFD700',
                    backgroundColor: 'rgba(255, 215, 0, 0.1)',
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Total Messages',
                    data: msgData,
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { callback: function (value) { return formatNumber(value); } }
                },
                y1: {
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false }, // only want the grid lines for one axis to show up
                },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: { display: true, labels: { color: '#ccc' } },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatNumber(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}


function setupSearch() {
    // General Search
    setupSectionSearch('search-general', '#recent-activity-table tbody tr');
    setupSectionSearch('search-roster', '#roster-table tbody tr');
    setupSectionSearch('search-messages', '#messages-table tbody tr');
    setupSectionSearch('search-xp', '#xp-table tbody tr');
    setupSectionSearch('search-bosses', '#bosses-table tbody tr');
    setupSectionSearch('search-outliers', '#outliers-table tbody tr');
}

function setupSectionSearch(inputId, rowSelector) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        const rows = document.querySelectorAll(rowSelector);
        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(val) ? '' : 'none';
        });
    });
}

// ---------------------------------------------------------
// NEW RENDER FUNCTIONS
// ---------------------------------------------------------

function renderFullRoster(members) {
    const tbody = document.getElementById('roster-body');
    if (!tbody) return;

    let html = '';
    members.forEach(m => {
        const ratio = m.msgs_total > 0 ? (m.total_xp / m.msgs_total).toFixed(0) : 0;
        html += `
            <tr>
                <td style="display:flex;align-items:center;gap:10px">
                     <img src="assets/${m.rank_img || 'rank_minion.png'}" width="24">
                     <span class="player-link" onclick="openPlayerProfile('${m.username}')">${m.username}</span>
                </td>
                <td>${formatNumber(m.xp_7d)}</td>
                <td>${formatNumber(m.total_xp)}</td>
                <td>${formatNumber(m.boss_7d)}</td>
                <td>${formatNumber(m.total_boss)}</td>
                <td>${formatNumber(m.msgs_7d)}</td>
                <td>${formatNumber(m.msgs_total)}</td>
                <td>${formatNumber(ratio)}</td>
                <td>${m.days_in_clan || 0}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function renderMessagesSection(members) {
    // 1. Update Time
    renderTime('updated-time-msg', dashboardData.generated_at);

    // 2. Table
    const tbody = document.querySelector('#messages-table tbody');
    if (tbody) {
        const sorted = [...members].sort((a, b) => b.msgs_7d - a.msgs_7d).slice(0, 50);
        tbody.innerHTML = sorted.map(m => `
            <tr>
                <td>${m.username}</td>
                <td>${m.role}</td>
                <td>${formatNumber(m.msgs_total)}</td>
                <td style="color:var(--neon-green)">${m.msgs_7d}</td>
                <td>--</td> 
            </tr>
        `).join('');
    }

    // 3. Activity Heatmap (Hourly 24h)
    const heatmap = document.getElementById('activity-heatmap');
    if (heatmap && dashboardData.activity_heatmap) {
        heatmap.innerHTML = '';
        heatmap.style.display = 'grid';
        heatmap.style.gridTemplateColumns = 'repeat(24, 1fr)';
        heatmap.style.gap = '2px';
        heatmap.style.height = '60px';
        heatmap.style.alignItems = 'end'; // bars from bottom

        const maxVal = Math.max(...dashboardData.activity_heatmap);

        dashboardData.activity_heatmap.forEach((val, hour) => {
            const bar = document.createElement('div');
            // Height proportional to max
            const hPct = maxVal > 0 ? (val / maxVal) * 100 : 0;
            bar.style.height = Math.max(hPct, 15) + '%';
            // Increased opacity base to 0.4
            bar.style.backgroundColor = `rgba(0, 212, 255, ${Math.max(0.4, hPct / 100)})`;
            bar.style.borderRadius = '2px';
            bar.title = `${hour}:00 - ${val} msgs`;
            heatmap.appendChild(bar);
        });
    } else if (heatmap) {
        heatmap.innerHTML = '<div style="text-align:center;padding:50px;color:#666">Activity Heatmap Data Unavailable</div>';
    }

    // 4. Charts - Message Volume
    const ctxVol = document.getElementById('message-volume-chart');
    if (ctxVol) {
        if (charts.msgVol) charts.msgVol.destroy();
        const topMsg = [...members].sort((a, b) => b.msgs_7d - a.msgs_7d).slice(0, 5);
        charts.msgVol = new Chart(ctxVol, {
            type: 'bar',
            data: {
                labels: topMsg.map(m => m.username),
                datasets: [{
                    label: 'Messages (7d)',
                    data: topMsg.map(m => m.msgs_7d),
                    backgroundColor: '#00d4ff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: 'rgba(255,255,255,0.05)' } } }
            }
        });
    }

    // 5. Role Distribution
    const ctxRole = document.getElementById('role-distribution-chart');
    if (ctxRole) {
        if (charts.roleDist) charts.roleDist.destroy();
        // Aggregate roles
        const roles = {};
        members.forEach(m => {
            const r = m.role || 'Unknown';
            roles[r] = (roles[r] || 0) + 1;
        });
        charts.roleDist = new Chart(ctxRole, {
            type: 'doughnut',
            data: {
                labels: Object.keys(roles),
                datasets: [{
                    data: Object.values(roles),
                    backgroundColor: ['#FFD700', '#FF3333', '#33FF33', '#00d4ff', '#FF00FF', '#FFA500'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: { color: '#ccc', boxWidth: 10 } } }
            }
        });
    }
}

function renderXpSection(members) {
    renderTime('updated-time-xp', dashboardData.generated_at);

    // Table
    const tbody = document.querySelector('#xp-table tbody');
    if (tbody) {
        const sorted = [...members].sort((a, b) => b.xp_7d - a.xp_7d).slice(0, 50);
        tbody.innerHTML = sorted.map(m => `
            <tr>
                <td style="display:flex;align-items:center;gap:10px">
                    <img src="assets/${m.rank_img || 'rank_minion.png'}" width="20">
                    ${m.username}
                </td>
                <td>${m.role}</td>
                <td>${formatNumber(m.total_xp)}</td>
                <td style="color:var(--neon-green)">+${formatNumber(m.xp_7d)}</td>
                <td style="color:rgba(255,255,255,0.7)">+${formatNumber(m.xp_30d || 0)}</td>
            </tr>
        `).join('');
    }

    // XP Chart (7d vs Total) - effectively same as Top XP but maybe top 10?
    const ctxXP = document.getElementById('xp-7d-chart');
    if (ctxXP) {
        if (charts.xp7d) charts.xp7d.destroy();
        const top10 = [...members].sort((a, b) => b.xp_7d - a.xp_7d).slice(0, 10);
        charts.xp7d = new Chart(ctxXP, {
            type: 'bar',
            data: {
                labels: top10.map(m => m.username),
                datasets: [{
                    label: 'XP Gained (7d)',
                    data: top10.map(m => m.xp_7d),
                    backgroundColor: '#33FF33'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } } }
            }
        });
    }

    // Scatter: XP vs Messages
    const ctxScat = document.getElementById('xp-messages-scatter');
    if (ctxScat) {
        if (charts.scat) charts.scat.destroy();
        // Filter outliers for better chart view
        const dataPoints = members
            .filter(m => m.xp_7d > 0 && m.msgs_7d > 0 && m.xp_7d < 50000000)
            .map(m => ({ x: m.msgs_7d, y: m.xp_7d, r: 5, player: m.username }));

        charts.scat = new Chart(ctxScat, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'XP vs Msgs',
                    data: dataPoints,
                    backgroundColor: 'rgba(255, 215, 0, 0.5)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { title: { display: true, text: 'Messages (7d)' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { title: { display: true, text: 'XP (7d)' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const p = context.raw;
                                return `${p.player}: ${p.x} msgs, ${formatNumber(p.y)} XP`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderXPvsBossChart(members);
}

function renderBossesSection(members) {
    renderTime('updated-time-boss', dashboardData.generated_at);

    // Top Boss Cards
    const cards = document.getElementById('boss-cards');
    if (cards) {
        cards.innerHTML = '';
        const topKillers = [...members].sort((a, b) => b.boss_7d - a.boss_7d).slice(0, 4);
        topKillers.forEach(m => {
            cards.innerHTML += `
                <div class="stat-card">
                    <div class="stat-label">${m.username}</div>
                    <div class="stat-value" style="color:var(--neon-red)">${formatNumber(m.boss_7d)} Kills</div>
                    <div style="font-size:0.8em;color:#888;margin-top:5px;display:flex;align-items:center;justify-content:center;gap:5px">
                        <img src="assets/${m.favorite_boss_img || 'boss_pet_rock.png'}" style="height:30px;width:auto;object-fit:contain;">
                        <span>${m.favorite_boss || 'None'}</span>
                    </div>
                </div>
             `;
        });
    }

    // Table
    const tbody = document.querySelector('#bosses-table tbody');
    if (tbody) {
        const sorted = [...members].sort((a, b) => b.total_boss - a.total_boss).slice(0, 50);
        tbody.innerHTML = sorted.map((m, i) => `
            <tr>
                <td>#${i + 1}</td>
                <td>${m.username}</td>
                <td>${m.role}</td>
                <td style="color:var(--neon-gold);font-weight:bold">${formatNumber(m.total_boss)}</td>
                <td style="color:var(--neon-red)">+${formatNumber(m.boss_7d)}</td>
                <td style="color:rgba(255,255,255,0.7)">+${formatNumber(m.boss_30d || 0)}</td>
            </tr>
        `).join('');
    }
}

function renderOutliersSection(members) {
    renderTime('updated-time-out', dashboardData.generated_at);

    const tbody = document.querySelector('#outliers-table tbody');
    if (tbody) {
        // Enriched Purging Logic
        const purgingCandidates = [];

        members.forEach(m => {
            let status = null;
            let type = "";

            // Criteria for Purging
            if (m.days_in_clan > 60 && m.xp_30d < 50000 && m.boss_30d < 5 && m.msgs_30d === 0) {
                status = "Terminally Inactive";
                type = "Purge High Priority";
            } else if (m.days_in_clan > 30 && m.xp_30d === 0 && m.msgs_30d === 0) {
                status = "Zero Activity (30d)";
                type = "Purge";
            } else if (m.days_in_clan > 90 && m.msgs_total < 10 && m.xp_30d < 100000) {
                status = "Long-term Ghost";
                type = "Purge";
            }

            if (status) {
                purgingCandidates.push({ ...m, status, type });
            }
        });

        // Sort by days in clan desc
        purgingCandidates.sort((a, b) => b.days_in_clan - a.days_in_clan);

        if (purgingCandidates.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--neon-green)">No purging candidates found. Healthy roster!</td></tr>';
        } else {
            tbody.innerHTML = purgingCandidates.map(m => `
                <tr>
                    <td>${m.username}</td>
                    <td>${m.role}</td>
                    <td>${m.msgs_30d}</td>
                    <td>${formatNumber(m.xp_30d)}</td>
                    <td>${m.days_in_clan} days</td>
                    <td style="color:var(--neon-red);font-weight:bold">${m.status}</td>
                </tr>
            `).join('');
        }
    }
}

// ---------------------------------------------------------
// ADDED MISSING RENDER FUNCTIONS
// ---------------------------------------------------------

function renderPlayerRadar() {
    const ctx = document.getElementById('player-radar-chart');
    if (!ctx) return;
    if (charts.playerRadar) charts.playerRadar.destroy();

    // Compare Top 3 XP Gainers + User Average
    const top3 = dashboardData.topXPGainers.slice(0, 3);
    const datasets = top3.map((m, i) => ({
        label: m.username,
        data: [
            Math.min(100, (m.xp_7d / 1000000) * 100), // Scaled to 1M
            Math.min(100, m.msgs_7d),
            Math.min(100, m.boss_7d)
        ],
        fill: true,
        backgroundColor: i === 0 ? 'rgba(255, 215, 0, 0.2)' : (i === 1 ? 'rgba(0, 212, 255, 0.2)' : 'rgba(51, 255, 51, 0.2)'),
        borderColor: i === 0 ? '#FFD700' : (i === 1 ? '#00d4ff' : '#33FF33'),
        pointBackgroundColor: '#fff',
        pointBorderColor: '#fff'
    }));

    charts.playerRadar = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['XP Gain (Rel)', 'Messages', 'Boss Kills'],
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: { line: { borderWidth: 2 } },
            scales: {
                r: {
                    angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    pointLabels: { color: '#ccc' },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            },
            plugins: { legend: { position: 'top', labels: { color: '#e0e0e0' } } }
        }
    });
}

function renderXPvsBossChart(members) {
    // XP vs Boss Kills Scatter
    const ctx = document.getElementById('xp-boss-chart');
    if (!ctx) return;
    if (charts.xpBoss) charts.xpBoss.destroy();

    const dataPoints = members
        .filter(m => m.xp_7d > 0 && m.boss_7d > 0)
        .map(m => ({ x: m.boss_7d, y: m.xp_7d, player: m.username }));

    charts.xpBoss = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'XP vs Boss Kills (7d)',
                data: dataPoints,
                backgroundColor: 'rgba(255, 51, 51, 0.6)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Boss Kills (7d)' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: 'XP (7d)' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const p = context.raw;
                            return `${p.player}: ${p.x} kills, ${formatNumber(p.y)} XP`;
                        }
                    }
                }
            }
        }
    });

}

function renderLeaderboardChart() {
    const ctx = document.getElementById('leaderboard-chart');
    if (!ctx) return;
    if (charts.leaderboard) charts.leaderboard.destroy();

    // Composite Score: (XP / 10k) + (Boss * 5) + (Msgs * 2)
    const scores = dashboardData.allMembers.map(m => {
        const score = (m.xp_7d / 10000) + (m.boss_7d * 5) + (m.msgs_7d * 2);
        return { name: m.username, score: Math.round(score) };
    }).sort((a, b) => b.score - a.score).slice(0, 10);

    charts.leaderboard = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: scores.map(s => s.name),
            datasets: [{
                label: 'Clan Activity Score',
                data: scores.map(s => s.score),
                backgroundColor: [
                    '#FFD700', '#C0C0C0', '#CD7F32', // Gold, Silver, Bronze
                    'rgba(0, 212, 255, 0.6)', 'rgba(0, 212, 255, 0.5)',
                    'rgba(0, 212, 255, 0.4)', 'rgba(0, 212, 255, 0.3)',
                    'rgba(0, 212, 255, 0.2)', 'rgba(0, 212, 255, 0.1)', 'rgba(0, 212, 255, 0.05)'
                ],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function initComparator() {
    const p1Input = document.getElementById('comp-p1');
    const p2Input = document.getElementById('comp-p2');
    const dl = document.getElementById('player-list');

    if (!p1Input || !p2Input || !dl) return;

    // Populate Datalist
    dl.innerHTML = dashboardData.allMembers.map(m => `<option value="${m.username}">`).join('');

    const updateComp = () => {
        const p1 = dashboardData.allMembers.find(m => m.username === p1Input.value);
        const p2 = dashboardData.allMembers.find(m => m.username === p2Input.value);
        if (p1 && p2) renderComparator(p1, p2);
    };

    p1Input.addEventListener('change', updateComp);
    p2Input.addEventListener('change', updateComp);

    // Auto-select top 2 for demo
    if (dashboardData.allMembers.length >= 2) {
        p1Input.value = dashboardData.allMembers[0].username;
        p2Input.value = dashboardData.allMembers[1].username;
        updateComp();
    }
}

function renderComparator(p1, p2) {
    const ctx = document.getElementById('comparator-radar');
    const tbody = document.getElementById('comparator-body');

    // 1. Radar
    if (charts.comparator) charts.comparator.destroy();

    // Normalize data for radar
    const maxXP = Math.max(p1.xp_7d, p2.xp_7d, 100000);
    const maxBoss = Math.max(p1.boss_7d, p2.boss_7d, 10);
    const maxMsg = Math.max(p1.msgs_7d, p2.msgs_7d, 10);

    const getData = (p) => [
        (p.xp_7d / maxXP) * 100,
        (p.boss_7d / maxBoss) * 100,
        (p.msgs_7d / maxMsg) * 100
    ];

    charts.comparator = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['XP Gain', 'Boss Kills', 'Messages'],
            datasets: [
                {
                    label: p1.username,
                    data: getData(p1),
                    borderColor: '#00d4ff', // Blue
                    backgroundColor: 'rgba(0, 212, 255, 0.2)',
                },
                {
                    label: p2.username,
                    data: getData(p2),
                    borderColor: '#ffb84d', // Orange
                    backgroundColor: 'rgba(255, 184, 77, 0.2)',
                }
            ]
        },
        options: {
            scales: { r: { suggestedMin: 0, suggestedMax: 100, grid: { color: 'rgba(255,255,255,0.1)' } } },
            plugins: { legend: { labels: { color: '#ccc' } } }
        }
    });

    // 2. Table
    const compareRow = (label, v1, v2, isNum = true) => {
        let diff = isNum ? (v1 - v2) : 0;
        let diffStr = isNum ? (diff > 0 ? `+${formatNumber(diff)}` : formatNumber(diff)) : '';
        let diffClass = diff > 0 ? 'diff-pos' : (diff < 0 ? 'diff-neg' : 'diff-neu');
        if (diff === 0) diffClass = 'diff-neu';

        // Invert for Orange (P2) advantage? No, Diff usually P1 - P2
        // Just color P1 winning as Blue, P2 winning as Orange
        if (v1 > v2) diffClass = 'diff-pos'; // Blue
        else if (v2 > v1) diffClass = 'diff-neg'; // Orange

        return `
            <tr>
                <td>${label}</td>
                <td style="color:#00d4ff">${isNum ? formatNumber(v1) : v1}</td>
                <td style="color:#ffb84d">${isNum ? formatNumber(v2) : v2}</td>
                <td class="${diffClass}">${diffStr}</td>
            </tr>
        `;
    };

    tbody.innerHTML = `
        ${compareRow('Role', p1.role, p2.role, false)}
        ${compareRow('Total XP', p1.total_xp, p2.total_xp)}
        ${compareRow('XP (7d)', p1.xp_7d, p2.xp_7d)}
        ${compareRow('Boss Kills (7d)', p1.boss_7d, p2.boss_7d)}
        ${compareRow('Messages (7d)', p1.msgs_7d, p2.msgs_7d)}
    `;
}

function renderTime(id, isoDate) {
    const el = document.getElementById(id);
    if (el && isoDate) {
        const d = new Date(isoDate);
        el.innerText = d.toLocaleString('en-GB').replace(/\//g, '-');
    }
}

// Player Profile Modal Handling
window.openPlayerProfile = function (username) {
    const m = dashboardData.allMembers.find(p => p.username === username);
    if (!m) return;

    const modal = document.getElementById('player-profile-modal');
    if (!modal) return;

    document.getElementById('pp-username').innerText = m.username;
    document.getElementById('pp-role').innerText = m.role;

    // Dynamic Profile Background
    const header = document.querySelector('.profile-header');
    if (header) {
        if (m.favorite_boss_all_time_img && m.favorite_boss_all_time_img !== 'boss_pet_rock.png') {
            header.style.backgroundImage = `linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.9)), url('assets/${m.favorite_boss_all_time_img}')`;
            header.style.backgroundSize = 'cover';
            header.style.backgroundPosition = 'center';
        } else {
            // Default Gradient
            header.style.background = 'linear-gradient(180deg, rgba(255, 215, 0, 0.1) 0%, transparent 100%)';
        }
    }
    document.getElementById('pp-total-xp').innerText = formatNumber(m.total_xp);
    document.getElementById('pp-total-boss').innerText = formatNumber(m.total_boss);
    document.getElementById('pp-total-msg').innerText = formatNumber(m.msgs_total);
    if (m.days_in_clan !== undefined) {
        // document.getElementById('pp-days').innerText = m.days_in_clan + ' Days';
        // If there is an element for Joined Date or Days
    }

    document.getElementById('pp-xp-7d').innerText = formatNumber(m.xp_7d);
    document.getElementById('pp-boss-7d').innerText = m.boss_7d;

    // Images
    const rankImg = document.getElementById('pp-rank-img');
    if (rankImg) rankImg.src = `assets/${m.rank_img || 'rank_minion.png'}`;

    document.getElementById('pp-top-skill').innerText = m.favorite_boss || 'Unknown';
    // Reusing Top Skill for Fav Boss for now as data structure suggests

    modal.style.display = 'flex';
}

window.closePlayerProfile = function () {
    const modal = document.getElementById('player-profile-modal');
    if (modal) modal.style.display = 'none';
}

