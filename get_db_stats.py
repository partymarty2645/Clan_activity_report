import sqlite3

def get_database_stats():
    """Get total counts of messages and snapshots from the database."""
    
    conn = sqlite3.connect('clan_data.db')
    cursor = conn.cursor()
    
    try:
        # Count total Discord messages
        cursor.execute("SELECT COUNT(*) FROM discord_messages")
        total_messages = cursor.fetchone()[0]
        
        # Count total WOM snapshots
        cursor.execute("SELECT COUNT(*) FROM wom_snapshots") 
        total_snapshots = cursor.fetchone()[0]
        
        # Count unique users who sent messages
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM discord_messages")
        unique_message_users = cursor.fetchone()[0]
        
        # Count unique players with snapshots
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM wom_snapshots")
        unique_snapshot_players = cursor.fetchone()[0]
        
        # Count total clan members
        cursor.execute("SELECT COUNT(*) FROM clan_members")
        total_members = cursor.fetchone()[0]
        
        print("📊 Database Statistics:")
        print("=" * 40)
        print(f"💬 Total Discord Messages: {total_messages:,}")
        print(f"👥 Unique Message Senders: {unique_message_users:,}")
        print(f"📈 Total WOM Snapshots: {total_snapshots:,}")  
        print(f"🎮 Unique Players with Snapshots: {unique_snapshot_players:,}")
        print(f"👑 Total Clan Members: {total_members:,}")
        print("=" * 40)
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    get_database_stats()