# Chart Integration Implementation Guide

**Document Version:** 1.0  
**Date:** 2025-12-22  
**Purpose:** Detailed technical guide for integrating AntV G2Plot charts into ClanStats dashboard

---

## Overview

This document provides step-by-step implementation instructions for integrating 7 different chart types into the ClanStats dashboard. Each chart requires:

1. **Data extraction** from SQLite database
2. **Data transformation** to correct format
3. **JSON export** to `clan_data.json`
4. **HTML/JavaScript integration** into dashboard

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Chart 1: Area Chart (Activity Trends)](#chart-1-area-chart)
3. [Chart 2: Funnel Chart (Member Progression)](#chart-2-funnel-chart)
4. [Chart 3: Radar Chart (Skill Comparison)](#chart-3-radar-chart)
5. [Chart 4: Scatter Chart (Engagement Archetypes)](#chart-4-scatter-chart)
6. [Chart 5: Column Chart (XP by Skill)](#chart-5-column-chart)
7. [Chart 6: Sankey Chart (Member Flow)](#chart-6-sankey-chart)
8. [Chart 7: Pie Chart (Activity Breakdown)](#chart-7-pie-chart)
9. [Chart 8: Line Chart (Health Metrics)](#chart-8-line-chart)
10. [Integration Checklist](#integration-checklist)

---

## Architecture Overview

### Current Data Pipeline

```
WOM API + Discord API
        ↓
   clan_data.db (SQLite)
        ↓
   scripts/export_sqlite.py
        ↓
   clan_data.json
        ↓
   docs/dashboard_logic.js
        ↓
   docs/index.html (renders charts)
```

### Required Changes

1. **Update `scripts/export_sqlite.py`** - Add functions to generate chart data
2. **Update `clan_data.json`** - Export new chart data structures
3. **Update `docs/dashboard_logic.js`** - Add chart rendering logic
4. **Update `docs/index.html`** - Add chart containers and AntV library

### AntV G2Plot Library

- **CDN Link:** `https://cdn.jsdelivr.net/npm/@antv/g2plot`
- **No build required** - Works directly in browser
- **Dark theme compatible** - Matches your existing dashboard

---

## Chart 1: Area Chart (Activity Trends)

### Purpose
Shows daily messages + XP gained over time (stacked areas). Reveals peak activity periods and trending engagement.

### SQL Query

```sql
-- Extract daily activity data
SELECT 
    DATE(dm.created_at) as date,
    COUNT(dm.id) as messages,
    COALESCE(SUM(ws.overall_experience - ws.prev_experience), 0) / 1000000 as xp_millions
FROM discord_messages dm
LEFT JOIN wom_snapshots ws ON DATE(dm.created_at) = DATE(ws.timestamp)
WHERE dm.created_at >= DATE('now', '-30 days')
GROUP BY DATE(dm.created_at)
ORDER BY date DESC;
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_daily_activity_chart(session, days=30):
    """Extract daily activity data for area chart."""
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta, timezone
    
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    stmt = select(
        func.date(DiscordMessage.created_at).label('date'),
        func.count(DiscordMessage.id).label('messages'),
        func.sum(WOMSnapshot.overall_experience) / 1_000_000
    ).where(
        DiscordMessage.created_at >= cutoff
    ).group_by(
        func.date(DiscordMessage.created_at)
    ).order_by(
        func.date(DiscordMessage.created_at).asc()
    )
    
    results = session.execute(stmt).all()
    
    # Format for area chart
    data = []
    for date_obj, messages, xp in results:
        date_str = str(date_obj)
        data.append({
            'time': date_str,
            'value': int(messages or 0),
            'group': 'Messages'
        })
        data.append({
            'time': date_str,
            'value': float(xp or 0),
            'group': 'XP (Millions)'
        })
    
    return data
```

### JSON Export

```json
{
  "chart_area_activity": [
    {"time": "2025-12-01", "value": 842, "group": "Messages"},
    {"time": "2025-12-01", "value": 32.5, "group": "XP (Millions)"},
    {"time": "2025-12-02", "value": 1205, "group": "Messages"},
    {"time": "2025-12-02", "value": 48.2, "group": "XP (Millions)"}
  ]
}
```

### HTML/JavaScript Integration

```html
<!-- In docs/index.html -->
<div id="chart-area-activity" style="height: 400px;"></div>

<script>
// In docs/dashboard_logic.js
function renderAreaActivityChart() {
    if (!clanData.chart_area_activity) return;
    
    const chart = new G2Plot.AreaChart(
        'chart-area-activity',
        {
            data: clanData.chart_area_activity,
            xField: 'time',
            yField: 'value',
            seriesField: 'group',
            smooth: true,
            animation: {
                appear: { animation: 'path-in', duration: 1000 }
            },
            theme: 'dark',
            color: ['#51CF66', '#FFE66D'],
            xAxis: { type: 'time' },
            yAxis: { label: { formatter: (v) => `${v}` } }
        }
    );
    
    chart.render();
}

// Call on data load
document.addEventListener('clanDataLoaded', renderAreaActivityChart);
</script>
```

---

## Chart 2: Funnel Chart (Member Progression)

### Purpose
Shows conversion from Recruit → Member → Officer → Leadership. Identifies where churn happens.

### SQL Query

```sql
-- Count members by role
SELECT role, COUNT(*) as count
FROM clan_members
GROUP BY role
ORDER BY CASE 
    WHEN role = 'Recruit' THEN 1
    WHEN role = 'Member' THEN 2
    WHEN role = 'Member+' THEN 3
    WHEN role = 'Officer' THEN 4
    WHEN role = 'Leadership' THEN 5
    ELSE 6
END;
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_funnel_chart(session):
    """Extract membership hierarchy for funnel chart."""
    from sqlalchemy import func
    from core.roles import RoleAuthority, ClanRole
    
    # Query member counts by role
    stmt = select(
        ClanMember.role,
        func.count(ClanMember.username).label('count')
    ).group_by(ClanMember.role)
    
    results = session.execute(stmt).all()
    
    # Define role ordering
    role_order = {
        'Recruit': 0,
        'Member': 1,
        'Member+': 2,
        'Officer': 3,
        'Leadership': 4
    }
    
    # Convert to funnel format
    data = []
    for role, count in sorted(results, key=lambda x: role_order.get(x[0], 999)):
        data.append({
            'category': role,
            'value': int(count)
        })
    
    return data
```

### JSON Export

```json
{
  "chart_funnel_progression": [
    {"category": "Recruit", "value": 1450},
    {"category": "Member", "value": 980},
    {"category": "Member+", "value": 520},
    {"category": "Officer", "value": 145},
    {"category": "Leadership", "value": 28}
  ]
}
```

### HTML/JavaScript Integration

```html
<div id="chart-funnel-progression" style="height: 400px;"></div>

<script>
function renderFunnelChart() {
    if (!clanData.chart_funnel_progression) return;
    
    const chart = new G2Plot.Funnel(
        'chart-funnel-progression',
        {
            data: clanData.chart_funnel_progression,
            xField: 'category',
            yField: 'value',
            seriesField: null,
            legend: false,
            statistic: {
                title: null,
                content: null
            },
            theme: 'dark',
            color: ['#51CF66', '#FFE66D', '#FF6B6B', '#4ECDC4', '#A5D8FF']
        }
    );
    
    chart.render();
}

document.addEventListener('clanDataLoaded', renderFunnelChart);
</script>
```

---

## Chart 3: Radar Chart (Skill Comparison)

### Purpose
Compare top members vs average members across multiple skill dimensions.

### SQL Query

```sql
-- Get avg and max for each skill
SELECT 
    skill_name,
    AVG(level) as avg_level,
    MAX(level) as max_level
FROM (
    SELECT 'Attack' as skill_name, 
           json_extract(raw_data, '$.skills.attack.level') as level
    FROM wom_snapshots
    UNION ALL
    SELECT 'Strength', json_extract(raw_data, '$.skills.strength.level')
    FROM wom_snapshots
    -- ... repeat for all skills
)
GROUP BY skill_name;
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_radar_chart(session):
    """Extract skill distribution for radar chart."""
    import json
    from sqlalchemy import func, cast, String
    
    # Get all snapshots with raw data
    stmt = select(WOMSnapshot.raw_data).order_by(WOMSnapshot.timestamp.desc()).limit(1000)
    snapshots = session.execute(stmt).scalars().all()
    
    # Extract skills from JSON
    skill_data = {}
    for snapshot_json in snapshots:
        if not snapshot_json:
            continue
        
        try:
            data = json.loads(snapshot_json)
            skills = data.get('data', {}).get('skills', {})
            
            for skill_name, skill_info in skills.items():
                if skill_name not in skill_data:
                    skill_data[skill_name] = []
                skill_data[skill_name].append(skill_info.get('level', 0))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    # Calculate avg and max
    result = []
    for skill_name, levels in skill_data.items():
        if not levels:
            continue
        
        avg_level = sum(levels) / len(levels)
        max_level = max(levels)
        
        # Add both groups to chart
        result.append({
            'name': skill_name.capitalize(),
            'value': int(avg_level),
            'group': 'Average Member'
        })
        result.append({
            'name': skill_name.capitalize(),
            'value': int(max_level),
            'group': 'Top Member'
        })
    
    return result
```

### JSON Export

```json
{
  "chart_radar_skills": [
    {"name": "Attack", "value": 65, "group": "Average Member"},
    {"name": "Attack", "value": 87, "group": "Top Member"},
    {"name": "Strength", "value": 68, "group": "Average Member"},
    {"name": "Strength", "value": 92, "group": "Top Member"}
  ]
}
```

### HTML/JavaScript Integration

```html
<div id="chart-radar-skills" style="height": 400px;"></div>

<script>
function renderRadarChart() {
    if (!clanData.chart_radar_skills) return;
    
    const chart = new G2Plot.Radar(
        'chart-radar-skills',
        {
            data: clanData.chart_radar_skills,
            xField: 'name',
            yField: 'value',
            seriesField: 'group',
            meta: {
                value: { alias: 'Level', min: 0, max: 99 }
            },
            xAxis: {
                tickLine: null,
                grid: { line: { style: { stroke: '#444' } } }
            },
            yAxis: {
                label: null,
                grid: { line: { style: { stroke: '#444' } } }
            },
            theme: 'dark',
            color: ['#A5D8FF', '#FF6B6B']
        }
    );
    
    chart.render();
}

document.addEventListener('clanDataLoaded', renderRadarChart);
</script>
```

---

## Chart 4: Scatter Chart (Engagement Archetypes)

### Purpose
Shows correlation between XP and messages to identify member archetypes (Grinders, Socialites, Balanced, Inactive).

### SQL Query

```sql
-- Get 30-day stats per member
SELECT 
    username,
    SUM(CASE WHEN timestamp >= DATE('now', '-30 days') 
        THEN overall_experience ELSE 0 END) as xp_30d,
    COUNT(CASE WHEN created_at >= DATE('now', '-30 days')
        THEN 1 END) as messages_30d
FROM clan_members cm
LEFT JOIN wom_snapshots ws ON cm.username = ws.username
LEFT JOIN discord_messages dm ON cm.username = dm.author_name
GROUP BY cm.username;
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_scatter_chart(session, days=30):
    """Extract member archetypes for scatter chart."""
    from sqlalchemy import func, and_, case
    from datetime import datetime, timedelta, timezone
    
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    # Get XP and message counts per member
    xp_stmt = select(
        WOMSnapshot.username,
        func.sum(
            WOMSnapshot.overall_experience - 
            func.coalesce(WOMSnapshot.prev_experience, 0)
        ).label('xp_30d')
    ).where(WOMSnapshot.timestamp >= cutoff).group_by(WOMSnapshot.username)
    
    msg_stmt = select(
        DiscordMessage.author_name,
        func.count(DiscordMessage.id).label('messages_30d')
    ).where(DiscordMessage.created_at >= cutoff).group_by(DiscordMessage.author_name)
    
    xp_data = {row[0]: row[1] or 0 for row in session.execute(xp_stmt)}
    msg_data = {row[0]: row[1] or 0 for row in session.execute(msg_stmt)}
    
    # Combine and classify
    result = []
    for username in set(list(xp_data.keys()) + list(msg_data.keys())):
        xp = xp_data.get(username, 0)
        msgs = msg_data.get(username, 0)
        
        # Classify archetype
        if xp > 30_000_000 and msgs < 100:
            group = 'Grinders'
        elif xp < 15_000_000 and msgs > 300:
            group = 'Socialites'
        elif xp > 15_000_000 and msgs > 100:
            group = 'Balanced'
        else:
            group = 'Inactive'
        
        result.append({
            'x': int(xp),
            'y': int(msgs),
            'group': group
        })
    
    return result
```

### JSON Export

```json
{
  "chart_scatter_archetypes": [
    {"x": 42000000, "y": 85, "group": "Grinders"},
    {"x": 12000000, "y": 456, "group": "Socialites"},
    {"x": 24500000, "y": 234, "group": "Balanced"},
    {"x": 2100000, "y": 12, "group": "Inactive"}
  ]
}
```

### HTML/JavaScript Integration

```html
<div id="chart-scatter-archetypes" style="height: 400px;"></div>

<script>
function renderScatterChart() {
    if (!clanData.chart_scatter_archetypes) return;
    
    const chart = new G2Plot.Scatter(
        'chart-scatter-archetypes',
        {
            data: clanData.chart_scatter_archetypes,
            xField: 'x',
            yField: 'y',
            seriesField: 'group',
            xAxis: {
                type: 'linear',
                label: { formatter: (v) => `${(v / 1000000).toFixed(0)}M` }
            },
            yAxis: {
                label: { formatter: (v) => `${v} msgs` }
            },
            theme: 'dark',
            color: ['#51CF66', '#FFE66D', '#A5D8FF', '#FF6B6B'],
            pointSize: 8,
            tooltip: {
                title: null,
                showTitle: false,
                formatter: (datum) => {
                    return {
                        name: datum.group,
                        value: `${(datum.x / 1000000).toFixed(1)}M XP, ${datum.y} msgs`
                    };
                }
            }
        }
    );
    
    chart.render();
}

document.addEventListener('clanDataLoaded', renderScatterChart);
</script>
```

---

## Chart 5: Column Chart (XP by Skill)

### Purpose
Shows total clan XP gains by skill over the period. Identifies training priorities.

### SQL Query

```sql
-- Extract XP by skill from raw_data JSON
SELECT 
    'Attack' as skill,
    SUM(json_extract(raw_data, '$.data.skills.attack.experience')) as total_xp
FROM wom_snapshots
WHERE timestamp >= DATE('now', '-30 days')
-- Repeat for each skill
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_column_chart(session, days=30):
    """Extract XP by skill for column chart."""
    import json
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta, timezone
    
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    # Get all snapshots with raw data
    stmt = select(WOMSnapshot.raw_data).where(
        WOMSnapshot.timestamp >= cutoff
    )
    
    snapshots = session.execute(stmt).scalars().all()
    
    # Aggregate XP by skill
    skill_xp = {}
    for snapshot_json in snapshots:
        if not snapshot_json:
            continue
        
        try:
            data = json.loads(snapshot_json)
            skills = data.get('data', {}).get('skills', {})
            
            for skill_name, skill_info in skills.items():
                if skill_name not in skill_xp:
                    skill_xp[skill_name] = 0
                skill_xp[skill_name] += skill_info.get('experience', 0)
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    # Format for column chart (top 10 skills)
    result = []
    for skill, xp in sorted(
        skill_xp.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]:
        result.append({
            'category': skill.capitalize(),
            'value': int(xp / 1_000_000)  # Convert to millions
        })
    
    return result
```

### JSON Export

```json
{
  "chart_column_xp_skills": [
    {"category": "Attack", "value": 2400},
    {"category": "Strength", "value": 2100},
    {"category": "Defence", "value": 1950},
    {"category": "Ranged", "value": 1650}
  ]
}
```

### HTML/JavaScript Integration

```html
<div id="chart-column-xp" style="height: 400px;"></div>

<script>
function renderColumnChart() {
    if (!clanData.chart_column_xp_skills) return;
    
    const chart = new G2Plot.Column(
        'chart-column-xp',
        {
            data: clanData.chart_column_xp_skills,
            xField: 'category',
            yField: 'value',
            seriesField: null,
            color: '#51CF66',
            columnStyle: { radius: [4, 4, 0, 0] },
            label: {
                position: 'top',
                style: { fill: '#aaa', fontSize: 12 }
            },
            yAxis: {
                label: { formatter: (v) => `${v}M` }
            },
            theme: 'dark'
        }
    );
    
    chart.render();
}

document.addEventListener('clanDataLoaded', renderColumnChart);
</script>
```

---

## Chart 6: Sankey Chart (Member Flow)

### Purpose
Shows how members progress through ranks and where they leave. Identifies retention bottlenecks.

### SQL Query

```sql
-- Count member movements between ranks
-- Requires tracking role changes over 30 days
-- Query gets complex: need historical role data

-- Simplified: use current + estimated churn
SELECT 
    'Recruit' as source,
    'Member' as target,
    COUNT(*) as count
FROM clan_members
WHERE role = 'Member'
AND joined_at >= DATE('now', '-30 days');
-- Repeat for each transition
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_sankey_chart(session):
    """
    Extract member flow for Sankey chart.
    
    NOTE: Requires historical role tracking.
    This is a simplified version showing current distribution.
    """
    from sqlalchemy import func
    from core.roles import RoleAuthority, ClanRole
    
    # Get member counts by role
    stmt = select(
        ClanMember.role,
        func.count(ClanMember.username).label('count')
    ).group_by(ClanMember.role)
    
    role_counts = {row[0]: row[1] for row in session.execute(stmt)}
    
    # Estimate flows (simplified - needs historical data)
    result = []
    
    # Recruit -> Member (assume 80% stay, 20% leave)
    recruits = role_counts.get('Recruit', 0)
    promoted = int(recruits * 0.80)
    left = recruits - promoted
    
    if promoted > 0:
        result.append({
            'source': 'Recruit (New)',
            'target': 'Member',
            'value': promoted
        })
    if left > 0:
        result.append({
            'source': 'Recruit (New)',
            'target': 'Left Clan',
            'value': left
        })
    
    # Member -> Member+ (similar logic)
    members = role_counts.get('Member', 0)
    promoted = int(members * 0.75)
    left = int(members * 0.10)
    
    if promoted > 0:
        result.append({
            'source': 'Member',
            'target': 'Member+',
            'value': promoted
        })
    if left > 0:
        result.append({
            'source': 'Member',
            'target': 'Left Clan',
            'value': left
        })
    
    # Member+ -> Officer
    member_plus = role_counts.get('Member+', 0)
    promoted = int(member_plus * 0.50)
    left = int(member_plus * 0.08)
    
    if promoted > 0:
        result.append({
            'source': 'Member+',
            'target': 'Officer',
            'value': promoted
        })
    if left > 0:
        result.append({
            'source': 'Member+',
            'target': 'Left Clan',
            'value': left
        })
    
    # Officer -> Leadership
    officers = role_counts.get('Officer', 0)
    promoted = int(officers * 0.30)
    left = int(officers * 0.05)
    
    if promoted > 0:
        result.append({
            'source': 'Officer',
            'target': 'Leadership',
            'value': promoted
        })
    if left > 0:
        result.append({
            'source': 'Officer',
            'target': 'Left Clan',
            'value': left
        })
    
    return result
```

### JSON Export

```json
{
  "chart_sankey_flow": [
    {"source": "Recruit (New)", "target": "Member", "value": 145},
    {"source": "Recruit (New)", "target": "Left Clan", "value": 127},
    {"source": "Member", "target": "Member+", "value": 89},
    {"source": "Member", "target": "Left Clan", "value": 34}
  ]
}
```

### HTML/JavaScript Integration

```html
<div id="chart-sankey-flow" style="height": 500px;"></div>

<script>
function renderSankeyChart() {
    if (!clanData.chart_sankey_flow) return;
    
    const chart = new G2Plot.Sankey(
        'chart-sankey-flow',
        {
            data: clanData.chart_sankey_flow,
            sourceField: 'source',
            targetField: 'target',
            weightField: 'value',
            nodeCfg: {
                size: [20, 60],
                padding: [50, 50],
                style: {
                    fill: '#51CF66',
                    fillOpacity: 0.8
                }
            },
            edgeCfg: {
                style: {
                    stroke: '#aaa',
                    strokeOpacity: 0.5
                }
            },
            theme: 'dark',
            animation: false,
            tooltip: {
                title: null,
                showTitle: false
            }
        }
    );
    
    chart.render();
}

document.addEventListener('clanDataLoaded', renderSankeyChart);
</script>
```

---

## Chart 7: Pie Chart (Activity Breakdown)

### Purpose
Shows what activities the clan focuses on (PvM, training, skilling, etc).

### SQL Query

```sql
-- Infer activity from boss kills and XP progression
SELECT 
    'PvM (Bosses)' as activity,
    COUNT(*) as count
FROM boss_snapshots
WHERE timestamp >= DATE('now', '-30 days')
-- Repeat for other activities based on XP types
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_pie_chart(session, days=30):
    """Extract activity distribution for pie chart."""
    import json
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone
    
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    # Get boss kills (indicator of PvM)
    boss_stmt = select(func.count(BossSnapshot.id)).where(
        BossSnapshot.timestamp >= cutoff
    )
    pvm_kills = session.execute(boss_stmt).scalar() or 0
    
    # Get XP by skill to infer activities
    xp_stmt = select(WOMSnapshot.raw_data).where(
        WOMSnapshot.timestamp >= cutoff
    )
    
    skill_xp = {
        'combat': 0,
        'skilling': 0,
        'ranged': 0,
        'magic': 0
    }
    
    for snapshot_json in session.execute(xp_stmt).scalars():
        if not snapshot_json:
            continue
        
        try:
            data = json.loads(snapshot_json)
            skills = data.get('data', {}).get('skills', {})
            
            # Classify skills
            combat_skills = ['attack', 'strength', 'defence', 'constitution']
            skilling_skills = ['cooking', 'firemaking', 'crafting', 'smithing']
            
            for skill, info in skills.items():
                xp = info.get('experience', 0)
                if skill in combat_skills:
                    skill_xp['combat'] += xp
                elif skill in skilling_skills:
                    skill_xp['skilling'] += xp
                elif skill in ['ranged', 'cannon']:
                    skill_xp['ranged'] += xp
                elif skill in ['magic']:
                    skill_xp['magic'] += xp
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Format for pie chart
    result = [
        {'category': 'PvM (Bosses)', 'value': int(pvm_kills)},
        {
            'category': 'Skilling (Combat)',
            'value': int((skill_xp['combat'] + skill_xp['ranged']) / 1_000_000)
        },
        {
            'category': 'Skilling (Non-Combat)',
            'value': int(skill_xp['skilling'] / 1_000_000)
        },
        {'category': 'Magic', 'value': int(skill_xp['magic'] / 1_000_000)},
        {'category': 'Other', 'value': 100}  # Placeholder
    ]
    
    return result
```

### JSON Export

```json
{
  "chart_pie_activities": [
    {"category": "PvM (Bosses)", "value": 4250},
    {"category": "Skilling (Combat)", "value": 3120},
    {"category": "Skilling (Non-Combat)", "value": 1890},
    {"category": "Magic", "value": 340},
    {"category": "Other", "value": 180}
  ]
}
```

### HTML/JavaScript Integration

```html
<div id="chart-pie-activities" style="height": 400px;"></div>

<script>
function renderPieChart() {
    if (!clanData.chart_pie_activities) return;
    
    const chart = new G2Plot.Pie(
        'chart-pie-activities',
        {
            data: clanData.chart_pie_activities,
            angleField: 'value',
            colorField: 'category',
            radius: 0.9,
            innerRadius: 0.6,  // Donut style
            label: {
                type: 'inner',
                offset: '-30%',
                content: '{percentage}'
            },
            theme: 'dark',
            color: ['#51CF66', '#FFE66D', '#FF6B6B', '#A5D8FF', '#4ECDC4']
        }
    );
    
    chart.render();
}

document.addEventListener('clanDataLoaded', renderPieChart);
</script>
```

---

## Chart 8: Line Chart (Health Metrics)

### Purpose
Tracks clan health indicators (avg member level, participation rate) over time.

### SQL Query

```sql
-- Get daily avg member level
SELECT 
    DATE(timestamp) as date,
    AVG(json_extract(raw_data, '$.data.skills.overall.level')) as avg_level,
    COUNT(DISTINCT username) as active_members
FROM wom_snapshots
WHERE timestamp >= DATE('now', '-30 days')
GROUP BY DATE(timestamp)
ORDER BY date;
```

### Python Function

```python
# File: scripts/export_sqlite.py (NEW FUNCTION)

def get_line_chart(session, days=30):
    """Extract health metrics for line chart."""
    import json
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta, timezone
    
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    
    # Get snapshots grouped by date
    stmt = select(
        func.date(WOMSnapshot.timestamp).label('date'),
        func.count(WOMSnapshot.id).label('snapshot_count'),
        WOMSnapshot.raw_data
    ).where(
        WOMSnapshot.timestamp >= cutoff
    ).group_by(
        func.date(WOMSnapshot.timestamp)
    ).order_by(
        func.date(WOMSnapshot.timestamp)
    )
    
    results = session.execute(stmt).all()
    
    result = []
    for date_obj, count, snapshot_json in results:
        date_str = str(date_obj)
        
        # Parse JSON to get avg level
        avg_level = 0
        if snapshot_json:
            try:
                data = json.loads(snapshot_json)
                overall = data.get('data', {}).get('skills', {}).get('overall', {})
                avg_level = overall.get('level', 0)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Participation rate = snapshots / total members
        participation_rate = int((count / 100) * 100)  # Normalize
        
        result.append({
            'time': date_str,
            'value': int(avg_level),
            'group': 'Avg Member Level'
        })
        result.append({
            'time': date_str,
            'value': participation_rate,
            'group': 'Participation Rate'
        })
    
    return result
```

### JSON Export

```json
{
  "chart_line_health": [
    {"time": "2025-12-01", "value": 74, "group": "Avg Member Level"},
    {"time": "2025-12-01", "value": 68, "group": "Participation Rate"},
    {"time": "2025-12-05", "value": 76, "group": "Avg Member Level"},
    {"time": "2025-12-05", "value": 71, "group": "Participation Rate"}
  ]
}
```

### HTML/JavaScript Integration

```html
<div id="chart-line-health" style="height: 400px;"></div>

<script>
function renderLineChart() {
    if (!clanData.chart_line_health) return;
    
    const chart = new G2Plot.Line(
        'chart-line-health',
        {
            data: clanData.chart_line_health,
            xField: 'time',
            yField: 'value',
            seriesField: 'group',
            smooth: true,
            animation: {
                appear: {
                    animation: 'path-in',
                    duration: 1000
                }
            },
            theme: 'dark',
            color: ['#51CF66', '#A5D8FF'],
            xAxis: { type: 'time' },
            yAxis: {
                min: 0,
                max: 100,
                label: { formatter: (v) => `${v}` }
            },
            point: {
                size: 5,
                shape: 'circle'
            }
        }
    );
    
    chart.render();
}

document.addEventListener('clanDataLoaded', renderLineChart);
</script>
```

---

## Integration Checklist

### Step 1: Update Python Export Functions

- [ ] Add all 8 function stubs to `scripts/export_sqlite.py`
- [ ] Test each function with sample data
- [ ] Handle edge cases (null values, missing data)
- [ ] Add error logging

### Step 2: Update Data Export

- [ ] Call all 8 functions in `export_to_json()`
- [ ] Add chart data to `clan_data.json` structure:
  ```python
  json_data = {
      'last_updated': datetime.now(timezone.utc).isoformat(),
      'members': [...],
      'stats': {...},
      'charts': {
          'area_activity': [...],
          'funnel_progression': [...],
          'radar_skills': [...],
          'scatter_archetypes': [...],
          'column_xp_skills': [...],
          'sankey_flow': [...],
          'pie_activities': [...],
          'line_health': [...]
      }
  }
  ```

### Step 3: Update HTML Dashboard

- [ ] Add AntV library CDN link to `docs/index.html`:
  ```html
  <script src="https://cdn.jsdelivr.net/npm/@antv/g2plot"></script>
  ```
- [ ] Add container divs for each chart
- [ ] Ensure dark theme styling matches

### Step 4: Update JavaScript Logic

- [ ] Add 8 render functions to `docs/dashboard_logic.js`
- [ ] Dispatch `clanDataLoaded` event after fetching `clan_data.json`
- [ ] Call all render functions on data load
- [ ] Add error handling for missing data

### Step 5: Testing

- [ ] Verify each chart renders correctly
- [ ] Check data accuracy against database
- [ ] Test with different data sizes (large rosters, long date ranges)
- [ ] Verify dark theme aesthetics
- [ ] Test responsiveness on different screen sizes

### Step 6: Performance Optimization

- [ ] Profile query performance (especially Sankey)
- [ ] Add indexes if needed (see Issue #1 in VSCODE_AUDIT.md)
- [ ] Consider caching frequently queried data
- [ ] Monitor memory usage with large datasets

---

## Implementation Priority

**Phase 1 (MVP):** Area + Scatter + Pie charts
- **Why:** Show activity trends, member types, and activity breakdown
- **Effort:** 2-3 days
- **Impact:** High - most useful for clan leadership

**Phase 2 (Polish):** Funnel + Sankey + Line
- **Why:** Retention analysis is crucial for growth
- **Effort:** 2-3 days  
- **Impact:** High - identify where members leave

**Phase 3 (Enhancement):** Radar + Column
- **Why:** Skill analysis and training metrics
- **Effort:** 1-2 days
- **Impact:** Medium - useful but secondary

---

## Common Issues & Solutions

### Issue: Large JSON files slow dashboard load
**Solution:**
- Implement pagination (only show last 30 days)
- Add caching headers
- Use gzip compression
- Consider splitting into separate JSON files per chart

### Issue: Null values break charts
**Solution:**
- Filter `WHERE value IS NOT NULL` in SQL
- Handle JSON parse errors with try/except
- Provide default values (0 or skip)

### Issue: AntV charts not rendering
**Solution:**
- Check browser console for errors
- Verify CDN link is accessible
- Ensure container div has height set
- Confirm `clanDataLoaded` event fires

### Issue: Sankey chart too complex
**Solution:**
- Limit nodes to 5-7 max (Recruit, Member, Member+, Officer, Leadership, Left)
- Simplify flow (omit inactive → active transitions)
- Show summary stats alongside chart

---

## Future Enhancements

1. **Interactive filtering:** Click to filter by date range
2. **Export to image:** Save charts as PNG/SVG
3. **Drill-down:** Click bar/segment to see details
4. **Animations:** Smooth transitions on data updates
5. **Comparisons:** "This month vs last month" view
6. **Alerts:** Flag concerning trends (high churn, low participation)

---

**Document Complete**

This guide provides complete implementation instructions for integrating 8 chart types into your dashboard. Start with Phase 1 (Area + Scatter + Pie) for quick wins.
