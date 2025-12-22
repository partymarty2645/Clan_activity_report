"""
Database Integrity Tests
========================
Tests to verify data consistency and referential integrity.
These tests help catch migration issues early.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import WOMSnapshot, DiscordMessage, BossSnapshot, ClanMember, Base


@pytest.fixture
def db_session():
    """Create a fresh test database session."""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestDatabaseIntegrity:
    """Verify no orphaned or inconsistent records exist."""

    def test_database_initialization(self, db_session):
        """Verify database initializes with correct schema."""
        # This is a smoke test - just verify we can query without errors
        assert db_session.query(ClanMember).count() == 0
        assert db_session.query(WOMSnapshot).count() == 0
        assert db_session.query(DiscordMessage).count() == 0
        assert db_session.query(BossSnapshot).count() == 0

    def test_no_orphaned_wom_snapshots(self, db_session):
        """
        Verify all WOM snapshots have corresponding users (either by id or username).
        This helps catch missing FK relationships.
        """
        # Create test data
        member = ClanMember(username="testuser", role="member", id=1)
        db_session.add(member)
        db_session.commit()
        
        # Add snapshot with user_id
        snapshot = WOMSnapshot(
            user_id=1,
            username="testuser",
            timestamp=datetime.now(),
            total_xp=1000,
            total_boss_kills=10
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Verify snapshot references valid user
        snapshots = db_session.query(WOMSnapshot).all()
        for snap in snapshots:
            if snap.user_id:
                member = db_session.query(ClanMember).filter_by(id=snap.user_id).first()
                assert member is not None, f"WOMSnapshot {snap.id} references non-existent user_id {snap.user_id}"

    def test_no_orphaned_boss_snapshots(self, db_session):
        """
        Verify all boss snapshots reference valid WOM snapshots.
        """
        # Create test data
        member = ClanMember(username="testuser", role="member", id=1)
        db_session.add(member)
        
        snapshot = WOMSnapshot(
            user_id=1,
            username="testuser",
            timestamp=datetime.now(),
            total_xp=1000,
            total_boss_kills=10
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Add boss snapshot
        boss = BossSnapshot(
            wom_snapshot_id=snapshot.id,
            snapshot_id=snapshot.id,
            boss_name="Vorkath",
            kills=50,
            rank=100
        )
        db_session.add(boss)
        db_session.commit()
        
        # Verify boss references valid snapshot
        bosses = db_session.query(BossSnapshot).all()
        for boss in bosses:
            if boss.wom_snapshot_id:
                snap = db_session.query(WOMSnapshot).filter_by(id=boss.wom_snapshot_id).first()
                assert snap is not None, f"BossSnapshot {boss.id} references non-existent wom_snapshot_id {boss.wom_snapshot_id}"

    def test_no_orphaned_discord_messages(self, db_session):
        """
        Verify all Discord messages have user references.
        """
        # Create test member
        member = ClanMember(username="testuser", role="member", id=1)
        db_session.add(member)
        db_session.commit()
        
        # Add message with user_id
        message = DiscordMessage(
            id=123456789,
            user_id=1,
            author_id=987654321,
            author_name="testuser",
            content="Hello world",
            channel_id=111,
            channel_name="general",
            guild_id=222,
            guild_name="Clan",
            created_at=datetime.now()
        )
        db_session.add(message)
        db_session.commit()
        
        # Verify message references valid user
        messages = db_session.query(DiscordMessage).all()
        for msg in messages:
            if msg.user_id:
                member = db_session.query(ClanMember).filter_by(id=msg.user_id).first()
                assert member is not None, f"DiscordMessage {msg.id} references non-existent user_id {msg.user_id}"

    def test_username_uniqueness(self, db_session):
        """
        Verify usernames are unique in clan_members.
        """
        # Add two members with different usernames
        m1 = ClanMember(username="user1", role="member", id=1)
        m2 = ClanMember(username="user2", role="member", id=2)
        db_session.add_all([m1, m2])
        db_session.commit()
        
        # Verify both exist
        assert db_session.query(ClanMember).count() == 2
        
        # Check they have different usernames
        usernames = {m.username for m in db_session.query(ClanMember).all()}
        assert len(usernames) == 2

    def test_model_relationships(self, db_session):
        """
        Verify ORM relationships work correctly.
        """
        # Create full hierarchy
        member = ClanMember(username="testuser", role="member", id=1)
        db_session.add(member)
        db_session.commit()
        
        snapshot = WOMSnapshot(
            user_id=1,
            username="testuser",
            timestamp=datetime.now(),
            total_xp=5000,
            total_boss_kills=20
        )
        db_session.add(snapshot)
        db_session.commit()
        
        boss1 = BossSnapshot(
            wom_snapshot_id=snapshot.id,
            snapshot_id=snapshot.id,
            boss_name="Zulrah",
            kills=100,
            rank=50
        )
        boss2 = BossSnapshot(
            wom_snapshot_id=snapshot.id,
            snapshot_id=snapshot.id,
            boss_name="Vorkath",
            kills=75,
            rank=75
        )
        db_session.add_all([boss1, boss2])
        db_session.commit()
        
        # Verify data relationships
        assert db_session.query(BossSnapshot).filter_by(wom_snapshot_id=snapshot.id).count() == 2
        assert db_session.query(WOMSnapshot).filter_by(user_id=1).count() == 1
