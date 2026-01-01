/**
 * Clan Dashboard Logic
 * Handles data loading, chart rendering, and interactions.
 */

// Global State
let dashboardData = null;
let charts = {};
let currentPeriod = '7d'; // Default timeframe
let CONFIG = {
    LB_BOSS_WEIGHT: 3,
    LB_MSG_WEIGHT: 6,
    PURGE_DAYS: 30,
    PURGE_MIN_XP: 0,
    PURGE_MIN_BOSS: 0,
    PURGE_MIN_MSGS: 0,
    LEADERBOARD_SIZE: 10,
    TOP_BOSS_CARDS: 5
};

// Global Error Handler
window.onerror = function (msg, url, lineNo, columnNo, error) {
    console.error("Global Error: " + msg, error);
    const el = document.getElementById('updated-time');
    if (el) el.innerHTML = `<span style="color:red">Error: ${msg}</span>`;

    // NEW: SweetAlert Error
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'error',
            title: 'System Error',
            text: msg,
            background: '#1a1c2e',
            color: '#fff'
        });
    }
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
    // Also resize G2Plot charts
    Object.values(charts).forEach(chart => {
        if (chart && typeof chart.resize === 'function') chart.resize();
    });

    // 5. Force chart updates after resize
    setTimeout(() => {
        if (typeof Chart !== 'undefined') {
            Object.values(Chart.instances).forEach(chart => {
                if (chart && typeof chart.update === 'function') chart.update();
            });
        }
        Object.values(charts).forEach(chart => {
            if (chart && typeof chart.update === 'function') chart.update();
        });
    }, 100);
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

                // Initialize Config
                if (dashboardData.config) {
                    CONFIG.LB_BOSS_WEIGHT = dashboardData.config.leaderboard_weight_boss || 3;
                    CONFIG.LB_MSG_WEIGHT = dashboardData.config.leaderboard_weight_msgs || 6;
                    CONFIG.PURGE_DAYS = dashboardData.config.purge_threshold_days || 30;
                    CONFIG.PURGE_MIN_XP = dashboardData.config.purge_min_xp || 0;
                    CONFIG.PURGE_MIN_BOSS = dashboardData.config.purge_min_boss || 0;
                    CONFIG.PURGE_MIN_MSGS = dashboardData.config.purge_min_msgs || 0;
                    CONFIG.LEADERBOARD_SIZE = dashboardData.config.leaderboard_size || 10;
                    CONFIG.TOP_BOSS_CARDS = dashboardData.config.top_boss_cards || 4;
                }

                console.log("Loaded data from clan_data.json", CONFIG);
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

        console.log("Dashboard data loaded successfully:", dashboardData.generated_at, "with", dashboardData.allMembers ? dashboardData.allMembers.length : 0, "members");

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
        safelyRun(() => renderInactiveWatchlist(dashboardData.allMembers), "renderInactiveWatchlist");

        // New Render Functions
        console.log("Starting to render tab sections...");
        safelyRun(() => renderFullRoster(dashboardData.allMembers), "renderFullRoster");
        safelyRun(() => renderMessagesSection(dashboardData.allMembers), "renderMessagesSection");
        safelyRun(() => renderXpSection(dashboardData.allMembers), "renderXpSection");
        safelyRun(() => renderBossesSection(dashboardData.allMembers), "renderBossesSection");
        safelyRun(() => renderOutliersSection(dashboardData.allMembers), "renderOutliersSection");
        safelyRun(() => renderAIInsights(dashboardData.allMembers), "renderAIInsights");

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
// ---------------------------------------------------------
// OPTIMIZED TABLE SORTING (Async with Spinner)
// ---------------------------------------------------------
window.sortTable = function (n) {
    const table = document.getElementById("roster-table");
    if (!table) return;

    // Determine Sort Direction
    const prevCol = table.dataset.sortCol ? parseInt(table.dataset.sortCol, 10) : null;
    const prevDir = table.dataset.sortDir || 'asc';
    let dir = 'asc';
    if (prevCol === n && prevDir === 'asc') dir = 'desc';

    table.dataset.sortCol = n;
    table.dataset.sortDir = dir;

    // Update Header Icons
    updateSortIcons(table, n, dir);

    // Show Loading Spinner (Critical for UX on large tables)
    const tbody = document.getElementById("roster-body");
    if (tbody) {
        // height: 500px ensures the table doesn't collapse excessively during sort
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:50px;"><div class="spinner"></div> Sorting Roster...</td></tr>';
    }

    // Defer the heavy lifting to allow the browser to paint the spinner
    setTimeout(() => {
        performSort(n, dir);
    }, 10);
};

function updateSortIcons(table, colIdx, dir) {
    const headers = table.querySelectorAll('th');
    headers.forEach((th, i) => {
        const icon = th.querySelector('i');
        if (!icon) return;
        icon.className = 'fas fa-sort'; // Reset
        icon.style.opacity = '0.3';

        if (i === colIdx) {
            icon.className = dir === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down';
            icon.style.opacity = '1';
            icon.style.color = 'var(--neon-gold)'; // Highlight active sort
        }
    });
}

function performSort(n, dir) {
    // Column Mapping
    // 0: Player (string)
    // 1: XP 7d
    // 2: XP Total
    // 3: Boss 7d
    // 4: Boss Total
    // 5: Msgs 7d
    // 6: Msgs Total
    // 7: Ratio (Total XP / Total Msgs)
    // 8: Days

    const members = dashboardData.allMembers;
    if (!members) return;

    // Create a copy to sort
    const sorted = [...members].sort((a, b) => {
        let valA, valB;

        switch (n) {
            case 0: // Username
                valA = a.username.toLowerCase();
                valB = b.username.toLowerCase();
                return dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
            case 1: valA = a.xp_7d || 0; valB = b.xp_7d || 0; break;
            case 2: valA = a.total_xp || 0; valB = b.total_xp || 0; break;
            case 3: valA = a.boss_7d || 0; valB = b.boss_7d || 0; break;
            case 4: valA = a.total_boss || 0; valB = b.total_boss || 0; break;
            case 5: valA = a.msgs_7d || 0; valB = b.msgs_7d || 0; break;
            case 6: valA = a.msgs_total || 0; valB = b.msgs_total || 0; break;
            case 7: // Ratio
                valA = a.msgs_total > 0 ? (a.total_xp / a.msgs_total) : 0;
                valB = b.msgs_total > 0 ? (b.total_xp / b.msgs_total) : 0;
                break;
            case 8: valA = a.days_in_clan || 0; valB = b.days_in_clan || 0; break;
            default: return 0;
        }

        // Numeric Sort
        return dir === 'asc' ? valA - valB : valB - valA;
    });

    // Re-render
    renderFullRoster(sorted);
}


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
             <div class="top-stat-container">
                <img src="assets/${topXpMember.rank_img || 'rank_minion.png'}" class="top-stat-rank-img">
                <div class="top-stat-username">${topXpMember.username}</div>
                <div class="top-stat-value">${formatNumber(topXpMember[xpKey])}</div>
            </div>
        `);
    }

    // Top Messenger
    const topMsgMember = [...members].sort((a, b) => b[msgKey] - a[msgKey])[0];
    if (topMsgMember) {
        setHtml('stat-top-msg', `
             <div class="top-stat-container">
                <img src="assets/${topMsgMember.rank_img || 'rank_minion.png'}" class="top-stat-rank-img">
                <div class="top-stat-username">${topMsgMember.username}</div>
                <div class="top-stat-value" style="color:var(--neon-green)">${formatNumber(topMsgMember[msgKey])}</div>
            </div>
        `);
    }

    // Rising Star: Joined < 14 weeks (98 days) AND Highest Messages
    // Filter by days_in_clan < 98
    const newcomers = members.filter(m => m.days_in_clan < 98);
    // Sort by messages (total or 7d? "sent the most messages" implies recent activity usually, but let's stick to 7d or total if user meant historical. Given context "rising", 7d makes sense to show WHO IS POPPING OFF, but "joined within last 14 weeks" implies finding the best new recruit. NEW RECRUIT = TOTAL MESSAGES usually better metric for 'best integration'. Let's use 7d as it shows CURRENT activity which is usually what rising star means).
    // Let's use msgs_7d for "Rising" momentum.
    const risingStar = newcomers.sort((a, b) => b.msgs_7d - a.msgs_7d)[0];

    if (risingStar) {
        setHtml('stat-rising-star', `
             <div class="top-stat-container">
                <img src="assets/${risingStar.rank_img || 'rank_minion.png'}" class="top-stat-rank-img">
                <div class="top-stat-username">${risingStar.username}</div>
                <div class="top-stat-value" style="color:var(--neon-blue)">${formatNumber(risingStar.msgs_7d)}</div>
            </div>
        `);
    } else {
        setHtml('stat-rising-star', "No Newcomers");
    }

    // 5. Active Members (Active in last 30d via XP or Msgs)
    const activeCount = members.filter(m => (m.msgs_30d > 0 || m.xp_30d > 0)).length;
    setHtml('stat-active-members', formatNumber(activeCount));

    // Top Boss (Default to static if no dynamic boss data available for 30d, or sort by boss_score if available)
    if (data.topBossKiller) {
        const m = data.topBossKiller;
        // Try to find full member data
        const fullMember = members.find(p => p.username === m.name);

        let bossImg = 'rank_minion.png';

        if (fullMember) {
            // Priority: User's actual favorite boss image
            if (fullMember.favorite_boss_img && fullMember.favorite_boss_img !== 'boss_pet_rock.png') {
                bossImg = fullMember.favorite_boss_img;
            }
            // Fallback to rank image if exists
            else if (fullMember.rank_img) {
                bossImg = fullMember.rank_img;
            }
        }
        // Last resort: use leaderboard data if available
        else if (m.rank_img) {
            bossImg = m.rank_img;
        }

        setHtml('stat-top-boss', `
             <div class="top-stat-container ${fullMember?.context_class || 'context-general'}">
                <img src="assets/${bossImg}" class="top-stat-rank-img" onerror="this.src='assets/rank_minion.png';this.onerror=null;">
                <div class="top-stat-username">${m.name}</div>
                <div class="top-stat-value" style="color:var(--neon-red)">${formatNumber(m.kills)}</div>
            </div>
        `);
    } else {
        setHtml('stat-top-boss', `
             <div class="top-stat-container">
                <img src="assets/rank_minion.png" class="top-stat-rank-img">
                <div class="top-stat-value" style="color:#999;font-size:1.1rem">No Data</div>
            </div>
        `);
    }
}

function renderNewsTicker(members) {
    const tickerContainer = document.getElementById('news-ticker');
    if (!tickerContainer) return;

    // AI PULSE INTEGRATION
    if (dashboardData.ai && dashboardData.ai.pulse && dashboardData.ai.pulse.length > 0) {
        console.log("Using AI Pulse Data");
        let html = dashboardData.ai.pulse.map(item => `<span style="color:var(--neon-green)">[AI-NET]</span> ${item}`).join(' &nbsp;&bull;&nbsp; ');

        // Loop it for smoothness
        if (dashboardData.ai.pulse.length < 5) html += ' &nbsp;&bull;&nbsp; ' + html;
        tickerContainer.innerHTML = html;
        return;
    }

    // Fallback to Legacy Logic
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

    let cardsHtml = '';

    // AI ALERTS INTEGRATION
    if (window.aiData && window.aiData.alerts) {
        window.aiData.alerts.forEach(alert => {
            const colorVar = alert.type === 'success' ? 'var(--neon-green)' : 'var(--neon-red)';
            cardsHtml += `
            <div class="alert-card" style="border-left: 3px solid ${colorVar}">
                <div class="alert-header" style="display:flex;align-items:center;gap:10px;margin-bottom:10px;color:${colorVar}">
                    <i class="fas ${alert.icon}"></i>
                    <span style="font-family:'Cinzel'">${alert.title}</span>
                </div>
                <div class="alert-metric" style="color:#ccc; font-size: 0.9em;">
                    ${alert.message}
                </div>
            </div>
            `;
        });
    }

    if (atRisk.length === 0 && cardsHtml === '') {
        alertsContainer.innerHTML = '<div class="glass-card" style="padding:20px;grid-column:1/-1;text-align:center;color:#4fec4f">No immediate risks detected.</div>';
        return;
    }

    // Optimized: Build HTML string first (Single DOM write)
    cardsHtml += atRisk.map(m => `
        <div class="alert-card">
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
        </div>
    `).join('');

    alertsContainer.innerHTML = cardsHtml;
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

    // Filter: 0 msgs in last 30d (or PURGE_DAYS)
    const inactive = members.filter(m => m.msgs_30d === 0 && m.days_in_clan > CONFIG.PURGE_DAYS).slice(0, 20);

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
    const container = document.getElementById('container-scatter-interaction');
    if (!container) return;
    if (charts.scatterInt) charts.scatterInt.destroy();

    const members = dashboardData.allMembers;
    const dataPoints = members
        .filter(m => m.msgs_30d > 0 || m.xp_30d > 0)
        .map(m => ({
            msgs: m.msgs_30d,
            xp: m.xp_30d,
            player: m.username,
            role: m.role
        }));

    // Cap the x-axis at the highest observed value (with minimal buffer)
    const maxMsgs = dataPoints.length ? Math.max(...dataPoints.map(d => d.msgs)) : 0;
    const xMax = maxMsgs ? Math.ceil(maxMsgs * 1.02) : undefined;

    const scatter = new G2Plot.Scatter('container-scatter-interaction', {
        appendPadding: 30,
        data: dataPoints,
        xField: 'msgs',
        yField: 'xp',
        colorField: 'role',
        size: 5,
        shape: 'circle',
        pointStyle: { fillOpacity: 0.8, stroke: '#fff', lineWidth: 1 },
        xAxis: {
            title: { text: 'Messages (30d)', style: { fill: '#888' } },
            grid: { line: { style: { stroke: '#333', lineDash: [4, 4] } } },
            label: { style: { fill: '#888' } },
            max: xMax,
            minLimit: 0
        },
        yAxis: {
            title: { text: 'XP Gained (30d)', style: { fill: '#888' } },
            grid: { line: { style: { stroke: '#333', lineDash: [4, 4] } } },
            label: { formatter: (v) => formatNumber(Number(v)), style: { fill: '#888' } },
            min: 0
        },
        tooltip: {
            fields: ['player', 'msgs', 'xp', 'role'],
            formatter: (datum) => {
                return { name: datum.player, value: `${datum.msgs} msgs, ${formatNumber(datum.xp)} XP` };
            },
            showTitle: false
        },
        theme: 'dark',
        legend: { position: 'top' }
    });

    scatter.render();
    charts.scatterInt = scatter;
}

function renderBossDiversity() {
    const container = document.getElementById('container-boss-diversity');
    if (!container) return;
    const data = dashboardData.chart_boss_diversity;
    if (!data) return;

    if (charts.bossDiv) charts.bossDiv.destroy();

    // Transform Data for Donut Chart (Cleaner than Rose)
    const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
    let chartData = data.labels
        .map((label, i) => ({
            type: label,
            value: data.datasets[0].data[i]
        }))
        .filter(d => d.value > 0 && d.type.toLowerCase() !== 'other')
        .sort((a, b) => b.value - a.value);

    // NO Grouping small slices (User Request: Show All)
    // NO Grouping logic here. All slices shown.

    const donut = new G2Plot.Pie('container-boss-diversity', {
        appendPadding: 10,
        data: chartData,
        angleField: 'value',
        colorField: 'type',
        radius: 0.8,
        innerRadius: 0.64,
        label: {
            type: 'spider', // Better labeling for diversity
            labelHeight: 28,
            content: '{name}\n{percentage}',
        },
        interactions: [{ type: 'element-active' }, { type: 'pie-statistic-active' }],
        theme: 'dark',
        statistic: {
            title: false,
            content: {
                style: {
                    whiteSpace: 'pre-wrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    fontSize: '18px',
                    color: '#fff'
                },
                content: 'Total\n' + formatNumber(total),
            },
        },
    });

    donut.render();
    charts.bossDiv = donut;
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

    // Safety Check: if no trend data, fallback to most killed boss across group (30d assumed)
    if (!data || !data.chart_data || !data.chart_data.datasets || !data.chart_data.datasets[0]) {
        let fallbackBoss = null;
        if (dashboardData.allMembers) {
            const topMember = [...dashboardData.allMembers].sort((a, b) => (b.boss_30d || 0) - (a.boss_30d || 0))[0];
            if (topMember && topMember.favorite_boss) fallbackBoss = topMember.favorite_boss;
        }
        if (!fallbackBoss) {
            const fallback = dashboardData.chart_boss_diversity;
            if (fallback && fallback.labels && fallback.datasets && fallback.datasets[0]) {
                const filtered = fallback.labels.map((label, idx) => ({ label, val: fallback.datasets[0].data[idx] }))
                    .filter(item => item.label.toLowerCase() !== 'other');
                if (filtered.length) fallbackBoss = filtered.sort((a, b) => b.val - a.val)[0].label;
            }
        }
        if (nameEl) nameEl.innerText = fallbackBoss || "No data";
        ctx.style.display = 'none';

        const container = ctx.parentElement;
        let msg = container.querySelector('.no-data-msg-boss');
        if (!msg) {
            msg = document.createElement('div');
            msg.className = 'no-data-msg-boss';
            msg.innerText = fallbackBoss ? `No trend data. Fallback: ${fallbackBoss}` : "No Trending Boss Data Available";
            msg.style.cssText = "text-align:center; padding: 2rem; color: #666; font-style: italic;";
            container.appendChild(msg);
        }
        return;
    }

    // Ensure visible if data exists
    ctx.style.display = 'block';
    const container = ctx.parentElement;
    const msg = container.querySelector('.no-data-msg-boss');
    if (msg) msg.remove();

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

    // NEW CHARTS
    renderScatterInteraction();
    renderBossDiversity();
    renderRaidsPerformance();
    renderSkillMastery();
    renderBossTrend();
    renderTenureChart();
    renderXPWeeklyCorrelation();
    renderLeaderboardChart();

    // UPDATED VISUALIZATIONS
    renderActivityHeatmap();     // NEW: Weekly 24h Heatmap
    renderActivityTrend();       // NEW: Weekly Trend (Replaces Correlation/Area)
    renderXPContribution();      // NEW: Top 25 Annual XP (Replaces Radar)
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

function renderActivityCorrelation() {
    const container = document.getElementById('container-activity-trend');
    if (!container) return;
    if (charts.trend) charts.trend.destroy();

    const history = dashboardData.history || [];
    const dualData = [];

    history.forEach(d => {
        const dateStr = new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
        dualData.push({
            date: dateStr,
            xp: d.xp || 0,
            msgs: d.msgs || 0
        });
    });

    if (dualData.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:2rem;color:#666;font-style:italic;">No activity history available</div>';
        return;
    }

    const dualAxes = new G2Plot.DualAxes('container-activity-trend', {
        data: [dualData, dualData],
        xField: 'date',
        yField: ['xp', 'msgs'],
        geometryOptions: [
            { geometry: 'column', color: '#00d4ff' }, // XP Bars
            { geometry: 'line', color: '#FFD700', lineStyle: { lineWidth: 3 } } // Msg Line
        ],
        theme: 'dark',
        meta: {
            xp: { alias: 'XP Gained', formatter: (v) => formatNumber(Number(v)) },
            msgs: { alias: 'Messages' }
        },
        yAxis: [
            { min: 0, label: { formatter: (v) => formatNumber(Number(v)) } }, // Left: XP
            { min: 0 } // Right: Messages
        ],
        legend: { position: 'top-left' }
    });

    dualAxes.render();
    charts.trend = dualAxes;
}

function renderXPContribution() {
    const container = document.getElementById('xp-contribution-chart');
    if (!container) return;
    // Note: If using G2Plot, charts are instances on the DOM element. 
    // chart.js instance map might need cleanup if reusing keys.
    if (charts.xpContrib) charts.xpContrib.destroy();

    const members = dashboardData.allMembers;
    const sorted = [...members].sort((a, b) => (b.xp_30d || b.xp_7d) - (a.xp_30d || a.xp_7d));

    const active = sorted.filter(m => (m.xp_30d || m.xp_7d) > 0);
    const showCount = 25;
    const topSlice = active.slice(0, showCount);

    // Approximate annual XP using 30d if present else 7d
    const annualData = topSlice.map(m => {
        const base = m.xp_30d ? m.xp_30d * 12 : (m.xp_7d || 0) * 52;
        return { type: m.username, value: base };
    });

    const column = new G2Plot.Column('xp-contribution-chart', {
        data: annualData,
        xField: 'type',
        yField: 'value',
        theme: 'dark',
        color: '#33FF33',
        meta: {
            value: { alias: 'Annualized XP', formatter: (v) => formatNumber(v) }
        },
        xAxis: {
            label: { autoRotate: true, autoHide: true }
        },
        yAxis: {
            min: 0,
            label: { formatter: (v) => formatNumber(Number(v)) }
        },
        tooltip: {
            formatter: (d) => ({ name: d.type, value: `${formatNumber(d.value)} XP/yr` })
        }
    });

    column.render();
    charts.xpContrib = column;
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
    console.log("renderFullRoster called with", members ? members.length : 0, "members");
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
    console.log("renderMessagesSection called with", members ? members.length : 0, "members");
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
                <td>${formatNumber(m.msgs_30d || 0)}</td> 
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
        heatmap.style.height = '100%'; // Use container height
        heatmap.style.minHeight = '120px'; // Ensure visibility
        heatmap.style.alignItems = 'end'; // bars from bottom
        heatmap.style.justifyItems = 'center';

        const maxVal = Math.max(...dashboardData.activity_heatmap);
        const totalVal = dashboardData.activity_heatmap.reduce((a, b) => a + b, 0);
        if (totalVal === 0) {
            heatmap.innerHTML = '<div style="text-align:center;padding:1.5rem;color:#666;font-style:italic;grid-column:1/-1">No hourly activity recorded</div>';
            return;
        }

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
    console.log('renderXpSection called with', members ? members.length : 'no', 'members');
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
    const ctxScat = document.getElementById('container-activity-trend');
    if (ctxScat) {
        if (charts.scat) charts.scat.destroy();
        // Filter outliers for better chart view
        const dataPoints = members
            .filter(m => m.xp_7d > 0 && m.msgs_7d > 0 && m.xp_7d < 40000000 && m.msgs_7d < 1500)
            .map(m => ({ x: m.msgs_7d, y: m.xp_7d, r: 5, player: m.username }));

        // Clear any existing content and create canvas
        ctxScat.innerHTML = '<canvas id="xp-messages-scatter"></canvas>';
        const canvas = ctxScat.querySelector('#xp-messages-scatter');

        charts.scat = new Chart(canvas, {
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

    // XP Contribution Chart (Top 25)
    const ctxContrib = document.getElementById('xp-contribution-chart');
    if (ctxContrib) {
        if (charts.contrib) charts.contrib.destroy();
        // Render annualized XP contribution here too so both entry points stay consistent
        const top25 = [...members].sort((a, b) => (b.xp_30d || b.xp_7d) - (a.xp_30d || a.xp_7d)).slice(0, 25);
        const data = top25.map(m => {
            const base = m.xp_30d ? m.xp_30d * 12 : (m.xp_7d || 0) * 52;
            return { name: m.username, value: base };
        });
        try {
            const columnPlot = new G2Plot.Column(ctxContrib, {
                data,
                xField: 'name',
                yField: 'value',
                theme: 'dark',
                color: '#33FF33',
                meta: {
                    value: {
                        alias: 'Annualized XP',
                        formatter: (v) => formatNumber(v)
                    }
                },
                xAxis: {
                    label: {
                        autoRotate: true,
                        autoHide: true
                    }
                },
                tooltip: {
                    formatter: (datum) => {
                        return { name: datum.name, value: formatNumber(datum.value) + ' XP/yr' };
                    }
                }
            });
            columnPlot.render();
            charts.contrib = columnPlot;
        } catch (e) {
            console.warn("Failed to render XP Contribution chart:", e);
            ctxContrib.innerHTML = `<div style="text-align:center;padding:20px;color:#ff6b6b">Error rendering chart</div>`;
        }
    }

    // Remove the call to renderXPvsBossChart since it doesn't belong here
    // renderXPvsBossChart(members);
}

function renderBossesSection(members) {
    console.log("renderBossesSection called with", members ? members.length : 0, "members");
    renderTime('updated-time-boss', dashboardData.generated_at);

    // Top Boss Cards
    const cards = document.getElementById('boss-cards');
    if (cards) {
        cards.innerHTML = '';
        const topKillers = [...members].sort((a, b) => (b.boss_7d || 0) - (a.boss_7d || 0)).slice(0, CONFIG.TOP_BOSS_CARDS);
        topKillers.forEach(m => {
            const bg = m.favorite_boss_img || 'boss_pet_rock.png';
            cards.innerHTML += `
                <div class="glass-card stat-card" style="position:relative; overflow:hidden; aspect-ratio:2/3; display:flex; flex-direction:column; justify-content:flex-end; padding:15px; text-align:center;">
                    <div style="position:absolute; inset:0; background-image:url('assets/${bg}'); background-size:cover; background-position:center; opacity:0.3; transition:transform 0.5s;"></div>
                    <div style="position:relative; z-index:1; text-shadow:0 2px 10px rgba(0,0,0,0.8);">
                        <div style="font-weight:700; font-size:1.1rem; color:#fff; margin-bottom:5px;">${m.username}</div>
                        <div style="font-family:'Cinzel'; font-size:1.8rem; color:var(--neon-red); line-height:1;">${formatNumber(m.boss_30d || 0)}</div>
                        <div style="font-size:0.8rem; color:#aaa; margin-top:5px; text-transform:uppercase; letter-spacing:1px;">Kills (7d)</div>
                         <div style="font-size:0.75rem; color:var(--neon-gold); margin-top:8px; border-top:1px solid rgba(255,255,255,0.1); padding-top:4px;">${m.favorite_boss || 'Unknown'}</div>
                    </div>
                </div>
             `;
        });
    }

    // Table
    const tbody = document.querySelector('#bosses-table tbody');
    if (tbody) {
        // FIXED sorting: Now sorts by 7d kills (Top Killer)
        const sorted = [...members].sort((a, b) => b.boss_7d - a.boss_7d).slice(0, 50);
        tbody.innerHTML = sorted.map((m, i) => `
            <tr>
                <td>#${i + 1}</td>
                <td>${m.username}</td>
                <td>${m.role}</td>
                <td style="color:rgba(255,255,255,0.7)">${formatNumber(m.total_boss)}</td>
                <td style="color:var(--neon-red);font-weight:bold">+${formatNumber(m.boss_7d)}</td>
                <td style="color:rgba(255,255,255,0.7)">+${formatNumber(m.boss_30d || 0)}</td>
            </tr>
        `).join('');
    }
}

function renderOutliersSection(members) {
    console.log("renderOutliersSection called with", members ? members.length : 0, "members");
    renderTime('updated-time-out', dashboardData.generated_at);

    const tbody = document.querySelector('#outliers-table tbody');
    if (tbody) {
        const purgingCandidates = getPurgeCandidates(members);

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

/**
 * Pure Function: Determine Purge Candidates
 * @param {Array} members 
 * @returns {Array} List of candidates with status/type
 */
function getPurgeCandidates(members) {
    const candidates = [];

    members.forEach(m => {
        let status = null;
        let type = "";

        // Criteria for Purging - Uses CONFIG if available, else defaults
        const pDays = CONFIG.PURGE_DAYS || 30;
        const minXP = CONFIG.PURGE_MIN_XP || 0;
        const minBoss = CONFIG.PURGE_MIN_BOSS || 0;
        const minMsgs = CONFIG.PURGE_MIN_MSGS || 0;

        if (m.days_in_clan > 60 && m.xp_30d < minXP && m.boss_30d < minBoss && m.msgs_30d === minMsgs) {
            status = "Terminally Inactive";
            type = "Purge High Priority";
        } else if (m.days_in_clan > pDays && m.xp_30d === 0 && m.msgs_30d === 0) {
            status = "Zero Activity (30d)";
            type = "Purge";
        } else if (m.days_in_clan > 90 && m.msgs_total < minMsgs && m.xp_30d < 100000) {
            status = "Long-term Ghost";
            type = "Purge";
        }

        if (status) {
            candidates.push({ ...m, status, type });
        }
    });

    return candidates.sort((a, b) => b.days_in_clan - a.days_in_clan);
}

// ---------------------------------------------------------
// ADDED MISSING RENDER FUNCTIONS
// ---------------------------------------------------------

function renderActivityHeatmap() {
    // 24h Hourly Activity (Aggregated)
    const container = 'activity-heatmap';
    if (!document.getElementById(container)) return;
    if (charts.heatmap) charts.heatmap.destroy();

    const data = dashboardData.activity_heatmap;
    if (!data || !Array.isArray(data) || data.length === 0) {
        document.getElementById(container).innerHTML = '<div class="no-data">No heatmap data</div>';
        return;
    }

    // transform [v0, v1...] to [{hour: '00:00', value: v0}, ...]
    const plotData = data.map((val, idx) => ({
        hour: `${String(idx).padStart(2, '0')}:00`,
        value: Number(val) || 0
    }));

    try {
        const column = new G2Plot.Column(container, {
            data: plotData,
            xField: 'hour',
            yField: 'value',
            color: '#00d4ff',
            columnStyle: {
                radius: [4, 4, 0, 0],
            },
            autoFit: true,
            theme: 'dark',
            meta: {
                value: { alias: 'Messages' }
            },
            xAxis: {
                label: { autoRotate: false, style: { fill: '#666', fontSize: 10 } },
                grid: null
            },
            yAxis: {
                grid: { line: { style: { stroke: '#333', lineDash: [2, 2] } } }
            },
            tooltip: {
                formatter: (datum) => {
                    return { name: 'Activity', value: datum.value + ' msgs' };
                }
            }
        });

        column.render();
        charts.heatmap = column;
    } catch (e) {
        console.warn("Failed to render Heatmap:", e);
    }
}

function renderActivityTrend() {
    // Weekly Activity Trend (Line/Area Chart)
    const container = 'container-activity-trend';
    const el = document.getElementById(container);
    if (!el) return;

    // Clear previous if G2Plot attached to div
    el.innerHTML = '';

    const hist = dashboardData.history; // This is a list of objects: [{date: '...', msgs: ...}, ...]
    if (!hist || !Array.isArray(hist) || hist.length === 0) {
        el.innerHTML = '<div class="no-data">No trend data available</div>';
        return;
    }

    // Transform to [{date: '...', value: ..., category: 'Messages'}, ...]
    const data = hist.map(item => ({
        date: item.date,
        value: Number(item.msgs) || 0,
        category: 'Messages'
    }));

    try {
        const area = new G2Plot.Area(container, {
            data: data,
            xField: 'date',
            yField: 'value',
            seriesField: 'category',
            color: ['#00d4ff'],
            areaStyle: {
                fill: 'l(270) 0:#00d4ff 1:rgba(0, 212, 255, 0.1)',
            },
            theme: 'dark',
            xAxis: {
                range: [0, 1], // optimize time axis range
                label: { style: { fill: '#666' }, autoRotate: true }
            },
            yAxis: {
                grid: { line: { style: { stroke: '#333' } } },
                label: { formatter: (v) => formatNumber(Number(v)) }
            },
            legend: false,
            tooltip: {
                showMarkers: true
            },
            smooth: true,
            animation: {
                appear: {
                    animation: 'wave-in',
                    duration: 1000,
                },
            },
        });

        area.render();
        charts.activityTrend = area;
    } catch (e) {
        console.warn("Failed to render Activity Trend:", e);
    }
}

function renderXPContribution() {
    // Top 25 Annualized XP (Bar Chart)
    const container = 'xp-contribution-chart';
    if (!document.getElementById(container)) return;

    document.getElementById(container).innerHTML = '';

    const data = dashboardData.topXPYear || [];
    if (!Array.isArray(data) || data.length === 0) {
        document.getElementById(container).innerHTML = '<div class="no-data">No Annual XP Data</div>';
        return;
    }

    // Prepare for G2Plot Bar (Horizontal)
    const plotData = data.slice(0, 25).map(m => {
        // Safe number extraction
        let val = m.xp_year;
        if (!val) val = (m.xp_30d || 0) * 12;
        if (!val) val = (m.xp_7d || 0) * 52;
        return {
            username: m.username,
            xp: Number(val) || 0
        };
    }).sort((a, b) => a.xp - b.xp); // Sort ascending for bar chart (appears descending)

    // Dynamic height based on item count to avoid crowding
    const chartHeight = Math.max(400, plotData.length * 30);

    try {
        const bar = new G2Plot.Bar(container, {
            data: plotData,
            height: chartHeight,
            xField: 'xp',
            yField: 'username',
            seriesField: 'username', // Color by user
            color: '#FFD700', // Gold color for Annual XP
            barStyle: { radius: [0, 2, 2, 0] },
            theme: 'dark',
            xAxis: {
                label: { formatter: (v) => formatNumber(Number(v)) },
                grid: { line: { style: { stroke: '#333' } } }
            },
            yAxis: {
                label: { style: { fill: '#ccc', fontSize: 11 } }
            },
            legend: false,
            tooltip: {
                formatter: (d) => ({ name: 'Annual XP', value: formatNumber(d.xp) })
            },
            scrollbar: { type: 'vertical' }
        });

        bar.render();
        charts.xpContribution = bar;
    } catch (e) {
        console.warn("Failed to render XP Contribution:", e);
    }
}




function renderPlayerRadar() {
    const container = 'player-radar-chart';
    if (!document.getElementById(container)) return;

    // Destroy existing chart instance if it exists (using the key 'playerRadar' which we will reuse)
    if (charts.playerRadar) charts.playerRadar.destroy();

    // 1. Get Top 5 Players (by XP for now, or weighted score)
    const top5 = dashboardData.topXPGainers.slice(0, 5);

    // 2. Prepare Data for Grouped Column Chart (Normalized)
    // We want to compare them across 3 metrics: XP, Messages, Boss Kills
    // Issues: Values are vastly different scales (XP in millions, others in hundreds).
    // Solution: Normalize each metric to 0-100% relative to the MAX in that set.

    // Find Max for each metric among these 5
    const maxXP = Math.max(...top5.map(m => m.xp_7d), 1);
    const maxMsgs = Math.max(...top5.map(m => m.msgs_7d), 1);
    const maxBoss = Math.max(...top5.map(m => m.boss_7d), 1);

    const data = [];
    top5.forEach(m => {
        data.push({ name: m.username, metric: 'XP (Relative)', value: (m.xp_7d / maxXP) * 100, raw: m.xp_7d, unit: 'XP' });
        data.push({ name: m.username, metric: 'Messages (Relative)', value: (m.msgs_7d / maxMsgs) * 100, raw: m.msgs_7d, unit: 'Msgs' });
        data.push({ name: m.username, metric: 'Boss Kills (Relative)', value: (m.boss_7d / maxBoss) * 100, raw: m.boss_7d, unit: 'Kills' });
    });

    try {
        const columnPlot = new G2Plot.Column(container, {
            data: data,
            isGroup: true,
            xField: 'metric',
            yField: 'value',
            seriesField: 'name',
            // Dodge means grouped bars
            groupField: 'name',
            columnStyle: {
                radius: [4, 4, 0, 0],
            },
            theme: 'dark',
            color: ['#00d4ff', '#ffb84d', '#33FF33', '#FF3333', '#A020F0'], // Distinct colors
            meta: {
                value: {
                    alias: 'Performance %',
                    min: 0,
                    max: 100,
                }
            },
            tooltip: {
                formatter: (datum) => {
                    return { name: datum.name, value: `${formatNumber(datum.raw)} ${datum.unit}` };
                }
            },
            legend: {
                position: 'top-left',
            },
            label: {
                // Optional: show raw value on top of bar? Might be too crowded.
                // Let's hide labels for cleaner look, tooltip is enough.
                content: ''
            }
        });

        columnPlot.render();
        charts.playerRadar = columnPlot;
    } catch (e) {
        console.warn("Failed to render Top 5 Comparison chart:", e);
        document.getElementById(container).innerHTML = `<div style="text-align:center;padding:20px;color:#ff6b6b">Error rendering chart</div>`;
    }
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

function renderTenureChart() {
    const ctx = document.getElementById('tenure-distribution-chart');
    if (!ctx) return;
    if (charts.tenure) charts.tenure.destroy();

    const members = dashboardData.allMembers || [];
    const buckets = {
        '0-30d': 0,
        '30-90d': 0,
        '90-180d': 0,
        '180d+': 0
    };

    members.forEach(m => {
        const d = m.days_in_clan || 0;
        if (d <= 30) buckets['0-30d']++;
        else if (d <= 90) buckets['30-90d']++;
        else if (d <= 180) buckets['90-180d']++;
        else buckets['180d+']++;
    });

    charts.tenure = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(buckets),
            datasets: [{
                data: Object.values(buckets),
                backgroundColor: ['#00d4ff', '#33FF33', '#FFD700', '#FF3333'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: '#ccc' } } }
        }
    });
}

function renderXPWeeklyCorrelation() {
    const container = document.getElementById('container-xp-scatter');
    if (!container) return;
    if (charts.xpMsgsCorr && charts.xpMsgsCorr.destroy) charts.xpMsgsCorr.destroy();

    const members = dashboardData.allMembers || [];
    const points = members
        .filter(m => m.xp_7d > 0 && m.msgs_7d > 0)
        .slice(0, 200)
        .map(m => ({ name: m.username, xp: m.xp_7d, msgs: m.msgs_7d }));

    if (points.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:1.5rem;color:#666;font-style:italic;">No XP/message correlation data available</div>';
        return;
    }

    const scatter = new G2Plot.Scatter('container-xp-scatter', {
        data: points,
        xField: 'msgs',
        yField: 'xp',
        size: 5,
        shape: 'circle',
        color: '#00d4ff',
        theme: 'dark',
        xAxis: { title: { text: 'Messages (7d)', style: { fill: '#888' } } },
        yAxis: { title: { text: 'XP (7d)', style: { fill: '#888' } }, label: { formatter: (v) => formatNumber(Number(v)) } },
        tooltip: {
            formatter: (d) => ({ name: d.name, value: `${d.msgs} msgs, ${formatNumber(d.xp)} XP` })
        }
    });

    scatter.render();
    charts.xpMsgsCorr = scatter;
}

function renderLeaderboardChart() {
    const ctx = document.getElementById('leaderboard-chart');
    if (!ctx) return;
    if (charts.leaderboard) charts.leaderboard.destroy();

    // Composite Score: Messages > XP > Boss KC
    // Previous: (Boss * Weight) + (Msgs * Weight)
    // New Request: "messages>xp gained>boss kc" implies a hierarchy or a specific weighting where Msgs is dominant, then XP, then Boss.
    // Let's interpret as Weighted Sum with heavier weights on Msgs.
    // Msgs (High Weight), XP (scaled down significantly as it's in millions), Boss (Mid Weight).
    // Let's try: Msgs * 10, Boss * 5, XP / 1000.

    // Normalize first to avoid XP dominating purely by magnitude (1M XP vs 1000 Msgs)
    // But "Messages > XP > Boss" could also mean sorting order: Sort by Msg, if tie Sort by XP...
    // "Composite Score" usually implies a formula.
    // Let's do a weighted formula where 1 Msg worth a lot.
    // 1 Msg = 10 points. 1 Boss Kill = 5 points. 10k XP = 1 point.

    const scores = dashboardData.allMembers.map(m => {
        const score = (m.msgs_7d * 20) + (m.xp_7d / 5000) + (m.boss_7d * 5);
        return { name: m.username, score: Math.round(score) };
    }).sort((a, b) => b.score - a.score).slice(0, CONFIG.LEADERBOARD_SIZE);

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
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: `Composite: (Msgs*20) + (XP/5k) + (Boss*5)`,
                    color: '#888',
                    font: { size: 10, style: 'italic' },
                    padding: { bottom: 10 }
                }
            }
        }
    });
}



function renderTime(id, isoDate) {
    const el = document.getElementById(id);
    if (el && isoDate) {
        const d = new Date(isoDate);
        el.innerText = d.toLocaleString('en-GB').replace(/\//g, '-');
    }
}

function renderAIInsights(members) {
    console.log("renderAIInsights called with", members ? members.length : 0, "members");
    renderTime('updated-time-ai', dashboardData.generated_at);

    const container = document.getElementById('ai-feed-container');
    if (!container) return;

    container.innerHTML = '';

    const findAssetForInsight = (insight) => {
        // Try to map to a member mentioned in the message/title
        const text = `${insight.title || ''} ${insight.message || ''}`.toLowerCase();
        const member = (members || []).find(m => text.includes((m.username || '').toLowerCase()));
        if (member) {
            if (member.favorite_boss_img && member.favorite_boss_img !== 'boss_pet_rock.png') return member.favorite_boss_img;
            if (member.rank_img) return member.rank_img;
        }

        // Try to match boss names in text
        const bossMap = {
            'hydra': 'boss_alchemical_hydra.png',
            'vorkath': 'boss_vorkath.png',
            'zulrah': 'boss_zulrah.png',
            'cox': 'boss_chambers_of_xeric.png', 'chamber': 'boss_chambers_of_xeric.png', 'olm': 'boss_great_olm.png',
            'tob': 'boss_theatre_of_blood.png', 'verzik': 'boss_verzik_vitur.png',
            'toa': 'boss_tombs_of_amascut.png', 'warden': 'boss_tumeken\'s_warden.png',
            'nex': 'boss_nex.png',
            'corp': 'boss_corporeal_beast.png',
            'jad': 'boss_tztok-jad.png', 'zuk': 'boss_tzkal-zuk.png', 'inferno': 'boss_tzkal-zuk.png',
            'nightmare': 'boss_the_nightmare.png',
            'bandos': 'boss_general_graardor.png', 'graardor': 'boss_general_graardor.png',
            'sara': 'boss_commander_zilyana.png', 'zilyana': 'boss_commander_zilyana.png',
            'arma': 'boss_kree\'arra.png', 'kree': 'boss_kree\'arra.png',
            'zammy': 'boss_k\'ril_tsutsaroth.png', 'kril': 'boss_k\'ril_tsutsaroth.png',
            'muspah': 'boss_phantom_muspah.png',
            'duke': 'boss_duke_sucellus.png',
            'vard': 'boss_vardorvis.png',
            'levi': 'boss_the_leviathan.png',
            'whisperer': 'boss_the_whisperer.png',
            'wildy': 'boss_wilderness.png',
            'slayer': 'skill_slayer.png',
            'max': 'rank_maxed.png', 'comp': 'rank_completionist.png'
        };

        // Check for boss matches
        for (const [key, img] of Object.entries(bossMap)) {
            if (text.includes(key)) return img;
        }

        // Generic themed assets pool (Expanded)
        const pool = [
            'boss_alchemical_hydra.png',
            'boss_thermonuclear_smoke_devil.png',
            'boss_tombs_of_amascut.png',
            'boss_nightmare.png',
            'boss_chambers_of_xeric.png',
            'boss_theatre_of_blood.png',
            'boss_vorkath.png',
            'boss_zulrah.png',
            'boss_corporeal_beast.png',
            'boss_nex.png',
            'boss_tztok-jad.png',
            'boss_general_graardor.png',
            'skill_slayer.png',
            'boss_pet_rock.png'
        ];
        return pool[Math.floor(Math.random() * pool.length)];
    };

    // AI INSIGHTS INTEGRATION
    if (dashboardData.ai && dashboardData.ai.insights) {
        container.className = 'vertical-feed'; // Switch to vertical layout
        dashboardData.ai.insights.forEach(insight => {
            const colorVar = insight.type === 'trend' ? 'var(--neon-gold)' : insight.type === 'analysis' ? 'var(--neon-blue)' : 'var(--neon-green)';
            const icon = insight.type === 'trend' ? 'fa-chart-line' : insight.type === 'analysis' ? 'fa-brain' : 'fa-heartbeat';
            const asset = findAssetForInsight(insight);
            container.innerHTML += `
            <div class="alert-card" style="border-left: 4px solid ${colorVar}; min-height:180px; background: radial-gradient(circle at center, rgba(30,30,40,0.8), rgba(0,0,0,0.9)); position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: center;">
                <div style="position:absolute; inset:0; background-image:url('assets/${asset}'); background-repeat:no-repeat; background-position:center; background-size:cover; opacity:0.4; mix-blend-mode: luminosity;"></div>
                <div style="position:absolute; inset:0; background: linear-gradient(90deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.4) 50%, rgba(0,0,0,0.8) 100%);"></div>
                
                <div class="alert-header" style="display:flex;align-items:center;gap:15px;margin-bottom:12px;color:${colorVar}; position:relative; z-index:2; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">
                    <i class="fas ${icon}" style="font-size: 1.4em;"></i>
                    <span style="font-family:'Cinzel'; font-size: 1.4em; font-weight: 700; letter-spacing: 1px;">${insight.title}</span>
                </div>
                <div class="alert-metric" style="color:#e0e0e0; font-size: 1.1em; line-height: 1.5; position:relative; z-index:2; text-shadow: 0 1px 3px rgba(0,0,0,1);">
                    ${insight.message}
                </div>
            </div>
            `;
        });
    } else {
        container.innerHTML = '<div class="glass-card" style="padding:20px;grid-column:1/-1;text-align:center;color:#4fec4f">AI Insights will be available after next data refresh.</div>';
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

