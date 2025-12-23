import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, UTC

from database.models import Base, DiscordMessage, WOMSnapshot, ClanMember, PlayerNameAlias
from core.usernames import UsernameNormalizer
from services.identity_service import upsert_alias, resolve_member_by_name


@pytest.fixture()
def db():
    """Provides a fresh in-memory test database for each test."""
    # Use in-memory SQLite for isolation
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestDiscordIngestionWithAliases:
    """Tests for Discord message ingestion with alias resolution."""
    
    def test_discord_message_resolves_member_id_via_alias(self, db: Session):
        """
        Test that when a Discord message is saved with a normalized author_name,
        the member_id is resolved correctly via alias lookup.
        """
        # Setup: Create a ClanMember
        member = ClanMember(username="testplayer", role="member")
        db.add(member)
        db.commit()
        member_id = member.id  # Store ID after commit
        
        # Setup: Create alias for an old name
        old_name = "test player"  # Has space, will normalize same as 'testplayer'
        upsert_alias(db, member_id, old_name, source="discord", is_current=False)
        
        # Action: Create Discord message with normalized old name
        normalized_old = UsernameNormalizer.normalize(old_name)
        
        # Verify: resolve_member_by_name should find the member
        resolved_id = resolve_member_by_name(db, normalized_old)
        assert resolved_id == member_id, "Should resolve old name to member_id via alias"
        
        # Simulate saving Discord message with resolved user_id
        msg = DiscordMessage(
            id=123456789,
            user_id=resolved_id,  # Resolved via alias
            author_id=999,
            author_name=normalized_old,
            content="Hello clan!",
            channel_id=111,
            channel_name="general",
            guild_id=222,
            guild_name="Clan",
            created_at=datetime.now(UTC)
        )
        db.add(msg)
        db.commit()
        
        # Verify: Message is saved with correct user_id
        saved_msg = db.query(DiscordMessage).filter(DiscordMessage.id == 123456789).one()
        assert saved_msg.user_id == member_id  # Compare actual values


class TestWOMSnapshotIngestionWithAliases:
    """Tests for WOM snapshot ingestion with alias resolution."""
    
    def test_wom_snapshot_resolves_member_id_via_alias(self, db: Session):
        """
        Test that when a WOM snapshot is saved with a normalized username,
        the user_id is resolved correctly via alias lookup.
        """
        # Setup: Create a ClanMember with one name
        member = ClanMember(username="runescaper", role="member")
        db.add(member)
        db.commit()
        member_id = member.id  # Store ID after commit
        
        # Setup: Create alias for a previous name
        prev_name = "Rune Scraper"  # Different casing and spacing
        upsert_alias(db, member_id, prev_name, source="wom", is_current=False)
        
        # Action: Create WOM snapshot with normalized previous name
        normalized_prev = UsernameNormalizer.normalize(prev_name)
        
        # Verify: resolve_member_by_name should find the member
        resolved_id = resolve_member_by_name(db, normalized_prev)
        assert resolved_id == member_id, "Should resolve previous name to member_id via alias"
        
        # Simulate saving WOM snapshot with resolved user_id
        snapshot = WOMSnapshot(
            user_id=resolved_id,  # Resolved via alias
            username=normalized_prev,
            timestamp=datetime.now(UTC),
            total_xp=1000000,
            total_boss_kills=50,
            ehp=70.5,
            ehb=30.2,
            raw_data='{"test": "data"}'
        )
        db.add(snapshot)
        db.commit()
        
        # Verify: Snapshot is saved with correct user_id
        saved_snap = db.query(WOMSnapshot).filter(WOMSnapshot.username == normalized_prev).one()
        assert saved_snap.user_id == member_id  # Compare actual values


class TestMultipleAliasResolution:
    """Tests for handling players with multiple name changes."""
    
    def test_player_with_multiple_name_changes(self, db: Session):
        """
        Test a player who has changed their name multiple times.
        All old names should resolve to the same member_id.
        """
        # Setup: Create member
        member = ClanMember(username="currentname", role="member")
        db.add(member)
        db.commit()
        member_id = member.id  # Store ID after commit
        
        # Setup: Create multiple aliases for different past names
        past_names = [
            ("old name one", False),
            ("old name two", False),
            ("old name three", False),
            ("currentname", True),  # Current name
        ]
        
        for name, is_current in past_names:
            upsert_alias(db, member_id, name, source="wom", is_current=is_current)
        
        # Action: Try to resolve each past name
        for name, _ in past_names:
            normalized = UsernameNormalizer.normalize(name)
            resolved_id = resolve_member_by_name(db, normalized)
            
            # Verify: All names should resolve to same member
            assert resolved_id == member_id, f"Name '{name}' should resolve to member {member_id}"
        
        # Verify: All aliases are marked with correct is_current
        current_alias = db.query(PlayerNameAlias).filter(
            PlayerNameAlias.member_id == member_id,
            PlayerNameAlias.is_current == True
        ).one()
        assert UsernameNormalizer.normalize(str(current_alias.canonical_name)) == \
               UsernameNormalizer.normalize("currentname")


class TestAliasLookupWithNoMatch:
    """Tests for handling cases where an alias is not found."""
    
    def test_resolve_unknown_player_returns_none(self, db: Session):
        """
        Test that resolving a name with no alias returns None.
        """
        # Action: Try to resolve a name that doesn't exist
        resolved_id = resolve_member_by_name(db, "unknownplayer")
        
        # Verify: Should return None
        assert resolved_id is None, "Unknown name should return None"
    
    def test_discord_message_with_unresolved_author(self, db: Session):
        """
        Test that a Discord message can be saved even if author_name doesn't resolve.
        In practice, user_id would be None and logged as warning.
        """
        # Action: Create message with no alias resolution
        msg = DiscordMessage(
            id=987654321,
            user_id=None,  # No member found
            author_id=888,
            author_name=UsernameNormalizer.normalize("newplayer"),
            content="First message",
            channel_id=111,
            channel_name="general",
            guild_id=222,
            guild_name="Clan",
            created_at=datetime.now(UTC)
        )
        db.add(msg)
        db.commit()
        
        # Verify: Message is saved with user_id=None
        saved_msg = db.query(DiscordMessage).filter(DiscordMessage.id == 987654321).one()
        assert saved_msg.user_id is None, "Message should save with NULL user_id when alias not found"
