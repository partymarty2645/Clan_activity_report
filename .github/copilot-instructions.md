# GitHub Copilot Instructions

## Task-Orchestrator Defaults
- Start every session with get_overview(); prefer template discovery (list_templates with isEnabled=true) when creating tasks/features.
- Keep titles/summaries descriptive; include acceptance criteria and realistic complexity (1–10).

## What This Repo Does
- OSRS clan analytics pipeline: harvest WOM + Discord data, enrich with AI, generate Excel + JSON/JS dashboard, deploy to docs/Drive.
- Orchestrated by [main.py](../main.py) via `run_module()` wrappers; `run_auto.bat` runs backup → optimize → main.

## Configuration & Secrets
- Precedence: env vars > config.yaml > defaults (see [core/config.py](../core/config.py)). Critical: WOM_API_KEY, DISCORD_TOKEN, RELAY_CHANNEL_ID, WOM_GROUP_ID, optional WOM_GROUP_SECRET for group-wide refresh, LOCAL_DRIVE_PATH for Drive export.
- Config.fail_fast() aborts pipeline if required values missing; CLAN_FOUNDING_DATE clamps join dates.

## Data & DB Conventions
- SQLite via SQLAlchemy models in database/models.py; use SessionLocal / get_db() and AnalyticsService instead of raw sqlite.
- Normalize all usernames with UsernameNormalizer; timestamps are UTC via TimestampHelper.

## Pipeline Stages (main.py)
- Harvest: [scripts/harvest_sqlite.py](../scripts/harvest_sqlite.py) updates WOM group (secret gated), gathers WOM + Discord in parallel, skips recent players via WOM_STALENESS_SKIP_HOURS, keeps harvest_state.json for incremental fetch.
- AI Enrichment: [scripts/mcp_enrich.py](../scripts/mcp_enrich.py) populates data/ai_insights.json for downstream insights (fallback heuristics exist).
- Reporting: [scripts/report_sqlite.py](../scripts/report_sqlite.py) builds Excel via reporting/excel; metadata falls back to earliest snapshots when join dates missing.
- Dashboard Export: [scripts/export_sqlite.py](../scripts/export_sqlite.py) emits clan_data.json/js, computes boss/message/XPGain deltas (7d/30d/365d), applies asset fallbacks, filters zero-activity members, syncs root ↔ docs copies before Drive export.
- Publish: [scripts/publish_docs.py](../scripts/publish_docs.py) syncs clan_dashboard.html/index.html, dashboard_logic.js, clan_data.js/json, ai_data.js, assets/ into docs/ for Pages.
- Legacy CSV: [scripts/export_csv.py](../scripts/export_csv.py) runs last.

## Analytics Patterns
- Centralize metrics in AnalyticsService (get_latest_snapshots, get_snapshots_at_cutoff, get_boss_diversity_7d, get_correlation_data, get_activity_heatmap_simple, get_clan_records, etc.). Avoid ad-hoc queries.
- Boss and message stats are bulk-fetched to avoid N+1; gains clamp negatives to 0; staleness filters on cutoffs.

## AI Insights
- Export stage prefers Gemini JSON from data/ai_insights.json; fallback is heuristic AIInsightGenerator selecting 9 insights and ticker pulse.

## File Sync Gotchas
- Dashboard JS/HTML must stay mirrored between root and docs; sync helpers live in export_sqlite.py and publish_docs.py. Assets are exported recursively to Drive if LOCAL_DRIVE_PATH set.

## Developer Workflows
- One-shot pipeline: `./run_auto.bat` (Windows) or `python -m main.py` inside .venv after `setup.bat`. Logs stream to app.log with colorized stdout.
- Testing: use task “🧪 Run All Tests” (pytest tests/ -v --tb=short); run Phase 1 subset for quick checks.
- Backups/optimization: run_auto triggers backup_db.py and optimize_database.py before main; keep DB safety ratios (HARVEST_SAFE_DELETE_RATIO) intact.

## When Implementing
- Prefer adding analytics/report logic inside AnalyticsService; reuse Queries constants for SQL fragments.
- Maintain username/time normalization; clamp join dates to CLAN_FOUNDING_DATE; respect staleness thresholds instead of widening fetch loops blindly.
- Keep dashboard data schema stable (clan_data.json/js keys: allMembers, topBossers, topXPGainers, topXPYear, chart_* datasets, ai, config).

## Quick References
- Dashboard logic: [docs/dashboard_logic.js](../docs/dashboard_logic.js); HTML skin: [clan_dashboard.html](../clan_dashboard.html) (mirrored to docs/index.html).
- Assets map: [core/assets.py](../core/assets.py) and [core/asset_manager.py](../core/asset_manager.py); boss images fallback to DEFAULT_BOSS_IMAGE per context.

If anything here is unclear or missing, tell me which section to expand and I’ll refine it.