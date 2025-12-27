#!/usr/bin/env python3
"""
Clan Activity Report Data Pipeline
Queries database, processes data, generates reports
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connector import get_db
from sqlalchemy import text, func
import pandas as pd

class ClanDataPipeline:
    def __init__(self):
        self.db = next(get_db())

    def query_member_stats(self) -> pd.DataFrame:
        """Query member statistics from database."""
        query = text("""
            SELECT
                cm.username,
                COUNT(ws.id) as snapshot_count,
                MAX(ws.timestamp) as last_activity,
                AVG(ws.total_xp) as avg_xp,
                MAX(ws.total_xp) as max_xp,
                AVG(ws.total_boss_kills) as avg_boss_kills,
                MAX(ws.total_boss_kills) as max_boss_kills,
                AVG(ws.ehp) as avg_ehp,
                MAX(ws.ehp) as max_ehp
            FROM clan_members cm
            LEFT JOIN wom_snapshots ws ON cm.id = ws.user_id
            GROUP BY cm.id, cm.username
            ORDER BY avg_xp DESC
        """)

        result = self.db.execute(query).fetchall()
        return pd.DataFrame(result, columns=[
            'username', 'snapshot_count', 'last_activity',
            'avg_xp', 'max_xp', 'avg_boss_kills', 'max_boss_kills',
            'avg_ehp', 'max_ehp'
        ])

    def query_boss_rankings(self) -> pd.DataFrame:
        """Query boss ranking statistics."""
        query = text("""
            SELECT
                bs.boss_name,
                COUNT(DISTINCT ws.user_id) as players_with_kills,
                SUM(bs.kills) as total_kills,
                AVG(bs.kills) as avg_kills,
                MAX(bs.kills) as max_kills,
                AVG(CASE WHEN bs.rank > 0 THEN bs.rank END) as avg_rank,
                MIN(CASE WHEN bs.rank > 0 THEN bs.rank END) as best_rank
            FROM boss_snapshots bs
            JOIN wom_snapshots ws ON bs.snapshot_id = ws.id
            GROUP BY bs.boss_name
            ORDER BY total_kills DESC
        """)

        result = self.db.execute(query).fetchall()
        return pd.DataFrame(result, columns=[
            'boss_name', 'players_with_kills', 'total_kills',
            'avg_kills', 'max_kills', 'avg_rank', 'best_rank'
        ])

    def process_member_activity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process member activity data."""
        # Convert last_activity to datetime
        df['last_activity'] = pd.to_datetime(df['last_activity'])
        
        # Calculate activity metrics (timezone aware)
        active_threshold = datetime.now().astimezone() - timedelta(days=7)

        active_members = df[df['last_activity'] > active_threshold]
        inactive_members = df[df['last_activity'] <= active_threshold]

        return {
            'total_members': len(df),
            'active_members': len(active_members),
            'inactive_members': len(inactive_members),
            'activity_rate': len(active_members) / len(df) * 100 if len(df) > 0 else 0,
            'top_performers': df.head(10)[['username', 'avg_xp', 'max_xp']].to_dict('records'),
            'avg_xp_all': df['avg_xp'].mean(),
            'total_xp_range': {
                'min': df['avg_xp'].min(),
                'max': df['avg_xp'].max(),
                'median': df['avg_xp'].median()
            }
        }

    def process_boss_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process boss ranking data."""
        return {
            'total_bosses': len(df),
            'most_popular_boss': df.iloc[0]['boss_name'] if len(df) > 0 else None,
            'highest_total_kills': df.iloc[0]['total_kills'] if len(df) > 0 else 0,
            'boss_stats': df.head(10)[['boss_name', 'total_kills', 'players_with_kills', 'best_rank']].to_dict('records'),
            'avg_kills_per_boss': df['avg_kills'].mean(),
            'total_kills_all_bosses': df['total_kills'].sum()
        }

    def generate_report(self, member_stats: Dict, boss_stats: Dict) -> str:
        """Generate a comprehensive report."""
        report = f"""
# Clan Activity Report - {datetime.now().strftime('%Y-%m-%d')}

## Executive Summary
- **Total Members**: {member_stats['total_members']}
- **Active Members (last 7 days)**: {member_stats['active_members']} ({member_stats['activity_rate']:.1f}%)
- **Total Bosses Tracked**: {boss_stats['total_bosses']}
- **Total Boss Kills**: {boss_stats['total_kills_all_bosses']:,}

## Member Activity Analysis
### Activity Metrics
- Activity Rate: {member_stats['activity_rate']:.1f}%
- Average XP per Member: {member_stats['avg_xp_all']:,.0f}
- XP Range: {member_stats['total_xp_range']['min']:,.0f} - {member_stats['total_xp_range']['max']:,.0f}

### Top Performers
{f"\\n".join([f"- {p['username']}: {p['avg_xp']:,.0f} avg XP (max: {p['max_xp']:,.0f})" for p in member_stats['top_performers']])}

## Boss Performance Analysis
### Popular Bosses
{f"\\n".join([f"- {b['boss_name']}: {b['total_kills']:,} kills by {b['players_with_kills']} players (best rank: {b['best_rank']})" for b in boss_stats['boss_stats']])}

### Boss Statistics
- Average Kills per Boss: {boss_stats['avg_kills_per_boss']:.1f}
- Most Popular Boss: {boss_stats['most_popular_boss']}
- Highest Total Kills: {boss_stats['highest_total_kills']:,}

## Recommendations
1. Focus engagement efforts on {member_stats['inactive_members']} inactive members
2. Promote {boss_stats['most_popular_boss']} activities to maintain momentum
3. Recognize top performers: {', '.join([p['username'] for p in member_stats['top_performers'][:3]])}
4. Monitor XP growth trends for early intervention

---
*Report generated automatically by Clan Data Pipeline*
"""
        return report

    def run_pipeline(self) -> str:
        """Run the complete data pipeline."""
        print("Starting Clan Data Pipeline...")

        # Query data
        print("Querying member statistics...")
        member_df = self.query_member_stats()

        print("Querying boss rankings...")
        boss_df = self.query_boss_rankings()

        # Process data
        print("Processing member activity data...")
        member_stats = self.process_member_activity(member_df)

        print("Processing boss data...")
        boss_stats = self.process_boss_data(boss_df)

        # Generate report
        print("Generating report...")
        report = self.generate_report(member_stats, boss_stats)

        print("Pipeline complete!")
        return report

if __name__ == "__main__":
    pipeline = ClanDataPipeline()
    report = pipeline.run_pipeline()
    print("\n" + "="*80)
    print(report)
    print("="*80)

    # Save report to file
    with open("clan_activity_report.md", "w") as f:
        f.write(report)
    print("Report saved to clan_activity_report.md")