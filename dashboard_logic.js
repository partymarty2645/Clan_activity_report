const API_URL = 'http://localhost:5000/api'; // Fallback if needed, but we use clan_data.json primarily
let dashboardData = null;
let charts = {};

// --- CHART.JS DEFAULTS (NEON THEME) ---
Chart.defaults.color = '#e0e0e0';
Chart.defaults.borderColor = 'rgba(0, 212, 255, 0.1)';
Chart.defaults.font.family = "'Outfit', sans-serif";
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(10, 10, 10, 0.9)';
Chart.defaults.plugins.tooltip.titleColor = '#00d4ff';
Chart.defaults.plugins.tooltip.bodyColor = '#fff';
Chart.defaults.plugins.tooltip.borderColor = '#00d4ff';
Chart.defaults.plugins.tooltip.borderWidth = 1;

// --- DATA FETCHING ---
async function getDashboardData() {
    if (window.dashboardData) return window.dashboardData;
    if (dashboardData) return dashboardData;
    try {
        const response = await fetch('clan_data.json');
        if (!response.ok) throw new Error('Network response was not ok');
        dashboardData = await response.json();
        window.dashboardData = dashboardData; // Expose globally
        return dashboardData;
    } catch (error) {
        console.error("Failed to load clan_data.json:", error);
        return null;
    }
}

// --- NAVIGATION ---
function switchSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const section = document.getElementById(sectionId);
    if (section) section.classList.add('active');

    // Update Nav State
    document.querySelectorAll('.nav-item').forEach(n => {
        const text = n.textContent.trim().toLowerCase();
        if (sectionId === 'general' && text.includes('dashboard')) n.classList.add('active');
        else if (sectionId === 'roster' && text.includes('roster')) n.classList.add('active');
        else if (sectionId === 'bosses' && text.includes('boss')) n.classList.add('active');
        else if (sectionId === 'messages' && text.includes('message')) n.classList.add('active');
        else if (sectionId === 'xp-gains' && text.includes('xp')) n.classList.add('active');
        else if (sectionId === 'outliers' && text.includes('outlier')) n.classList.add('active');
        else if (sectionId === 'comparator' && text.includes('comparator')) n.classList.add('active');
    });

    // Trigger Data Load for Section
    if (sectionId === 'general') loadGeneralData();
    else if (sectionId === 'messages') loadMessagesData();
    else if (sectionId === 'xp-gains') loadXPGainsDataBubble();
    else if (sectionId === 'outliers') loadOutliersData();
    else if (sectionId === 'bosses') loadBossesData();
    else if (sectionId === 'roster') loadRosterData();
    else if (sectionId === 'comparator') loadComparatorData();

    // Trigger resize for charts
    setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
}

// --- GENERAL SECTION ---
async function loadGeneralData() {
    const data = await getDashboardData();
    if (!data) return;

    // FIX: Update Timestamps everywhere
    const now = new Date().toLocaleDateString() + ' ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    ['updated-time', 'updated-time-msg', 'updated-time-xp', 'updated-time-boss', 'updated-time-out'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = now;
    });

    // 1. Text Stats & Weekly Briefing (Oracle)
    const briefingEl = document.getElementById('weekly-briefing-text');
    if (briefingEl) {
        if (data.oracle && data.oracle.length) {
            const top = data.oracle[0];
            briefingEl.innerHTML = `Oracle Vision: <span style="color:var(--neon-purple)">${top.name}</span> is on track for <span style="color:var(--neon-green)">${top.milestone}</span>.`;
        } else {
            briefingEl.textContent = "Clan activity is stable. No major anomalies detected.";
        }
    }

    // 2. Alert Cards (Churn Risks)
    renderAlertCards(data.allMembers);

    // 3. Bingo Grid (Demo)
    renderBingoGrid();

    // 4. Stats Cards (Top Messenger, etc.)
    // FIX: Using direct ID targeting instead of wrapper lookup
    if (data.topMessenger) updateStatCard('top-messenger', data.topMessenger.name, data.topMessenger.messages, 'Best Yapper');
    if (data.topXPGainer) updateStatCard('top-xp', data.topXPGainer.name, formatNumber(data.topXPGainer.xp), 'XP Machine');
    if (data.risingStar) updateStatCard('rising-star', data.risingStar.name, `+${data.risingStar.msgs} msgs`, 'Rising Star');
    if (data.topBossKiller) updateStatCard('top-boss', data.topBossKiller.name, data.topBossKiller.kills, 'Boss Hunter');

    // 5. Charts
    try {
        renderActivityHealth(data);
        renderLeaderboard(data);
        renderRecentActivity(data);
        renderWatchlist(data);
        // NEW Charts (Previously Missing)
        renderTopXPContributors(data);
        renderPlayerRadar(data);
        renderActivityTrend(data);
    } catch (e) { console.error("Chart Render Error:", e); }

    // 6. Force Resize to prevent hidden charts
    setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
}

function renderAlertCards(members) {
    const container = document.getElementById('alert-cards-container');
    if (!container) return;
    // Logic: Total XP > 10m, XP 7d < 25k, Msgs 30d < 10
    const risks = members.filter(m => m.total_xp > 10000000 && m.xp_7d < 25000 && m.msgs_30d < 10)
        .sort((a, b) => b.total_xp - a.total_xp).slice(0, 3);

    if (risks.length === 0) {
        container.innerHTML = '<div class="glass-card" style="grid-column: 1/-1; padding: 20px; text-align: center; color: var(--neon-green);">No immediate churn risks detected.</div>';
    } else {
        container.innerHTML = risks.map(m => `
            <div class="glass-card alert-card">
                <div class="stat-label" style="color: var(--neon-red); letter-spacing: 2px;"><i class="fas fa-radiation"></i> CHURN RISK</div>
                <div class="stat-value" style="font-size: 20px; margin: 10px 0;">${m.username}</div>
                <div class="stat-description" style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span>XP (7d): ${formatNumber(m.xp_7d)}</span>
                    <span>Msgs (30d): ${m.msgs_30d}</span>
                </div>
            </div>
        `).join('');
    }
}

function renderBingoGrid() {
    const container = document.getElementById('bingo-grid');
    if (!container) return;
    const bingoTargets = [
        { name: 'Vorkath', progress: 100, complete: true },
        { name: 'Zulrah', progress: 45, complete: false },
        { name: 'Raids', progress: 12, complete: false },
        { name: 'Slayer', progress: 100, complete: true }
    ];
    container.innerHTML = bingoTargets.map(b => `
        <div class="glass-card bingo-card" style="${b.complete ? 'border: 1px solid var(--neon-green); box-shadow: inset 0 0 10px rgba(57, 255, 20, 0.3);' : ''}">
             <div class="bingo-progress" style="${b.complete ? 'color: var(--neon-green);' : ''}">
                ${b.complete ? '<i class="fas fa-check"></i>' : b.progress + '%'}
             </div>
             <div class="bingo-boss-name">${b.name}</div>
        </div>
    `).join('');
}

// FIX: Refactored to target specific element IDs defined in HTML
function updateStatCard(baseId, name, value, subtitle) {
    const nameEl = document.getElementById(baseId + '-name'); // e.g., top-messenger-name
    const valEl = document.getElementById(baseId + '-val');   // e.g., top-messenger-val

    if (nameEl) nameEl.textContent = name;
    if (valEl) valEl.textContent = value;
    // subtitle is unused in current HTML structure or static
}

function renderActivityHealth(data) {
    // FIX: Element ID is activity-health-chart in HTML
    const ctx = document.getElementById('activity-health-chart');
    if (!ctx) return;
    if (charts['health']) charts['health'].destroy();

    // Simple mock data for health if not fully aggregated in JSON
    charts['health'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Active', 'Quiet', 'Inactive'],
            datasets: [{
                data: [65, 25, 10], // Mock or derive from data.allMembers logic
                backgroundColor: ['#39ff14', '#ffd700', '#ff073a'],
                borderColor: '#000',
                borderWidth: 2
            }]
        },
        options: { cutout: '70%', plugins: { legend: { position: 'right' } } }
    });
}

function renderLeaderboard(data) {
    // Composite Score Top 5
    const ctx = document.getElementById('leaderboard-chart');
    if (!ctx) return;
    if (charts['leaderboard']) charts['leaderboard'].destroy();

    if (!data.allMembers) return;

    // FIX: Safe Sort with 0-check
    const top5 = [...data.allMembers]
        .sort((a, b) => ((b.xp_7d || 0) + (b.boss_7d || 0) * 1000) - ((a.xp_7d || 0) + (a.boss_7d || 0) * 1000))
        .slice(0, 5);

    charts['leaderboard'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top5.map(m => m.username),
            datasets: [{
                label: 'XP Gained (7d)',
                data: top5.map(m => m.xp_7d),
                backgroundColor: '#00d4ff',
                yAxisID: 'y'
            }, {
                label: 'Boss Kills (7d)',
                data: top5.map(m => m.boss_7d),
                backgroundColor: '#ff073a',
                yAxisID: 'y1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { position: 'left', display: false },
                y1: { position: 'right', display: false, grid: { drawOnChartArea: false } }
            }
        }
    });
}

function renderRecentActivity(data) {
    const tbody = document.getElementById('recent-activity-body');
    if (!tbody) return;
    // Just show members with highest recent activity
    const recent = [...data.allMembers].sort((a, b) => b.xp_7d - a.xp_7d).slice(0, 5);
    tbody.innerHTML = recent.map(m => `
        <tr>
            <td>${m.username}</td>
            <td><span class="role-badge ${getRoleBadge(m.role)}">${m.role}</span></td>
            <td style="color:#39ff14">+${formatNumber(m.xp_7d)} XP</td>
        </tr>
    `).join('');
}

function renderWatchlist(data) {
    const list = document.getElementById('inactive-watchlist');
    if (!list) return;
    // Filter for truly inactive (0 xp, 0 msg, 0 boss in 30d)
    const ghosts = data.allMembers.filter(m => m.xp_30d === 0 && m.msgs_30d === 0 && m.boss_30d === 0).slice(0, 5);
    if (ghosts.length === 0) {
        list.innerHTML = '<li style="color:#888;">No ghosts detected.</li>';
    } else {
        list.innerHTML = ghosts.map(m => `
            <li>
                <span class="bad-name">${m.username}</span>
                <span class="days-inactive">${m.days_in_clan}d in clan</span>
            </li>
        `).join('');
    }
}

// --- MESSAGES SECTION ---
async function loadMessagesData() {
    const data = await getDashboardData();
    const timeEl = document.getElementById('updated-time-msg');
    if (timeEl) timeEl.textContent = new Date().toLocaleDateString();

    // 1. Volume Chart
    const topMsgs = [...data.allMembers].sort((a, b) => b.msgs_30d - a.msgs_30d).slice(0, 5);
    const ctxVol = document.getElementById('message-volume-chart');
    if (ctxVol) {
        if (charts['msg-vol']) charts['msg-vol'].destroy();
        charts['msg-vol'] = new Chart(ctxVol, {
            type: 'bar',
            data: {
                labels: topMsgs.map(m => m.username),
                datasets: [{
                    label: 'Messages (30d)',
                    data: topMsgs.map(m => m.msgs_30d),
                    backgroundColor: '#00d4ff'
                }]
            },
            options: { indexAxis: 'y', plugins: { legend: { display: false } } }
        });
    }

    // 2. Role Distribution
    renderRoleDistribution(data);

    // 3. Activity Heatmap
    renderActivityHeatmap(data);

    // 4. Table
    const tbody = document.querySelector('#messages-table tbody');
    if (tbody) {
        tbody.innerHTML = [...data.allMembers].sort((a, b) => b.msgs_total - a.msgs_total).map(m => `
            <tr>
                <td>${m.username}</td>
                <td><span class="role-badge ${getRoleBadge(m.role)}">${m.role}</span></td>
                <td>${formatNumber(m.msgs_total)}</td>
                <td>${formatNumber(m.msgs_7d)}</td>
                <td>${formatNumber(m.msgs_30d)}</td>
            </tr>
        `).join('');
        setupTableSearch('search-messages', 'messages-table');
    }
}

function renderRoleDistribution(data) {
    const ctx = document.getElementById('role-distribution-chart');
    if (!ctx) return;
    if (charts['role-dist']) charts['role-dist'].destroy();

    // Calculate distribution
    const roleCounts = {};
    data.allMembers.forEach(m => {
        const r = m.role || 'Unknown';
        roleCounts[r] = (roleCounts[r] || 0) + 1;
    });

    const sortedRoles = Object.entries(roleCounts).sort((a, b) => b[1] - a[1]);

    charts['role-dist'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: sortedRoles.map(r => r[0]),
            datasets: [{
                data: sortedRoles.map(r => r[1]),
                backgroundColor: [
                    '#00d4ff', '#39ff14', '#ff073a', '#e0e0e0', '#ffd700',
                    '#bc13fe', '#ffb84d', '#ff69b4', '#00ffff'
                ],
                borderWidth: 0
            }]
        },
        options: {
            plugins: { legend: { position: 'right', labels: { boxWidth: 10, color: '#aaa', font: { size: 10 } } } }
        }
    });
}

function renderActivityHeatmap(data) {
    const container = document.getElementById('activity-heatmap');
    if (!container) return;

    // Data usually in data.activityTrends
    const trends = data.activityTrends || [];
    if (trends.length === 0) {
        container.innerHTML = '<div class="loading">No activity data available</div>';
        return;
    }

    // Grid: 7 days x 24 hours. 
    // We need to map [day, hour] keys to values.
    const map = {};
    let maxVal = 1;
    trends.forEach(t => {
        map[`${t.day}-${t.hour}`] = t.value;
        if (t.value > maxVal) maxVal = t.value;
    });

    // Generate Grid HTML
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    // CSS Grid: 30px label col, then 24 1fr cols.
    let html = '<div style="display:grid; grid-template-columns: 40px repeat(24, 1fr); gap: 2px; height: 100%; align-content: center;">';

    // Header (Hours)
    html += '<div style="font-size:8px; color:#444;">UTC</div>'; // Corner
    for (let h = 0; h < 24; h += 2) html += `<div style="grid-column: span 2; font-size:8px; text-align:center; color:#666;">${h}</div>`;

    // Rows
    for (let d = 0; d < 7; d++) {
        html += `<div style="font-size:10px; color:#888; align-self:center;">${days[d]}</div>`;
        for (let h = 0; h < 24; h++) {
            const val = map[`${d}-${h}`] || 0;
            const intensity = Math.min(1, val / (maxVal * 0.8)); // slightly boost visibility
            // Color: Neon Blue with opacity
            const color = `rgba(0, 212, 255, ${Math.max(0.1, intensity)})`;
            const tooltip = `${days[d]} ${h}:00 - ${val} msgs`;

            html += `<div style="
                background: ${color}; 
                height: 12px; 
                border-radius: 2px;
                " title="${tooltip}"></div>`;
        }
    }
    html += '</div>';

    container.innerHTML = html;
    container.style.height = 'auto';
    container.style.display = 'block'; // Ensure visibility
}

// --- XP GAINS SECTION ---
async function loadXPGainsDataBubble() {
    const data = await getDashboardData();
    const timeEl = document.getElementById('updated-time-xp');
    if (timeEl) timeEl.textContent = new Date().toLocaleDateString();

    // 1. XP 7d Chart
    const topXP = [...data.allMembers].sort((a, b) => b.xp_7d - a.xp_7d).slice(0, 10);
    const ctxXP = document.getElementById('xp-7d-chart');
    if (ctxXP) {
        if (charts['xp-7d']) charts['xp-7d'].destroy();
        charts['xp-7d'] = new Chart(ctxXP, {
            type: 'bar',
            data: {
                labels: topXP.map(m => m.username),
                datasets: [{
                    label: 'XP Gained (7d)',
                    data: topXP.map(m => m.xp_7d),
                    backgroundColor: '#39ff14'
                }]
            },
            options: { plugins: { legend: { display: false } } }
        });
    }

    // 2. Scatter (XP vs Boss) - Optional
    const ctxScatter = document.getElementById('xp-boss-chart');
    if (ctxScatter) {
        if (charts['xp-boss']) charts['xp-boss'].destroy();
        charts['xp-boss'] = new Chart(ctxScatter, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Player Performance',
                    data: data.allMembers.map(m => ({ x: m.boss_total || m.total_boss, y: m.xp_7d })),
                    backgroundColor: '#bc13fe'
                }]
            },
            options: {
                scales: {
                    x: { title: { display: true, text: 'Total Boss Kills' } },
                    y: { title: { display: true, text: 'XP Gained (7d)' } }
                }
            }
        });
    }

    // 3. XP vs Messages Scatter
    const ctxMsg = document.getElementById('xp-messages-scatter');
    if (ctxMsg) {
        if (charts['xp-msg']) charts['xp-msg'].destroy();
        charts['xp-msg'] = new Chart(ctxMsg, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'XP vs Messages',
                    data: data.allMembers.map(m => ({ x: m.msgs_total || 0, y: m.xp_7d })),
                    backgroundColor: '#ff69b4'
                }]
            },
            options: {
                scales: {
                    x: { title: { display: true, text: 'Total Messages' } },
                    y: { title: { display: true, text: 'XP Gained (7d)' } }
                }
            }
        });
    }

    // 4. Table
    const tbody = document.querySelector('#xp-table tbody');
    if (tbody) {
        tbody.innerHTML = [...data.allMembers].sort((a, b) => b.xp_7d - a.xp_7d).map(m => `
            <tr>
                <td>${m.username}</td>
                <td><span class="role-badge ${getRoleBadge(m.role)}">${m.role}</span></td>
                <td>${formatNumber(m.total_xp)}</td>
                <td style="color:var(--neon-green)">+${formatNumber(m.xp_7d)}</td>
                <td>+${formatNumber(m.xp_30d)}</td>
            </tr>
        `).join('');
        setupTableSearch('search-xp', 'xp-table');
    }
}

// --- BOSSES SECTION ---
async function loadBossesData() {
    const data = await getDashboardData();
    const timeEl = document.getElementById('updated-time-boss');
    if (timeEl) timeEl.textContent = new Date().toLocaleDateString();

    // Render Boss Cards if data.bossCards exists
    const cardContainer = document.getElementById('boss-cards');
    if (cardContainer) {
        cardContainer.innerHTML = '';
        const createCard = (title, bossData, icon) => {
            if (!bossData || !bossData.name) return '';
            return `
                <div class="glass-card stat-card">
                    <div class="stat-icon"><img src="assets/${icon}" style="width:32px; filter: drop-shadow(0 0 5px var(--neon-gold));"></div>
                    <div class="stat-info">
                        <div class="stat-value">${bossData.name}</div>
                        <div class="stat-sub">${title}</div>
                        <div class="stat-sub" style="color:var(--neon-blue)">${formatNumber(bossData.count || bossData.kills)}</div>
                    </div>
                </div>
             `;
        };
        // Use safest logic: data.topBossKiller is usually reliable. 
        cardContainer.innerHTML += createCard('Weekly Top Killer', data.topBossKiller, 'boss_vorkath.png');

        // Pivot: Show Total Clan Kills (7d) which is always robust
        const totalKills = data.allMembers.reduce((acc, m) => acc + (m.boss_7d || 0), 0);
        cardContainer.innerHTML += createCard('Total Kills (7d)', { name: 'Clan Total', count: totalKills }, 'boss_pet_rock.png');
    }

    // Table
    const tbody = document.querySelector('#bosses-table tbody');
    if (tbody) {
        tbody.innerHTML = [...data.allMembers].sort((a, b) => b.total_boss - a.total_boss).map((m, idx) => `
            <tr>
                <td>#${idx + 1}</td>
                <td>${m.username}</td>
                <td><span class="role-badge ${getRoleBadge(m.role)}">${m.role}</span></td>
                <td style="color:var(--neon-gold); font-weight:bold;">${formatNumber(m.total_boss)}</td>
                <td>${formatNumber(m.boss_7d)}</td>
                <td>${formatNumber(m.boss_30d)}</td>
            </tr>
        `).join('');
        setupTableSearch('search-bosses', 'bosses-table');
    }
}

// --- OUTLIERS SECTION ---
async function loadOutliersData() {
    const data = await getDashboardData();
    const timeEl = document.getElementById('updated-time-out');
    if (timeEl) timeEl.textContent = new Date().toLocaleDateString();

    // Define simple outlier logic: Top 5% XP or Msgs
    const outliers = [...data.allMembers].sort((a, b) => b.xp_7d - a.xp_7d).slice(0, 10); // Mock logic

    const tbody = document.querySelector('#outliers-table tbody');
    if (tbody) {
        tbody.innerHTML = outliers.map(m => `
            <tr>
                <td>${m.username}</td>
                <td><span class="role-badge ${getRoleBadge(m.role)}">${m.role}</span></td>
                <td>${formatNumber(m.msgs_7d)}</td>
                <td>${formatNumber(m.xp_7d)}</td>
                <td>${(m.msgs_total / (m.days_in_clan || 1)).toFixed(1)}</td>
                <td><span style="color:var(--neon-red)">Anomalous</span></td>
            </tr>
        `).join('');
        setupTableSearch('search-outliers', 'outliers-table');
    }
}

// --- ROSTER SECTION ---
async function loadRosterData() {
    const data = await getDashboardData();
    const tbody = document.getElementById('roster-body');

    if (tbody) {
        tbody.innerHTML = data.allMembers.map(m => `
            <tr>
                <td class="player-cell">
                    <!-- FIX: Prefer role-derived asset (e.g. rank_zamorakian.png) over server generic (rank_diamond.png) -->
                    <img src="${getRankImage(m.role)}" class="rank-icon-sm" onerror="this.src='assets/rank_recruit.png'">
                    ${m.username}
                </td>
                <td>${formatNumber(m.xp_7d)}</td>
                <td>${formatNumber(m.total_xp)}</td>
                <td>${formatNumber(m.boss_7d)}</td>
                <td>${formatNumber(m.total_boss)}</td>
                <td>${formatNumber(m.msgs_7d)}</td>
                <td>${formatNumber(m.msgs_total)}</td>
                <td>${(m.social_ratio !== undefined && m.social_ratio !== null) ? m.social_ratio.toFixed(2) : '-'}</td>
            </tr>
        `).join('');
        setupTableSearch('search-roster', 'roster-table');
    }
}

// --- COMPARATOR SECTION ---
async function loadComparatorData() {
    await getDashboardData();
    initComparator();
}

function initComparator() {
    const data = window.dashboardData;
    if (!data) return;

    const inputA = document.getElementById('comparator-search-a');
    const inputB = document.getElementById('comparator-search-b');

    // Simple Datalist setup
    let datalist = document.getElementById('player-datalist');
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = 'player-datalist';
        data.allMembers.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.username;
            datalist.appendChild(opt);
        });
        document.body.appendChild(datalist);
    }

    if (inputA) {
        inputA.setAttribute('list', 'player-datalist');
        inputA.onchange = updateComparator;
    }
    if (inputB) {
        inputB.setAttribute('list', 'player-datalist');
        inputB.onchange = updateComparator;
    }
}

function updateComparator() {
    const nameA = document.getElementById('comparator-search-a').value;
    const nameB = document.getElementById('comparator-search-b').value;
    const data = window.dashboardData;

    const playerA = data.allMembers.find(m => m.username === nameA);
    const playerB = data.allMembers.find(m => m.username === nameB);

    // Update Radar Chart if both exist
    if (playerA && playerB) {
        const ctx = document.getElementById('comparator-radar');
        if (charts['comparator']) charts['comparator'].destroy();

        charts['comparator'] = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['XP', 'Boss', 'Msgs', 'Activity', 'Loyalty'],
                datasets: [
                    {
                        label: playerA.username,
                        data: [playerA.xp_7d / 200000 * 100, playerA.boss_7d / 50 * 100, playerA.msgs_7d / 50 * 100, 80, 70],
                        borderColor: '#00d4ff',
                        backgroundColor: 'rgba(0, 212, 255, 0.2)'
                    },
                    {
                        label: playerB.username,
                        data: [playerB.xp_7d / 200000 * 100, playerB.boss_7d / 50 * 100, playerB.msgs_7d / 50 * 100, 60, 90],
                        borderColor: '#ffb84d',
                        backgroundColor: 'rgba(255, 184, 77, 0.2)'
                    }
                ]
            }
        });

        // Update Table (Tale of the Tape)
        const tbody = document.getElementById('comparator-body');
        if (tbody) {
            const metrics = [
                { label: 'Total XP', key: 'total_xp' },
                { label: 'Total Boss', key: 'total_boss' },
                { label: 'Messages', key: 'msgs_total' },
                { label: 'Days in Clan', key: 'days_in_clan' }
            ];

            tbody.innerHTML = metrics.map(m => {
                const v1 = playerA[m.key] || 0;
                const v2 = playerB[m.key] || 0;
                const diff = v1 - v2;
                const color = diff > 0 ? '#00d4ff' : (diff < 0 ? '#ffb84d' : '#888');
                return `
                    <tr>
                        <td>${m.label}</td>
                        <td style="color:#00d4ff">${formatNumber(v1)}</td>
                        <td style="color:#ffb84d">${formatNumber(v2)}</td>
                        <td style="color:${color}">${diff > 0 ? '+' : ''}${formatNumber(diff)}</td>
                    </tr>
                 `;
            }).join('');
        }
    }
}


// --- MISSING CHART IMPLEMENTATIONS ---

function renderTopXPContributors(data) {
    const ctx = document.getElementById('top-xp-contributors-chart');
    if (!ctx) return;
    if (charts['top-xp-contrib']) charts['top-xp-contrib'].destroy();

    const top10 = [...data.allMembers].sort((a, b) => b.xp_7d - a.xp_7d).slice(0, 10);

    charts['top-xp-contrib'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top10.map(m => m.username),
            datasets: [{
                label: '7d XP Contribution',
                data: top10.map(m => m.xp_7d),
                backgroundColor: '#00d4ff',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { display: false }, y: { ticks: { color: '#ccc', font: { size: 10 } } } }
        }
    });
}

function renderPlayerRadar(data) {
    const ctx = document.getElementById('player-radar-chart');
    if (!ctx) return;
    if (charts['player-radar']) charts['player-radar'].destroy();

    // Top 5 by composite activity
    const top5 = [...data.allMembers]
        .sort((a, b) => ((b.xp_7d || 0) + (b.boss_7d || 0) * 1000 + (b.msgs_7d || 0) * 100) - ((a.xp_7d || 0) + (a.boss_7d || 0) * 1000 + (a.msgs_7d || 0) * 100))
        .slice(0, 5);

    charts['player-radar'] = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['XP Gains', 'Boss Kills', 'Messages', 'Loyalty', 'Impact'],
            datasets: top5.map((m, i) => ({
                label: m.username,
                data: [
                    Math.min(100, (m.xp_7d / 1000000) * 100),
                    Math.min(100, (m.boss_7d / 50) * 100),
                    Math.min(100, (m.msgs_7d / 100) * 100),
                    Math.min(100, (m.days_in_clan / 365) * 100),
                    Math.min(100, (m.total_xp / 200000000) * 100)
                ],
                borderColor: ['#00d4ff', '#ff073a', '#39ff14', '#ffd700', '#bc13fe'][i] || '#fff',
                backgroundColor: 'rgba(0,0,0,0)', // Clean look
                borderWidth: 2
            }))
        },
        options: {
            elements: { line: { tension: 0.3 } },
            scales: { r: { angleLines: { color: '#333' }, grid: { color: '#333' }, pointLabels: { color: '#888' } } }
        }
    });
}

function renderActivityTrend(data) {
    const ctx = document.getElementById('activity-trend-chart');
    if (!ctx) return;
    if (charts['activity-trend']) charts['activity-trend'].destroy();

    // Mock trend if real historical data isn't in JSON yet
    const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const xpTrend = [12, 19, 15, 25, 32, 40, 35].map(v => v * 100000); // Mock
    const msgTrend = [50, 60, 45, 80, 120, 150, 90]; // Mock

    charts['activity-trend'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Total XP', data: xpTrend, borderColor: '#39ff14', yAxisID: 'y' },
                { label: 'Messages', data: msgTrend, borderColor: '#00d4ff', yAxisID: 'y1' }
            ]
        },
        options: {
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: { display: false },
                y1: { display: false, position: 'right', grid: { drawOnChartArea: false } }
            }
        }
    });
}

// --- HELPERS ---
function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toLocaleString();
}

function getRoleBadge(role) {
    if (!role) return 'member';
    return role.toLowerCase().replace(/ /g, '-');
}

function getRankImage(role) {
    if (!role) return 'assets/rank_recruit.png';
    // Normalize: "Zamorakian" -> "rank_zamorakian.png", "Deputy Owner" -> "rank_deputy_owner.png"
    const normalized = role.toLowerCase().replace(/ /g, '_').replace(/'/g, '');

    // We now have assets for almost all roles, even flavor ones.
    // If specific one fails, the <img> onerror logic in the HTML (renderRosterData) will catch it.
    return `assets/rank_${normalized}.png`;
}

function getBossImage(bossName) {
    if (!bossName) return 'assets/boss_pet_rock.png';
    // Normalize: "General Graardor" -> "boss_general_graardor.png"
    const normalized = bossName.toLowerCase().replace(/ /g, '_').replace(/'/g, '').replace(/\(/g, '').replace(/\)/g, '').replace(/\./g, '');
    return `assets/boss_${normalized}.png`;
}

function setupTableSearch(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;

    input.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });
}

// --- SORT TABLE ---
function sortTable(n) {
    const table = document.getElementById("roster-table");
    if (!table) return;
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.rows);
    const ascending = table.getAttribute('data-order') !== 'asc'; // Toggle
    table.setAttribute('data-order', ascending ? 'asc' : 'desc');

    rows.sort((a, b) => {
        const valA = getText(a.cells[n]);
        const valB = getText(b.cells[n]);
        const numA = parseNum(valA);
        const numB = parseNum(valB);

        if (!isNaN(numA) && !isNaN(numB)) return ascending ? numA - numB : numB - numA;
        return ascending ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });

    rows.forEach(row => tbody.appendChild(row));
}

const getText = (cell) => cell.textContent.trim();
const parseNum = (str) => {
    str = str.replace(/,/g, '').replace(/k/i, '000').replace(/m/i, '000000').replace(/\+/g, '');
    return parseFloat(str);
};

// --- OMNI SEARCH LOGIC ---
let omniOpen = false;
let omniIndex = [];
let omniSelection = 0;

function toggleOmni() {
    omniOpen = !omniOpen;
    const overlay = document.getElementById('omni-search-overlay');
    const input = document.getElementById('omni-input');
    if (overlay) overlay.style.display = omniOpen ? 'flex' : 'none';
    if (omniOpen && input) {
        input.focus();
        input.value = '';
        buildOmniIndex();
        renderOmniResults(omniIndex.slice(0, 10));
    }
}

function buildOmniIndex() {
    omniIndex = [
        { name: 'General Dashboard', type: 'Section', action: () => switchSection('general') },
        { name: 'Full Roster', type: 'Section', action: () => switchSection('roster') },
        { name: 'Boss Activity', type: 'Section', action: () => switchSection('bosses') },
        { name: 'Messages & Activity', type: 'Section', action: () => switchSection('messages') },
        { name: 'XP Gains', type: 'Section', action: () => switchSection('xp-gains') },
        { name: 'Comparators', type: 'Section', action: () => switchSection('comparator') },
    ];

    if (window.dashboardData && window.dashboardData.allMembers) {
        window.dashboardData.allMembers.forEach(m => {
            omniIndex.push({
                name: m.username,
                type: 'Player',
                action: () => {
                    switchSection('roster');
                    const search = document.getElementById('search-roster');
                    if (search) { search.value = m.username; search.dispatchEvent(new Event('input')); }
                    toggleOmni();
                }
            });
        });
    }
}

function renderOmniResults(items) {
    const container = document.getElementById('omni-results');
    if (!container) return;
    container.innerHTML = items.map((item, idx) => `
        <div class="omni-item ${idx === 0 ? 'selected' : ''}">
            <div class="omni-item-text">${item.name}</div>
            <div style="font-size:10px; color:#666;">${item.type}</div>
        </div>
    `).join('');
    omniSelection = 0;

    container.querySelectorAll('.omni-item').forEach((el, idx) => {
        el.onclick = () => {
            items[idx].action();
            toggleOmni();
        };
    });
}

// Global Event Listeners
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleOmni();
    }
    if (e.key === 'Escape' && omniOpen) toggleOmni();

    if (omniOpen) {
        const results = document.querySelectorAll('.omni-item');
        if (e.key === 'ArrowDown') {
            omniSelection = Math.min(omniSelection + 1, results.length - 1);
            updateSelection();
        } else if (e.key === 'ArrowUp') {
            omniSelection = Math.max(omniSelection - 1, 0);
            updateSelection();
        } else if (e.key === 'Enter') {
            if (results[omniSelection]) results[omniSelection].click();
        }
    }
});

function updateSelection() {
    document.querySelectorAll('.omni-item').forEach((el, idx) => {
        if (idx === omniSelection) {
            el.classList.add('selected');
            el.scrollIntoView({ block: 'nearest' });
        } else {
            el.classList.remove('selected');
        }
    });
}

// Omni Input Listener
const omniInput = document.getElementById('omni-input');
if (omniInput) {
    omniInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = omniIndex.filter(i => i.name.toLowerCase().includes(term));
        renderOmniResults(filtered.slice(0, 10));
    });
}

// --- INIT ---
window.addEventListener('load', () => {
    switchSection('general');
});
