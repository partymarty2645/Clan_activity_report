#!/usr/bin/env python3
"""
Performance benchmark script for UserAccessService vs direct database access.
Tests bulk operations and individual queries to validate efficiency improvements.
"""

import sys
import os
import time
import statistics
from typing import List, Tuple

# Add parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import logging
from core.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def benchmark_unified_access() -> Tuple[float, int]:
    """Benchmark unified access patterns (what UserAccessService provides)."""
    conn = sqlite3.connect(Config.DB_FILE)
    cursor = conn.cursor()
    
    start_time = time.time()
    
    # Unified query that gets comprehensive member data
    cursor.execute("""
        SELECT 
            cm.id,
            cm.username,
            cm.role,
            cm.joined_at,
            COUNT(DISTINCT dm.id) as msg_count,
            MAX(ws.timestamp) as latest_snapshot,
            MAX(ws.total_xp) as total_xp,
            MAX(ws.total_boss_kills) as total_boss_kills
        FROM clan_members cm
        LEFT JOIN discord_messages dm ON cm.id = dm.user_id
        LEFT JOIN wom_snapshots ws ON cm.id = ws.user_id
        WHERE ws.timestamp >= datetime('now', '-30 days')
        GROUP BY cm.id, cm.username, cm.role, cm.joined_at
        ORDER BY cm.username
    """)
    unified_results = cursor.fetchall()
    member_count = len(unified_results)
    
    end_time = time.time()
    conn.close()
    
    return end_time - start_time, member_count

def benchmark_fragmented_access() -> Tuple[float, int]:
    """Benchmark old fragmented access patterns (what scripts used to do)."""
    conn = sqlite3.connect(Config.DB_FILE)
    cursor = conn.cursor()
    
    start_time = time.time()
    
    # Step 1: Get active members
    cursor.execute("""
        SELECT DISTINCT cm.username, cm.id
        FROM clan_members cm
        JOIN wom_snapshots ws ON cm.id = ws.user_id
        WHERE ws.timestamp >= datetime('now', '-30 days')
        ORDER BY cm.username
    """)
    members = cursor.fetchall()
    member_count = len(members)
    
    # Step 2: Get individual data for each member (old fragmented pattern)
    for username, user_id in members:
        # Individual queries that UserAccessService consolidates
        cursor.execute("SELECT role, joined_at FROM clan_members WHERE id = ?", (user_id,))
        cursor.execute("SELECT COUNT(*) FROM discord_messages WHERE user_id = ?", (user_id,))
        cursor.execute("SELECT total_xp, total_boss_kills FROM wom_snapshots WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
    
    end_time = time.time()
    conn.close()
    
    return end_time - start_time, member_count

def run_performance_comparison():
    """Run comprehensive performance comparison."""
    print("🔬 Performance Benchmark: Unified vs Fragmented Database Access")
    print("=" * 70)
    
    runs = 3
    unified_times = []
    fragmented_times = []
    
    for run in range(runs):
        print(f"\n📊 Run {run + 1}/{runs}")
        
        # Test unified approach (UserAccessService style)
        unified_time, member_count = benchmark_unified_access()
        unified_times.append(unified_time)
        print(f"  Unified Access:    {unified_time:.3f}s ({member_count} members)")
        
        # Test fragmented approach (old script style)  
        fragmented_time, _ = benchmark_fragmented_access()
        fragmented_times.append(fragmented_time)
        print(f"  Fragmented Access: {fragmented_time:.3f}s ({member_count} members)")
        
        # Calculate efficiency
        if fragmented_time > 0:
            efficiency = ((fragmented_time - unified_time) / fragmented_time) * 100
            print(f"  Efficiency Gain:   {efficiency:+.1f}%")
        
        time.sleep(0.5)  # Brief pause between tests
    
    print("\n📈 Performance Summary:")
    print(f"  Unified avg:    {statistics.mean(unified_times):.3f}s")
    print(f"  Fragmented avg: {statistics.mean(fragmented_times):.3f}s")
    
    if statistics.mean(fragmented_times) > 0:
        overall_efficiency = ((statistics.mean(fragmented_times) - statistics.mean(unified_times)) / statistics.mean(fragmented_times)) * 100
        print(f"  Overall Gain:   {overall_efficiency:+.1f}%")
        
        if overall_efficiency > 0:
            print(f"  🎯 UserAccessService patterns show {overall_efficiency:.1f}% improvement!")
        else:
            print(f"  ⚠️  Fragmented access is {abs(overall_efficiency):.1f}% faster (investigate)")
    
    print("\n✅ Performance validation complete!")

if __name__ == "__main__":
    run_performance_comparison()