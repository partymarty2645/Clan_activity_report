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
    LEADERBOARD_SIZE: 25,
    TOP_BOSS_CARDS: 6
};

// Global HTML Decorators (used by multiple render functions)
const SHADOW_DECORATORS = `
    <div class="necrotic-border"></div>
    <div class="scanlines"></div>
    <div class="corner-accent top-left"></div>
    <div class="corner-accent top-right"></div>
    <div class="corner-accent bottom-left"></div>
    <div class="corner-accent bottom-right"></div>
    <div class="void-particles">
        <div class="void-particle"></div><div class="void-particle"></div><div class="void-particle"></div>
        <div class="void-particle"></div><div class="void-particle"></div>
    </div>`;

// Normalize asset base so GitHub Pages (served from /Clan_activity_report/) loads images correctly
const ASSET_BASE = (() => {
    try {
        const href = window.location.href;
        if (href.includes('/Clan_activity_report/')) return '/Clan_activity_report/assets/';
    } catch (_) {}
    return 'assets/';
})();

const normalizeAssetPath = (src) => {
    if (!src) return src;
    // Rewrite any leading assets/ reference (assets/, ../assets/, or /assets/) to the correct base
    return src.replace(/^\/?(?:\.\.\/)?assets\//, ASSET_BASE);
};

const normalizeAssetTags = (root = document) => {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll('img').forEach((img) => {
        const current = img.getAttribute('src');
        const fixed = normalizeAssetPath(current);
        if (fixed && fixed !== current) img.setAttribute('src', fixed);
    });
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

        // Normalize critical collections to avoid null crashes
        if (!Array.isArray(dashboardData.allMembers)) dashboardData.allMembers = [];
        if (!Array.isArray(dashboardData.history)) dashboardData.history = [];
        if (!Array.isArray(dashboardData.activity_heatmap)) dashboardData.activity_heatmap = [];
        if (!Array.isArray(dashboardData.topXPYear)) dashboardData.topXPYear = [];

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

        // CRITICAL: Initialize BOSS_THEMES BEFORE calling any render functions that use getBossTheme()
        BOSS_THEMES = getBossThemesFromCSS();
        console.log("BOSS_THEMES initialized from CSS variables");

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

        // Ensure any relative asset paths are normalized for the current host (e.g., GitHub Pages)
        normalizeAssetTags();

    } catch (criticalError) {
        console.error("CRITICAL INIT ERROR:", criticalError);
        const headerInfo = document.querySelector('.header-info');
        // Ensure headerInfo exists, if not try updated-time id
        const el = headerInfo || document.getElementById('updated-time');
        if (el) el.innerHTML = `<span style="color:red; font-size: 0.8em;">INIT ERROR: ${criticalError.message}</span>`;
    }
});

// ========== HELPER FUNCTIONS (MOVED TO TOP FOR HOISTING) ==========

function renderTime(id, isoDate) {
    const el = document.getElementById(id);
    if (el && isoDate) {
        const d = new Date(isoDate);
        el.innerText = d.toLocaleString('en-GB').replace(/\//g, '-');
    }
}


const BOSS_ASSET_MAP = {
    // === 1. RAIDS & MEGA BOSSES ===
    'cox': 'boss_chambers_of_xeric.png',
    'chambers': 'boss_chambers_of_xeric.png',
    'olm': 'boss_great_olm.png',
    'muttadile': 'boss_muttadile.png',
    'tekton': 'boss_tekton.png',
    'vasa': 'boss_vasa_nistirio.png',
    'vespula': 'boss_vespula.png',
    'ice demon': 'boss_ice_demon.png',

    // ToB
    'tob': 'boss_theatre_of_blood.png',
    'theatre': 'boss_theatre_of_blood.png',
    'verzik': 'boss_verzik_vitur.png',
    'bloat': 'boss_pestilent_bloat.png',
    'maiden': 'boss_the_maiden_of_sugadinti.png',
    'sote': 'boss_sotetseg.png',
    'sotetseg': 'boss_sotetseg.png',
    'xarpus': 'boss_xarpus.png',

    // ToA
    'toa': 'boss_tombs_of_amascut.png',
    'tombs': 'boss_tombs_of_amascut.png',
    'warden': 'boss_tumeken\'s_warden.png',
    'tumeken': 'boss_tumeken\'s_warden.png',
    'elidinis': 'boss_elidinis\'_warden.png',
    'akkha': 'boss_akkha.png',
    'baba': 'boss_ba-ba.png',
    'kephri': 'boss_kephri.png',
    'zebak': 'boss_zebak.png',

    // Mega
    'nex': 'boss_nex.png',
    'corp': 'boss_corporeal_beast.png',
    'nightmare': 'boss_the_nightmare.png',
    'phosani': 'boss_phosanis_nightmare.png',

    // === 2. DESERT TREASURE 2 (DT2) ===
    'whisperer': 'boss_the_whisperer.png',
    'vardorvis': 'boss_vardorvis.png',
    'leviathan': 'boss_the_leviathan.png',
    'duke': 'boss_duke_sucellus.png',
    'sucellus': 'boss_duke_sucellus.png',

    // === 3. GOD WARS DUNGEON (GWD) ===
    'zilyana': 'boss_commander_zilyana.png',
    'sara': 'boss_commander_zilyana.png',
    'graardor': 'boss_general_graardor.png',
    'bandos': 'boss_general_graardor.png',
    'kril': 'boss_kril_tsutsaroth.png',
    'zammy': 'boss_kril_tsutsaroth.png',
    'kree': 'boss_kree_arra.png',
    'arma': 'boss_kree_arra.png',

    // === 4. SLAYER BOSSES ===
    'hydra': 'boss_alchemical_hydra.png',
    'araxxor': 'boss_araxxor.png',
    'sire': 'boss_abyssal_sire.png',
    'cerberus': 'boss_cerberus.png',
    'cerb': 'boss_cerberus.png',
    'kraken': 'boss_kraken.png',
    'thermy': 'boss_thermonuclear_smoke_devil.png',
    'smoke devil': 'boss_thermonuclear_smoke_devil.png',
    'ggs': 'boss_dusk.png',
    'grotesque': 'boss_dusk.png',
    'dusk': 'boss_dusk.png',
    // 'dawn': 'boss_grotesque_guardians.png',

    // === 5. WILDERNESS ===
    'artio': 'boss_artio.png',
    'callisto': 'boss_callisto.png',
    'calvarion': 'boss_calvarion.png',
    'vetion': 'boss_vet\'ion.png',
    'spindel': 'boss_spindel.png',
    'venenatis': 'boss_venenatis.png',
    'chaos ele': 'boss_chaos_elemental.png',
    'fanatic': 'boss_chaos_fanatic.png',
    'archaeologist': 'boss_crazy_archaeologist.png',
    'scorpia': 'boss_scorpia.png',

    // === 6. SKILLING / MINIGAMES / OTHER ===
    'zalcano': 'boss_zalcano.png',
    'tempoross': 'boss_tempoross.png',
    'todt': null,
    'wintertodt': null,
    'jad': 'boss_tztok-jad.png',
    'zuk': 'boss_tzkal-zuk.png',
    'inferno': 'boss_tzkal-zuk.png',
    'barrows': 'boss_dharok_the_wretched.png',
    'gauntlet': 'boss_the_corrupted_gauntlet.png',
    'hunllef': 'boss_corrupted_hunllef.png',
    'mimic': 'boss_the_mimic.png',
    'hespori': 'boss_hespori.png',
    'skotizo': 'boss_skotizo.png',
    'obor': 'boss_obor.png',
    'bryophyta': 'boss_bryophyta.png',
    'deranged': 'boss_deranged_archaeologist.png',

    // === 7. NEW / VARLAMORE ===
    'scurrius': 'boss_scurrius.png',
    'huey': 'boss_the_hueycoatl.png',
    'hueycoatl': 'boss_the_hueycoatl.png',
    'sol': 'boss_sol_heredit.png',
    'colosseum': 'boss_sol_heredit.png',

    // === 8. MOONS OF PERIL ===
    'blood moon': 'boss_blood_moon.png',
    'blue moon': 'boss_blue_moon.png',
    'eclipse': 'boss_eclipse_moon.png',
    'amoxliatl': 'boss_amoxliatl.png',

    // === 9. SOLO / WANDERING ===
    'zulrah': 'boss_zulrah.png',
    'vorkath': 'boss_vorkath.png',
    'muspah': 'boss_phantom_muspah.png',
    'mole': 'boss_giant_mole.png',
    'kq': 'boss_kalphite_queen.png',
    'kalphite': 'boss_kalphite_queen.png',
    'sarachnis': 'boss_sarachnis.png',
    'kbd': 'boss_king_black_dragon.png',
    'black dragon': 'boss_king_black_dragon.png',
};

function resolveBossImage(bossName, providedImg) {
    if (!bossName) return 'boss_pet_rock.png';
    const lower = bossName.toLowerCase();

    // 1. Check EXACT or KEYWORD match in Dictionary
    for (const [key, filename] of Object.entries(BOSS_ASSET_MAP)) {
        if (lower.includes(key)) {
            // Note: If mapped to null (e.g. wintertodt), we return pet rock
            return filename || 'boss_pet_rock.png';
        }
    }

    // 2. Fallback: If provided image is valid, use it
    if (providedImg && !providedImg.includes('pet_rock')) return providedImg;

    return 'boss_pet_rock.png';
}

function formatInsightMessage(msg) {
    if (!msg) return '';
    // Highlight large numbers
    let formatted = msg.replace(/(\d+(?:,\d+)?(?:\.\d+)?[KMB]?)/g, '<span style="color:var(--neon-gold); font-weight:bold;">$1</span>');

    // Highlight quoted names/text - REMOVED to prevent HTML attribute collision
    // formatted = formatted.replace(/'([^']+)'/g, '<span style="color:#fff; font-weight:bold;">$1</span>');
    // formatted = formatted.replace(/"([^"]+)"/g, '<span style="color:#fff; font-weight:bold;">$1</span>');

    // Highlight keywords
    const keywords = ['PEAK', 'RECORD', 'HIGH', 'LOW', 'ACTIVE', 'DORMANT', 'CLAN'];
    keywords.forEach(k => {
        formatted = formatted.replace(new RegExp(`\\b${k}\\b`, 'g'), `<span style="color:var(--neon-blue); font-weight:bold;">${k}</span>`);
    });

    return formatted;
}

// Helper to determine biome class for CSS texturing
function getBossBiome(bossName) {
    const lower = bossName.toLowerCase();
    if (lower.includes('blood') || lower.includes('theatre') || lower.includes('verzik') || lower.includes('vardorvis') || lower.includes('sote') || lower.includes('maiden') || lower.includes('bloat') || lower.includes('xarpus')) return 'biome-blood';
    if (lower.includes('ice') || lower.includes('nex') || lower.includes('wintertodt') || lower.includes('vorkath') || lower.includes('muspah') || lower.includes('blue moon') || lower.includes('phantom')) return 'biome-ice';
    if (lower.includes('desert') || lower.includes('tombs') || lower.includes('amascut') || lower.includes('kq') || lower.includes('kalphite') || lower.includes('warden') || lower.includes('kephri') || lower.includes('zebak') || lower.includes('akka') || lower.includes('baba')) return 'biome-desert';
    if (lower.includes('fire') || lower.includes('inferno') || lower.includes('zuk') || lower.includes('jad')) return 'biome-fire';
    if (lower.includes('toxic') || lower.includes('zulrah') || lower.includes('hydra') || lower.includes('cox') || lower.includes('xeric') || lower.includes('olm') || lower.includes('muttadile') || lower.includes('venenatis') || lower.includes('spindel')) return 'biome-toxic';
    if (lower.includes('whisperer') || lower.includes('leviathan') || lower.includes('void') || lower.includes('duke') || lower.includes('sucellus') || lower.includes('nightmare')) return 'biome-cosmic';
    if (lower.includes('undead') || lower.includes('vet') || lower.includes('barrows') || lower.includes('callisto') || lower.includes('artio') || lower.includes('scorpia') || lower.includes('chaos')) return 'biome-undead';
    return 'biome-generic';
}

function renderBossesSection(members) {
    console.log("renderBossesSection called with", members ? members.length : 0, "members");
    if (dashboardData && dashboardData.generated_at) renderTime('updated-time-boss', dashboardData.generated_at);

    const container = document.getElementById('bosses-grid');
    if (!container) return;

    container.innerHTML = '';
    container.style.display = 'grid';
    container.style.gridTemplateColumns = 'repeat(3, minmax(0, 1fr))';
    container.style.gap = '20px';

    const bossesSorted = [...members].sort((a, b) => (b.boss_7d || 0) - (a.boss_7d || 0)).filter(m => m.boss_7d > 0).slice(0, 6);

    if (bossesSorted.length === 0) {
        container.innerHTML = '<div class="glass-card" style="padding:20px;grid-column:1/-1;text-align:center;color:#888">No boss data available</div>';
    }

    bossesSorted.forEach((m, idx) => {
        const bossName = (m.favorite_boss_all_time || m.favorite_boss || 'Top Killer').toString();
        // Use helper to resolve image, fixing specific mismatches like Whisperer/Vardorvis
        const bossImg = resolveBossImage(bossName, m.favorite_boss_img);
        const theme = getBossTheme(bossName);
        const color = theme.color || '#bc13fe';
        const glow = theme.glow || 'rgba(188, 19, 254, 0.4)';
        const biomeClass = getBossBiome(bossName);

        container.innerHTML += `
        <div class="unified-card ${biomeClass}" style="--theme-color: ${color}; --theme-glow: ${glow};">
            ${SHADOW_DECORATORS}
            <div class="card-header" style="padding: 10px 12px 0 12px;">
                <div class="card-header-inner" style="display:flex; align-items:center; width:100%; gap:10px;">
                    <img src="assets/${m.rank_img || 'rank_minion.png'}" alt="rank" style="width:48px; height:48px; object-fit:contain;" onerror="this.src='assets/rank_minion.png'" />
                    <div style="flex:1; text-align:center;">
                        <div class="primary-text" style="font-size:1.3em; color:#fff;">${m.username}</div>
                        <div class="card-type-label" style="margin-top:2px;">${bossName.toUpperCase()}</div>
                    </div>
                    <div class="rank-badge"><span>#${idx + 1}</span></div>
                </div>
            </div>
            <div class="card-visual" style="text-align:center; padding-top:6px;">
                <img src="assets/${bossImg}" alt="${bossName}" class="boss-img" />
            </div>
            <div class="card-info" style="text-align:center; padding-bottom:10px;">
                <div class="primary-stat-val" style="font-size:2.2em;">${formatNumber(m.boss_7d)}</div>
                <div class="secondary-text">Kills (7d)</div>
            </div>
            <div class="details-overlay">
                <div class="detail-row"><span>Total Kills</span><span>${formatNumber(m.total_boss || 0)}</span></div>
                <div class="detail-row"><span>30d Kills</span><span>${formatNumber(m.boss_30d || 0)}</span></div>
            </div>
        </div>`;
    });

    // Also keep table in sync for data transparency
    const tbody = document.querySelector('#bosses-table tbody');
    if (tbody) {
        const sorted = [...members].sort((a, b) => b.boss_7d - a.boss_7d).slice(0, 50);
        tbody.innerHTML = sorted.map((m, i) => {
            const bossName = (m.favorite_boss_all_time || m.favorite_boss || 'Top Killer').toString();
            const bossKey = bossName.toLowerCase().replace(/[^a-z0-9]/g, ''); // Normalize for CSS class
            const theme = getBossTheme(bossName);
            // We use the CSS class for the theme if available, otherwise fallback to inline styles
            const themeClass = `theme-row-${bossKey}`;

            // Fallback inline style if CSS class doesn't exist (though harmless to add class)
            // But we keep the inline border for guaranteed color match if CSS is missing
            const style = `border-left: 3px solid ${theme.color};`;

            return `
            <tr class="${themeClass}" style="${style}">
                <td style="color:${i < 3 ? 'var(--neon-gold)' : '#fff'}">#${i + 1}</td>
                <td>${m.username}</td>
                <td>${m.role}</td>
                <td style="color:rgba(255,255,255,0.7)">${formatNumber(m.total_boss)}</td>
                <td style="color:var(--neon-red);font-weight:bold">+${formatNumber(m.boss_7d)}</td>
                <td style="color:rgba(255,255,255,0.7)">+${formatNumber(m.boss_30d || 0)}</td>
            </tr>`;
        }).join('');
    }
}

function renderOutliersSection(members) {
    console.log("renderOutliersSection called with", members ? members.length : 0, "members");
    renderTime('updated-time-purging', dashboardData.generated_at);

    const tbody = document.querySelector('#purging-table tbody');
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

function getPurgeCandidates(members) {
    const candidates = [];

    members.forEach(m => {
        let status = null;
        let type = "";

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

function renderActivityHeatmap() {
    const container = 'activity-heatmap';
    if (!document.getElementById(container)) return;
    if (charts.heatmap) charts.heatmap.destroy();

    const data = dashboardData.activity_heatmap;
    if (!data || !Array.isArray(data) || data.length === 0) {
        document.getElementById(container).innerHTML = '<div class="no-data">No heatmap data</div>';
        return;
    }

    const plotData = data.map((val, idx) => ({
        hour: `${String(idx).padStart(2, '0')}:00`,
        value: Number(val) || 0
    }));

    try {
        const column = new G2Plot.Column(container, {
            data: plotData,
            xField: 'hour',
            yField: 'value',
            color: 'l(270) 0:#00d4ff 1:#0055ff',
            columnStyle: { radius: [4, 4, 0, 0] },
            autoFit: true,
            theme: {
                styleSheet: {
                    backgroundColor: 'transparent',
                    plotBackgroundColor: 'transparent'
                }
            },
            meta: { value: { alias: 'Messages' } },
            xAxis: { label: { autoRotate: false, style: { fill: '#666', fontSize: 10 } }, grid: null },
            yAxis: { grid: { line: { style: { stroke: '#333', lineDash: [2, 2] } } } },
            legend: {
                position: 'top-left',
                itemName: { style: { fill: '#ccc', fontSize: 12 } }
            },
            tooltip: { formatter: (datum) => ({ name: 'Activity', value: datum.value + ' msgs' }) }
        });
        column.render();
        charts.heatmap = column;
    } catch (e) {
        console.warn("Failed to render Heatmap:", e);
    }
}

function renderActivityTrend() {
    const container = 'container-activity-trend';
    const el = document.getElementById(container);
    if (!el) return;

    el.innerHTML = '';

    const hist = dashboardData.history;
    if (!hist || !Array.isArray(hist) || hist.length === 0) {
        el.innerHTML = '<div style="text-align:center;padding:40px;color:#666;font-style:italic;">Activity history not yet available. Check back after more data is collected.</div>';
        return;
    }

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
            areaStyle: { fill: 'l(270) 0:#00d4ff 1:rgba(0, 212, 255, 0.1)' },
            theme: 'dark',
            xAxis: { range: [0, 1], label: { style: { fill: '#666' }, autoRotate: true } },
            yAxis: { grid: { line: { style: { stroke: '#333' } } }, label: { formatter: (v) => formatNumber(Number(v)) } },
            legend: false,
            tooltip: { showMarkers: true },
            smooth: true,
            animation: { appear: { animation: 'wave-in', duration: 1000 } }
        });
        area.render();
        charts.activityTrend = area;
    } catch (e) {
        console.warn("Failed to render Activity Trend:", e);
    }
}

function renderTenureChart() {
    const ctx = document.getElementById('tenure-distribution-chart');
    if (!ctx) return;
    if (charts.tenure) charts.tenure.destroy();

    const members = dashboardData.allMembers || [];
    if (members.length === 0) {
        ctx.style.display = 'none';
        return;
    }

    const buckets = { '0-30d': 0, '30-90d': 0, '90-180d': 0, '180d+': 0 };
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
        tooltip: { formatter: (d) => ({ name: d.name, value: `${d.msgs} msgs, ${formatNumber(d.xp)} XP` }) }
    });

    scatter.render();
    charts.xpMsgsCorr = scatter;
}

function renderLeaderboardChart() {
    const ctx = document.getElementById('leaderboard-chart');
    if (!ctx) return;
    if (charts.leaderboard) charts.leaderboard.destroy();

    const scores = dashboardData.allMembers.map(m => {
        const score = (m.msgs_7d * 100) + (m.xp_7d / 100000) + (m.boss_7d);
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
                    '#FFD700', '#C0C0C0', '#CD7F32',
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
                    text: `Composite: (Msgs*100) + (XP/100k) + (Boss*1)`,
                    color: '#888',
                    font: { size: 10, style: 'italic' },
                    padding: { bottom: 10 }
                }
            }
        }
    });
}

function renderAIHealthGauge() {
    const container = document.getElementById('ai-health-container');
    if (!container) return;

    // Improved container styling for Chart.js visibility
    container.style.display = 'block';
    container.style.width = '100%';
    container.style.padding = '20px';

    container.innerHTML = `
        <div style="width: 100%; max-width: 400px; margin: 0 auto; text-align:center;">
             <h3 style="color:var(--neon-blue); margin-bottom:15px; font-family:'Outfit',sans-serif; text-transform:uppercase; letter-spacing:1px;">System Health</h3>
             <div style="position:relative; height:220px; width:100%;">
                <canvas id="ai-health-canvas"></canvas>
             </div>
        </div>
    `;

    const ctx = document.getElementById('ai-health-canvas');
    if (!ctx) return;

    const members = dashboardData.allMembers;
    const high = members.filter(m => m.xp_7d > 1000000).length;
    const med = members.filter(m => m.xp_7d > 100000 && m.xp_7d <= 1000000).length;
    const low = members.filter(m => m.xp_7d > 0 && m.xp_7d <= 100000).length;
    const inactive = members.filter(m => m.xp_7d === 0).length;

    new Chart(ctx, {
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
                legend: { position: 'right', labels: { color: '#ccc', font: { family: "'Outfit', sans-serif" } } }
            }
        }
    });
}

function renderAIInsights(members) {
    console.log("renderAIInsights called with", members ? members.length : 0, "members");
    renderTime('updated-time-ai', dashboardData.generated_at);

    try { renderAIHealthGauge(); } catch (e) { console.warn("AI Gauge Error:", e); }

    const container = document.getElementById('ai-feed-container');
    if (!container) return;

    container.innerHTML = '';

    // Use ai_data.js format if available (richer structure with title + message)
    const aiData = window.aiData || dashboardData.ai || {};
    const insights = aiData.insights || [];

    // If empty, show fallback
    if (!insights || insights.length === 0) {
        container.innerHTML = '<div class="glass-card" style="padding:20px;grid-column:1/-1;text-align:center;color:#4fec4f">AI Insights will be available after next data refresh.</div>';
        return;
    }

    const extractPlayerName = (insight, allMembers) => {
        const msg = insight.message || insight.title || '';
        const lines = msg.split(':');
        if (lines.length > 0) {
            const firstWord = lines[0].trim().split(/\s+/)[0];
            if (firstWord && allMembers) {
                const found = allMembers.find(m =>
                    m.username.toLowerCase() === firstWord.toLowerCase() ||
                    m.username.toLowerCase().replace(/\s/g, '').includes(firstWord.toLowerCase().replace(/\s/g, ''))
                );
                if (found) return found;
            }
        }
        return null;
    };

    const findAssetForInsight = (insight, playerObj) => {
        const text = `${insight.message || insight.title || ''}`.toLowerCase();

        if (playerObj) {
            if (playerObj.favorite_boss_img && playerObj.favorite_boss_img !== 'boss_pet_rock.png') return playerObj.favorite_boss_img;
            if (playerObj.favorite_boss_all_time_img && playerObj.favorite_boss_all_time_img !== 'boss_pet_rock.png') return playerObj.favorite_boss_all_time_img;
        }

        const bossMap = {
            'hydra': 'boss_alchemical_hydra.png', 'vorkath': 'boss_vorkath.png', 'zulrah': 'boss_zulrah.png',
            'cox': 'boss_chambers_of_xeric.png', 'chamber': 'boss_chambers_of_xeric.png', 'olm': 'boss_great_olm.png',
            'tob': 'boss_theatre_of_blood.png', 'verzik': 'boss_verzik_vitur.png',
            'toa': 'boss_tombs_of_amascut.png', 'warden': 'boss_tombs_of_amascut.png',
            'nex': 'boss_nex.png', 'corp': 'boss_corporeal_beast.png',
            'jad': 'boss_tztok-jad.png', 'zuk': 'boss_tzkal-zuk.png', 'inferno': 'boss_tzkal-zuk.png',
            'nightmare': 'boss_the_nightmare.png', 'bandos': 'boss_general_graardor.png',
            'sara': 'boss_commander_zilyana.png', 'arma': 'boss_kreearra.png',
            'zammy': 'boss_kril_tsutsaroth.png', 'muspah': 'boss_phantom_muspah.png',
            'duke': 'boss_duke_sucellus.png', 'vard': 'boss_vardorvis.png', 'chat': 'boss_phoenix.png',
            'grind': 'boss_tzkal-zuk.png'
        };

        for (const [key, img] of Object.entries(bossMap)) {
            if (text.includes(key)) return img;
        }

        const pool = [
            'boss_alchemical_hydra.png', 'boss_thermonuclear_smoke_devil.png', 'boss_tombs_of_amascut.png',
            'boss_the_nightmare.png', 'boss_chambers_of_xeric.png', 'boss_theatre_of_blood.png',
            'boss_vorkath.png', 'boss_zulrah.png', 'boss_corporeal_beast.png', 'boss_nex.png',
            'boss_tztok-jad.png', 'boss_general_graardor.png', 'boss_phoenix.png'
        ];
        return pool[Math.floor(Math.random() * pool.length)];
    };

    const getAITheme = (insightType, assetName, bossNameExplicit) => {
        const hexToRgb = (hex) => {
            if (!hex) return null;
            const cleaned = hex.replace('#', '').trim();
            if (![3, 6].includes(cleaned.length)) return null;
            const full = cleaned.length === 3 ? cleaned.split('').map((c) => c + c).join('') : cleaned;
            const intVal = parseInt(full, 16);
            const r = (intVal >> 16) & 255;
            const g = (intVal >> 8) & 255;
            const b = intVal & 255;
            return `${r}, ${g}, ${b}`;
        };

        const bossNameFromAsset = (name) => {
            if (!name) return null;
            const file = name.split('/').pop() || name;
            const base = (file.split('.')[0] || '').replace(/^boss_/, '').replace(/^rank_/, '');
            const slug = base.replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
            if (!slug) return null;
            return slug.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        };

        const bossName = bossNameExplicit || bossNameFromAsset(assetName);
        const bossKey = bossName && Object.keys(BOSS_THEMES || {}).find(k => k.toLowerCase() === bossName.toLowerCase());
        const bossTheme = bossKey ? BOSS_THEMES[bossKey] : null;

        const typeColorMap = {
            'milestone': { color: 'var(--neon-gold)', rgb: '255, 215, 0', glow: 'rgba(255, 215, 0, 0.35)', icon: 'fa-trophy' },
            'roast': { color: 'var(--neon-red)', rgb: '255, 51, 51', glow: 'rgba(255, 51, 51, 0.35)', icon: 'fa-fire' },
            'trend-positive': { color: 'var(--neon-green)', rgb: '51, 255, 51', glow: 'rgba(51, 255, 51, 0.35)', icon: 'fa-arrow-up' },
            'trend-negative': { color: 'var(--boss-orange)', rgb: '255, 170, 0', glow: 'rgba(255, 170, 0, 0.35)', icon: 'fa-arrow-down' },
            'leadership': { color: 'var(--neon-blue)', rgb: '0, 212, 255', glow: 'rgba(0, 212, 255, 0.35)', icon: 'fa-crown' },
            'anomaly': { color: 'var(--neon-purple)', rgb: '188, 19, 254', glow: 'rgba(188, 19, 254, 0.35)', icon: 'fa-exclamation-circle' },
            'general': { color: '#888888', rgb: '136, 136, 136', glow: 'rgba(136, 136, 136, 0.35)', icon: 'fa-star' }
        };

        const baseTheme = typeColorMap[insightType] || typeColorMap.general;
        if (!bossTheme) return baseTheme;

        const rgb = hexToRgb(bossTheme.color) || baseTheme.rgb;
        return { ...baseTheme, color: bossTheme.color, rgb: rgb || baseTheme.rgb, glow: bossTheme.glow || baseTheme.glow };
    };

    // Render the insights in a rich 3-column grid
    container.style.display = 'grid';
    container.style.gridTemplateColumns = 'repeat(3, minmax(0, 1fr))';
    container.style.gap = '20px';
    container.style.padding = '0';
    container.style.maxWidth = 'none';
    container.style.width = '100%';
    container.style.margin = '0';

    insights.slice(0, 12).forEach((insight, idx) => {
        const insightTitle = insight.title || 'Clan Analysis';
        const insightMessage = insight.message || insight.insight;
        const insightType = insight.type || 'general';
        const insightTypeLabel = insightType.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

        // Robust Member Lookup (Case Insensitive)
        let member = null;
        if (insight.player) {
            const cleanName = insight.player.toLowerCase().trim();
            member = dashboardData.allMembers.find(m => m.username.toLowerCase().trim() === cleanName);
        }
        if (!member) {
            const guessed = extractPlayerName(insight, dashboardData.allMembers);
            if (guessed) member = guessed;
        }
        const displayName = member ? member.username : (insight.player || 'Clan Intelligence');

        // Theme & Assets
        const playerBossName = member ? (member.boss_30d_top || member.favorite_boss || member.favorite_boss_all_time) : null;
        const playerBossImg = member ? (member.boss_30d_top_img || member.favorite_boss_img || member.favorite_boss_all_time_img) : null;

        const typeFallback = insightAssetFallback[insightType] || insightAssetFallback.general;
        let rawAsset = playerBossImg || insight.asset || findAssetForInsight(insight, member) || typeFallback || 'boss_pet_rock.png';
        const candidateBossName = insight.boss || playerBossName || insight.title || (member ? (member.favorite_boss_all_time || member.favorite_boss) : null);
        let asset = resolveBossImage(candidateBossName, rawAsset);
        if (!asset || asset === 'boss_pet_rock.png') {
            const colorfulFallbacks = [
                'boss_vorkath.png', 'boss_zulrah.png', 'boss_general_graardor.png', 'boss_tzkal-zuk.png',
                'boss_theatre_of_blood.png', 'boss_commander_zilyana.png', 'boss_the_whisperer.png',
                'boss_alchemical_hydra.png', 'boss_phantom_muspah.png'
            ];
            asset = colorfulFallbacks[idx % colorfulFallbacks.length] || typeFallback || 'boss_pet_rock.png';
        }
        const theme = getAITheme(insightType, asset, candidateBossName);
        const rankImg = member && member.rank_img ? member.rank_img : 'rank_minion.png';

        const normalizeLabel = (val) => {
            if (!val) return '';
            const cleaned = val.replace(/boss_|rank_/gi, '').replace(/\.png$/i, '').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
            return cleaned.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        };

        const focusLabel = normalizeLabel(candidateBossName || asset || '');
        const biomeClass = getBossBiome(focusLabel || insightTypeLabel || '');

        // Stats to show
        let primaryStat = insight.score ? formatNumber(insight.score) : '';
        let secondaryLabel = insight.metric || 'Impact Score';
        const secondaryText = secondaryLabel || insightTypeLabel;

        const detailRows = [];
        detailRows.push({ label: 'Type', value: insightTypeLabel });
        if (focusLabel) detailRows.push({ label: 'Focus', value: focusLabel });
        if (primaryStat) detailRows.push({ label: secondaryLabel, value: primaryStat });
        if (insight.details) {
            Object.entries(insight.details).slice(0, 2).forEach(([k, v]) => {
                detailRows.push({ label: k, value: v });
            });
        }

        // Card Construction (match boss card styling)
        container.innerHTML += `
        <div class="unified-card ${biomeClass}" style="--theme-color: ${theme.color}; --theme-glow: ${theme.glow};">
            ${SHADOW_DECORATORS}
            <div class="card-header" style="padding: 10px 12px 0 12px;">
                <div class="card-header-inner" style="display:flex; align-items:center; width:100%; gap:10px;">
                    <img src="assets/${rankImg}" alt="rank" style="width:40px; height:40px; object-fit:contain;" onerror="this.src='assets/rank_minion.png'" />
                    <div style="flex:1;">
                         <div class="primary-text" style="font-size:1.1em; color:#fff; font-weight:bold;">${displayName}</div>
                         <div class="card-type-label" style="font-size:0.8em; opacity:0.8;">${insightTitle}</div>
                    </div>
                    <div class="rank-badge"><i class="fas ${theme.icon || 'fa-star'}"></i><span>${insightTypeLabel}</span></div>
                </div>
            </div>

            <div class="card-visual" style="text-align:center; padding-top:10px;">
                <img class="boss-img" src="assets/${asset}" alt="${insightTitle.replace(/"/g, '&quot;')}" 
                     style="height: 220px; width: 100%; object-fit: contain; filter: drop-shadow(0 0 15px ${theme.glow}); transition: transform 0.3s; image-rendering: pixelated;" 
                     onerror="this.onerror=null; this.alt=''; this.src='assets/boss_pet_rock.png';" />
            </div>
            <div class="card-info" style="text-align:center; padding:10px 0;">
                ${primaryStat ? `<div class="primary-stat-val" style="font-size:1.8em;">${primaryStat}</div>` : ''}
                <div class="secondary-text">${secondaryText}</div>
            </div>
            <div class="ai-card-message-block">
                ${formatInsightMessage(insightMessage)}
            </div>
            <div class="details-overlay">
                ${detailRows.map(r => `<div class="detail-row"><span>${r.label}</span><span>${r.value}</span></div>`).join('')}
            </div>
        </div>
        `;
    });

    // Normalize any generated image sources to the correct base path
    normalizeAssetTags(container);
}

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
        console.error(`Error in ${name}: `, e);
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
    const container = document.getElementById('general-stats');
    if (!container) return;

    container.innerHTML = '';
    container.style.display = 'grid';
    container.style.gridTemplateColumns = 'repeat(3, minmax(0, 1fr))';
    container.style.gap = '20px';
    const members = data.allMembers || [];
    const xpKey = currentPeriod === '30d' ? 'xp_30d' : 'xp_7d';
    const msgKey = currentPeriod === '30d' ? 'msgs_30d' : 'msgs_7d';
    const periodLabel = currentPeriod === '30d' ? '30d' : '7d';

    const themes = {
        blue: { color: '#00d4ff', glow: 'rgba(0, 212, 255, 0.4)' },
        gold: { color: '#FFD700', glow: 'rgba(255, 215, 0, 0.35)' },
        red: { color: '#FF3333', glow: 'rgba(255, 51, 51, 0.35)' },
        green: { color: '#33FF33', glow: 'rgba(51, 255, 51, 0.35)' }
    };

    const deriveThemeFromMember = (member, fallbackKey = 'blue') => {
        const base = themes[fallbackKey] || themes.blue;
        const bossName = member ? (member.boss_30d_top || member.favorite_boss || member.favorite_boss_all_time) : null;
        const bossTheme = bossName ? getBossTheme(bossName) : null;
        return {
            color: bossTheme?.color || base.color,
            glow: bossTheme?.glow || base.glow,
            bossName
        };
    };

    const buildCard = ({ title, titleHtml, badge, member, value, secondary, detailA, detailB, theme, imgOverride }) => {
        const t = theme || themes.blue;
        const img = imgOverride
            || (member && member.favorite_boss_img && member.favorite_boss_img !== 'boss_pet_rock.png' ? member.favorite_boss_img
                : member && member.rank_img ? member.rank_img
                    : 'rank_minion.png');
        const rankImg = member && member.rank_img ? member.rank_img : 'rank_minion.png';

        // Use titleHtml for display if provided, otherwise plain title
        const displayTitle = titleHtml || title;

        return `
            <div class="unified-card" style="--theme-color: ${t.color}; --theme-glow: ${t.glow};">
                ${SHADOW_DECORATORS}
            <div class="card-header" style="padding: 10px 12px 0 12px;">
                <div class="card-header-inner" style="display:flex; align-items:center; width:100%; gap:10px;">
                    <img src="assets/${rankImg}" alt="rank" style="width:48px; height:48px; object-fit:contain;" onerror="this.src='assets/rank_minion.png'" />
                    <div style="flex:1; text-align:center;">
                        <div class="primary-text" style="font-size:1.3em; color:#fff;">${member ? member.username : displayTitle}</div>
                        <div class="card-type-label" style="margin-top:2px;">${displayTitle}</div>
                    </div>
                    <div class="rank-badge"><span>${badge}</span></div>
                </div>
            </div>
            <div class="card-visual" style="text-align:center; padding-top:6px;">
                <img src="assets/${img}" alt="${title.replace(/"/g, '&quot;')}" style="height: 380px; object-fit: contain; filter: drop-shadow(0 0 10px ${t.glow});" />
            </div>
            <div class="card-info" style="text-align:center; padding-bottom:10px;">
                <div class="primary-stat-val" style="font-size:2.2em;">${value}</div>
                <div class="secondary-text">${secondary}</div>
            </div>
            <div class="details-overlay">
                <div class="detail-row"><span>${detailA.label}</span><span>${detailA.value}</span></div>
                <div class="detail-row"><span>${detailB.label}</span><span>${detailB.value}</span></div>
            </div>
            </div>`;
    };

    let html = '';

    const topMsg = [...members].sort((a, b) => b[msgKey] - a[msgKey])[0];
    if (topMsg && topMsg[msgKey] > 0) {
        html += buildCard({
            title: 'Top Messenger',
            titleHtml: '<h3>Top Messenger <span style="font-size:0.8em; opacity:0.7; font-weight:normal">(Total)</span></h3>',
            badge: '#1',
            member: topMsg,
            value: formatNumber(topMsg[msgKey]),
            secondary: `Messages(${periodLabel})`,
            detailA: { label: 'Total Messages', value: formatNumber(topMsg.msgs_total || 0) },
            detailB: { label: `${periodLabel} Messages`, value: formatNumber(topMsg[msgKey]) },
            theme: deriveThemeFromMember(topMsg, 'blue')
        });
    }

    const topXp = [...members].sort((a, b) => b[xpKey] - a[xpKey])[0];
    if (topXp && topXp[xpKey] > 0) {
        html += buildCard({
            title: 'Top XP',
            badge: '#1',
            member: topXp,
            value: formatNumber(topXp[xpKey]),
            secondary: `XP Gained(${periodLabel})`,
            detailA: { label: 'Total XP', value: formatNumber(topXp.total_xp || 0) },
            detailB: { label: `${periodLabel} XP`, value: formatNumber(topXp[xpKey] || 0) },
            theme: deriveThemeFromMember(topXp, 'green')
        });
    }

    const rising = members.filter(m => m.days_in_clan < 98).sort((a, b) => b[msgKey] - a[msgKey])[0];
    if (rising && rising[msgKey] > 0) {
        html += buildCard({
            title: 'Rising Star',
            titleHtml: '<h3>Rising Star <span style="font-size:0.8em; opacity:0.7; font-weight:normal">(7d Activity)</span></h3>',
            badge: '#1',
            member: rising,
            value: `${formatNumber(rising[msgKey])} msgs`,
            secondary: 'Recent Activity',
            detailA: { label: 'Days in Clan', value: formatNumber(rising.days_in_clan || 0) },
            detailB: { label: `${periodLabel} Messages`, value: formatNumber(rising[msgKey] || 0) },
            theme: deriveThemeFromMember(rising, 'blue')
        });
    }

    const topBoss = [...members].sort((a, b) => b.boss_7d - a.boss_7d)[0];
    if (topBoss && topBoss.boss_7d > 0) {
        html += buildCard({
            title: 'Top Boss Killer',
            badge: '#1',
            member: topBoss,
            value: formatNumber(topBoss.boss_7d),
            secondary: `Kills(${periodLabel})`,
            detailA: { label: 'Total Kills', value: formatNumber(topBoss.total_boss || 0) },
            detailB: { label: `${periodLabel} Kills`, value: formatNumber(topBoss.boss_7d || 0) },
            theme: deriveThemeFromMember(topBoss, 'red')
        });
    }

    const activeCount = members.filter(m => m[msgKey] > 0 || m[xpKey] > 0).length;
    html += buildCard({
        title: 'Active Members',
        badge: 'STATUS',
        member: null,
        value: activeCount,
        secondary: `${((activeCount / Math.max(members.length, 1)) * 100).toFixed(1)}% of Roster`,
        detailA: { label: 'Total Roster', value: formatNumber(members.length) },
        detailB: { label: 'Active', value: formatNumber(activeCount) },
        theme: themes.blue,
        imgOverride: 'skill_slayer.png'
    });

    // 6th card: Clan XP for the current period (7d/30d)
    const totalPeriodXp = members.reduce((sum, m) => sum + (m[xpKey] || 0), 0);
    html += buildCard({
        title: `Clan XP(${periodLabel})`,
        badge: 'CLAN',
        member: null,
        value: formatNumber(totalPeriodXp),
        secondary: 'Total XP gained',
        detailA: { label: 'Roster', value: formatNumber(members.length) },
        detailB: { label: 'Active', value: formatNumber(activeCount) },
        theme: themes.green,
        imgOverride: 'boss_the_mimic.png'
    });

    container.innerHTML = html;
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
    news.push(`📈 Clan Total XP Gained: ${formatNumber(totalXp)} `);

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
                    <span style="font-family:'Outfit'">${alert.title}</span>
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
                <span style="font-family:'Outfit'">Inactivity Risk</span>
            </div>
            <div class="player-info" style="display:flex;align-items:center;gap:15px">
                <img src="assets/${m.rank_img || 'rank_minion.png'}" style="width:40px;height:auto;" onerror="this.src='assets/rank_minion.png'">
                <div class="player-details">
                    <div class="player-name" style="color:#fff;font-weight:bold">${m.username}</div>
                    <div class="player-role" style="color:#888;font-size:0.8em">${m.role}</div>
                </div>
            </div>
            <div class="alert-metric" style="margin-top:15px;display:flex;justify-content:space-between;border-top:1px solid rgba(255,255,255,0.1);padding-top:10px">
                <div><span>Bossing:</span> <span style="color:#fff">${m.boss_7d}</span></div>
                <div><span>Msgs:</span> <span style="color:#fff">${m.msgs_7d}</span></div>
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
            title: { text: 'Messages (30d)', style: { fill: '#a0a0a0' } },
            grid: { line: { style: { stroke: '#333', lineDash: [4, 4] } } },
            label: { style: { fill: '#888' } },
            max: xMax,
            minLimit: 0
        },
        yAxis: {
            title: { text: 'XP Gained (30d)', style: { fill: '#a0a0a0' } },
            grid: { line: { style: { stroke: '#333', lineDash: [4, 4] } } },
            label: { formatter: (v) => formatNumber(Number(v)), style: { fill: '#888' } },
            min: 0
        },
        tooltip: {
            fields: ['player', 'msgs', 'xp', 'role'],
            formatter: (datum) => {
                return { name: datum.player, value: `${datum.msgs} msgs(30d), ${formatNumber(datum.xp)} XP` };
            },
            showTitle: false
        },
        theme: {
            styleSheet: {
                backgroundColor: 'transparent',
                plotBackgroundColor: 'transparent'
            }
        },
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
        theme: {
            styleSheet: {
                backgroundColor: 'transparent',
                plotBackgroundColor: 'transparent'
            }
        },
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
                    '#00FF00', '#004400', // CoX (Green)
                    '#FF0000', '#550000', // ToB (Red)
                    '#FFD700', '#665500'  // ToA (Gold)
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
            msg.innerText = fallbackBoss ? `No trend data.Fallback: ${fallbackBoss} ` : "No Trending Boss Data Available";
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
    Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';

    // Area Gradients Defaults (Chart.js doesn't do this globally easily, needs per dataset)

    Chart.defaults.font.family = "'Outfit', sans-serif";

    safelyRun(() => renderActivityHealthChart(), "renderActivityHealthChart");
    safelyRun(() => renderTopXPChart(), "renderTopXPChart");

    // NEW CHARTS
    safelyRun(() => renderScatterInteraction(), "renderScatterInteraction");
    safelyRun(() => renderBossDiversity(), "renderBossDiversity");
    safelyRun(() => renderRaidsPerformance(), "renderRaidsPerformance");
    safelyRun(() => renderSkillMastery(), "renderSkillMastery");
    safelyRun(() => renderBossTrend(), "renderBossTrend");
    safelyRun(() => renderTenureChart(), "renderTenureChart");
    safelyRun(() => renderXPWeeklyCorrelation(), "renderXPWeeklyCorrelation");
    safelyRun(() => renderLeaderboardChart(), "renderLeaderboardChart");

    // UPDATED VISUALIZATIONS
    safelyRun(() => renderActivityHeatmap(), "renderActivityHeatmap");     // NEW: Weekly 24h Heatmap
    safelyRun(() => renderActivityTrend(), "renderActivityTrend");       // NEW: Weekly Trend (Replaces Correlation/Area)
    safelyRun(() => renderXPContribution(), "renderXPContribution");      // NEW: Top 25 Annual XP (Replaces Radar)
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
                label: `XP Gained(${currentPeriod})`,
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
        theme: {
            styleSheet: {
                backgroundColor: 'transparent',
                plotBackgroundColor: 'transparent'
            }
        },
        meta: {
            xp: { alias: 'XP Gained', formatter: (v) => formatNumber(Number(v)) },
            msgs: { alias: 'Messages' }
        },
        yAxis: [
            { min: 0, label: { formatter: (v) => formatNumber(Number(v)), style: { fill: '#888' } } }, // Left: XP
            { min: 0, label: { style: { fill: '#888' } } } // Right: Messages
        ],
        legend: { position: 'top-left', itemName: { style: { fill: '#ccc' } } }
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

    // Clear container to prevent artifacts (CRITICAL FIX)
    container.innerHTML = '';

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
        color: 'l(270) 0:#33FF33 1:#00AA00',
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
            formatter: (d) => ({ name: d.type, value: `${formatNumber(d.value)} XP / yr` })
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
    setupSectionSearch('search-purging', '#purging-table tbody tr');
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
// BOSS THEME ENGINE (GLOBAL)
// ---------------------------------------------------------

// Fallback boss images for AI insight types when boss resolution fails
const insightAssetFallback = {
    'milestone': 'boss_the_mimic.png',
    'roast': 'boss_chaos_elemental.png',
    'trend-positive': 'boss_phoenix.png',
    'trend-negative': 'boss_the_nightmare.png',
    'leadership': 'boss_tzkal-zuk.png',
    'anomaly': 'boss_the_whisperer.png',
    'general': 'boss_pet_rock.png'
};

// BOSS_THEMES now sourced from CSS variables (:root)
// This creates a single source of truth for all boss colors
function getBossThemesFromCSS() {
    const root = document.documentElement;
    const getVar = (name) => getComputedStyle(root).getPropertyValue(name).trim();

    return {
        // Cyan (Ice/Spirit)
        "Vorkath": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Commander Zilyana": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Corporeal Beast": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Nex": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Wintertodt": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Duke Sucellus": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Amoxliatl": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Blue Moon": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Tempoross": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },
        "Phantom Muspah": { color: getVar('--boss-cyan'), glow: getVar('--boss-cyan-glow') },

        // Purple (Void/Shadow)
        "The Whisperer": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "The Leviathan": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "Skotizo": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "Abyssal Sire": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "Venenatis": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "Chaos Elemental": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "Obor": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "The Nightmare": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },
        "Phosani's Nightmare": { color: getVar('--boss-purple'), glow: getVar('--boss-purple-glow') },

        // Green (Venom/Nature)
        "Araxxor": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Zulrah": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Alchemical Hydra": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Grotesque Guardians": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Dagannoth Prime": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Dagannoth Supreme": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Dagannoth Rex": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Hespori": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Thermonuclear Smoke Devil": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Bryophyta": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Deranged Archaeologist": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Giant Mole": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Scurrius": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "The Hueycoatl": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Sarachnis": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Chambers Of Xeric": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },
        "Chambers Of Xeric (CM)": { color: getVar('--boss-green'), glow: getVar('--boss-green-glow') },

        // Red (Blood/Corruption)
        "The Corrupted Gauntlet": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "The Gauntlet": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Theatre Of Blood": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Theatre Of Blood (HM)": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Vardorvis": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Cerberus": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "K'ril Tsutsaroth": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Tekton": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Chaos Fanatic": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Crazy Archaeologist": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Doom of Mokhaiotl": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },
        "Blood Moon": { color: getVar('--boss-red'), glow: getVar('--boss-red-glow') },

        // Gold (Desert)
        "Tombs of Amascut": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Tombs of Amascut (Expert Mode)": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Kraken": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Callisto": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Scorpia": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Kalphite Queen": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Mimic": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Shellbane Gryphon": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "The Royal Titans": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },
        "Eclipse Moon": { color: getVar('--boss-gold'), glow: getVar('--boss-gold-glow') },

        // Orange (Fire/Magma)
        "TzKal-Zuk": { color: getVar('--boss-orange'), glow: getVar('--boss-orange-glow') },
        "TzTok-Jad": { color: getVar('--boss-orange'), glow: getVar('--boss-orange-glow') },
        "Zalcano": { color: getVar('--boss-orange'), glow: getVar('--boss-orange-glow') },
        "Sol Heredit": { color: getVar('--boss-orange'), glow: getVar('--boss-orange-glow') },
        "Yama": { color: getVar('--boss-orange'), glow: getVar('--boss-orange-glow') },

        // White (Undead/Spectral)
        "Barrows Chests": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') },
        "Vet'ion": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') },
        "Calvar'ion": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') },
        "Artio": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') },
        "Spindel": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') },
        "General Graardor": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') },
        "King Black Dragon": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') },
        "Kree'Arra": { color: getVar('--boss-white'), glow: getVar('--boss-white-glow') }
    };
}

let BOSS_THEMES = {}; // Will be initialized on DOM load

// Initialize BOSS_THEMES from CSS when document is ready
document.addEventListener('DOMContentLoaded', () => {
    BOSS_THEMES = getBossThemesFromCSS();
    console.log("BOSS_THEMES initialized from CSS variables");
});

function getBossTheme(bossName) {
    if (!bossName) return { color: "#bc13fe", glow: "rgba(188, 19, 254, 0.4)" }; // Default

    // Normalize common variants (underscores, double spaces, casing)
    const normalized = bossName.replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
    const lowerNorm = normalized.toLowerCase();

    // 1. Direct Exact Match
    if (BOSS_THEMES[normalized]) return BOSS_THEMES[normalized];

    // 2. Case-Insensitive Match
    const keys = Object.keys(BOSS_THEMES);
    const match = keys.find(k => k.toLowerCase() === lowerNorm);
    if (match) return BOSS_THEMES[match];

    // 3. Robust Fallback (Fuzzy Matching)
    const lower = lowerNorm;

    // overrides for specific keywords
    if (lower.includes('xeric') || lower.includes('cox')) return BOSS_THEMES["Chambers Of Xeric"];
    if (lower.includes('tob') || lower.includes('theatre')) return BOSS_THEMES["Theatre Of Blood"];
    if (lower.includes('toa') || lower.includes('amascut')) return BOSS_THEMES["Tombs of Amascut"];
    if (lower.includes('inferno') || lower.includes('zuk')) return BOSS_THEMES["TzKal-Zuk"];
    if (lower.includes('fight cave') || lower.includes('jad')) return BOSS_THEMES["TzTok-Jad"];

    // Explicit boss cues
    if (lower.includes('vardorvis')) return BOSS_THEMES["Vardorvis"];
    if (lower.includes('shellbane')) return BOSS_THEMES["Shellbane Gryphon"];
    if (lower.includes('duke sucellus')) return BOSS_THEMES["Duke Sucellus"];

    // RED (Blood/Chaos)
    if (lower.includes('gauntlet') || lower.includes('blood') || lower.includes('zamorak') || lower.includes('crazy') || lower.includes('vard'))
        return BOSS_THEMES["The Corrupted Gauntlet"];

    // PURPLE (Void/Shadow)
    if (lower.includes('void') || lower.includes('whisperer') || lower.includes('nightmare') || lower.includes('sire') || lower.includes('skotizo'))
        return BOSS_THEMES["The Whisperer"];

    // GOLD (Desert/ToA)
    if (lower.includes('desert') || lower.includes('royal') || lower.includes('kalphite') || lower.includes('scorpia') || lower.includes('eclipse'))
        return BOSS_THEMES["Tombs of Amascut"];

    // BLUE (Ice/Nex)
    if (lower.includes('nex') || lower.includes('ice') || lower.includes('winter') || lower.includes('moon') || lower.includes('blue') || lower.includes('frost'))
        return BOSS_THEMES["Nex"];

    // GREEN (Nature/Venom)
    if (lower.includes('rat') || lower.includes('garden') || lower.includes('tree') || lower.includes('hydra') || lower.includes('snake') || lower.includes('zulrah') || lower.includes('sarachnis') || lower.includes('mole'))
        return BOSS_THEMES["Zulrah"];

    // FIRE (Orange)
    if (lower.includes('fire') || lower.includes('magma') || lower.includes('volcano') || lower.includes('yama') || lower.includes('zalcano'))
        return BOSS_THEMES["TzKal-Zuk"];

    // UNDEAD (White)
    if (lower.includes('skeleton') || lower.includes('undead') || lower.includes('vet') || lower.includes('calvar') || lower.includes('artio') || lower.includes('spindel') || lower.includes('bear') || lower.includes('spider'))
        return BOSS_THEMES["Vet'ion"];

    // Default: Purple "Shadow Tech"
    return { color: "#bc13fe", glow: "rgba(188, 19, 254, 0.4)" };
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
        // Safeguard: Clamp negative XP values to 0 (data corruption protection)
        const total_xp = Math.max(0, m.total_xp || 0);
        const ratio = m.msgs_total > 0 ? Math.max(0, (total_xp / m.msgs_total).toFixed(0)) : 0;
        html += `
            <tr>
                <td style="display:flex;align-items:center;gap:10px">
                     <img src="assets/${m.rank_img || 'rank_minion.png'}" width="24">
                     <span class="player-link" onclick="openPlayerProfile('${m.username}')">${m.username}</span>
                </td>
                <td>${formatNumber(m.xp_7d)}</td>
                <td>${formatNumber(total_xp)}</td>
                <td>${formatNumber(m.boss_7d)}</td>
                <td>${formatNumber(m.total_boss)}</td>
                <td>${formatNumber(m.msgs_7d)}</td>
                <td>${formatNumber(m.msgs_total)}</td>
                <td>${formatNumber(ratio)}</td>
                <td>${m.days_in_clan || 0}</td>
            </tr >
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
        if (sorted.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#888">No message data available</td></tr>';
        } else {
            tbody.innerHTML = sorted.map(m => `
            <tr>
                    <td>${m.username}</td>
                    <td>${m.role}</td>
                    <td>${formatNumber(m.msgs_total)}</td>
                    <td style="color:var(--neon-green)">${m.msgs_7d}</td>
                    <td>${formatNumber(m.msgs_30d || 0)}</td> 
                </tr >
        `).join('');
        }
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
                scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: function (value) { return formatNumber(value); } } } }
            }
        });
    }

    // Scatter: XP vs Messages
    const ctxScat = document.getElementById('container-xp-scatter');
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
                theme: {
                    styleSheet: {
                        backgroundColor: 'transparent',
                        plotBackgroundColor: 'transparent'
                    }
                },
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
}

// ---------------------------------------------------------
// INTERACTION HANDLERS & MODAL
// ---------------------------------------------------------

// ---------------------------------------------------------
// INTERACTION HANDLERS & MODAL
// ---------------------------------------------------------

// Inject Modal CSS once
const style = document.createElement('style');
style.textContent = `
    .modal-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(5px);
        z-index: 1000; display: flex; align-items: center; justify-content: center;
        opacity: 0; pointer-events: none; transition: opacity 0.3s ease;
    }
    .modal-overlay.active { opacity: 1; pointer-events: auto; }
    
    .player-modal {
        background: rgba(16, 20, 24, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        width: 90%; max-width: 800px;
        max-height: 90vh; overflow-y: auto;
        box-shadow: 0 0 50px rgba(0, 212, 255, 0.1);
        transform: scale(0.95); transition: transform 0.3s ease;
        position: relative;
    }
    .modal-overlay.active .player-modal { transform: scale(1); }

    .modal-header {
        padding: 20px 25px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        display: flex; justify-content: space-between; align-items: center;
        background: linear-gradient(90deg, rgba(0,212,255,0.05) 0%, transparent 100%);
    }

    .modal-close {
        background: none; border: none; color: #888; font-size: 1.5rem; cursor: pointer;
        transition: color 0.2s;
    }
    .modal-close:hover { color: #fff; }

    .modal-body { padding: 25px; }
    
    .stat-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px; margin-top: 20px;
    }
    
    .stat-box {
        background: rgba(255, 255, 255, 0.03);
        padding: 15px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);
        text-align: center;
    }
    .stat-box .label { color: #888; font-size: 0.8rem; letter-spacing: 1px; margin-bottom: 5px; }
    .stat-box .val { color: #fff; font-size: 1.2rem; font-weight: bold; }
    .stat-box .highlight { color: #00d4ff; }
`;
document.head.appendChild(style);

function openPlayerProfile(username) {
    console.log("Opening profile for:", username);
    const member = dashboardData.allMembers.find(m => m.username === username);
    if (!member) {
        alert("Player data not found.");
        return;
    }

    let modal = document.getElementById('player-profile-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'player-profile-modal';
        modal.className = 'modal-overlay';
        modal.onclick = (e) => { if (e.target === modal) closePlayerProfile(); };
        modal.innerHTML = `
            <div class="player-modal">
                <div class="modal-header">
                    <div style="display:flex;align-items:center;gap:15px">
                        <img id="pm-rank" src="" style="width:40px;height:auto">
                        <div>
                            <h2 id="pm-username" style="margin:0;font-size:1.5rem;color:#fff"></h2>
                            <div id="pm-role" style="color:#00d4ff;font-size:0.9rem;letter-spacing:1px"></div>
                        </div>
                    </div>
                    <button class="modal-close" onclick="closePlayerProfile()"><i class="fas fa-times"></i></button>
                </div>
                <div class="modal-body">
                    <div style="display:flex; gap:25px; flex-wrap:wrap; margin-bottom:25px; align-items:center;">
                        <div style="flex:0 0 150px; text-align:center;">
                             <img id="pm-boss-img" src="" style="width:100%; max-width:120px; filter:drop-shadow(0 0 15px rgba(0,212,255,0.3));">
                             <div style="margin-top:10px;font-size:0.8rem;color:#666">Favorite Target</div>
                        </div>
                        <div style="flex:1;">
                            <h3 style="margin:0 0 15px 0; color:#fff; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px;">Performance Overview</h3>
                            <div class="stat-grid">
                                <div class="stat-box">
                                    <div class="label">TOTAL XP</div>
                                    <div class="val" id="pm-xp-total"></div>
                                </div>
                                <div class="stat-box">
                                    <div class="label">7D GAIN</div>
                                    <div class="val highlight" id="pm-xp-7d"></div>
                                </div>
                                <div class="stat-box">
                                    <div class="label">MSGS (TOTAL)</div>
                                    <div class="val" id="pm-msgs-total"></div>
                                </div>
                                <div class="stat-box">
                                    <div class="label">MSGS (7D)</div>
                                    <div class="val highlight" id="pm-msgs-7d"></div>
                                </div>
                                <div class="stat-box">
                                    <div class="label">BOSS KILLS</div>
                                    <div class="val" id="pm-boss-total"></div>
                                </div>
                                <div class="stat-box">
                                    <div class="label">DAYS IN CLAN</div>
                                    <div class="val" id="pm-tenure"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // Populate Data
    document.getElementById('pm-username').innerText = member.username;
    document.getElementById('pm-role').innerText = member.role.toUpperCase();
    document.getElementById('pm-rank').src = `assets/${member.rank_img || 'rank_minion.png'}`;
    document.getElementById('pm-rank').onerror = function () { this.src = 'assets/rank_minion.png'; };

    document.getElementById('pm-boss-img').src = `assets/${member.favorite_boss_img || 'boss_pet_rock.png'}`;
    document.getElementById('pm-boss-img').onerror = function () { this.src = 'assets/boss_pet_rock.png'; };

    document.getElementById('pm-xp-total').innerText = formatNumber(member.total_xp);
    document.getElementById('pm-xp-7d').innerText = "+" + formatNumber(member.xp_7d);
    document.getElementById('pm-msgs-total').innerText = formatNumber(member.msgs_total);
    document.getElementById('pm-msgs-7d').innerText = member.msgs_7d;
    document.getElementById('pm-boss-total').innerText = formatNumber(member.total_boss);
    document.getElementById('pm-tenure').innerText = member.days_in_clan + " days";

    // Show
    setTimeout(() => modal.classList.add('active'), 10);
}

function closePlayerProfile() {
    const modal = document.getElementById('player-profile-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}
