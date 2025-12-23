import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, ClanMember, PlayerNameAlias
from services.identity_service import (
    upsert_alias,
    resolve_member_by_name,
    sync_wom_name_changes,
    ensure_member_alias,
)


@pytest.fixture()
def db_session():
    # Use in-memory SQLite for isolation
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_alias_upsert_and_resolve(db_session):
    # Create a member
    m = ClanMember(username="DocOfMed")
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    # Ensure primary alias present
    ensure_member_alias(db_session, m, source="game")

    # Add a display variant alias
    upsert_alias(db_session, m.id, "Doc Of Med", source="discord", is_current=True)

    # Should resolve via any variant
    assert resolve_member_by_name(db_session, "docofmed") == m.id
    assert resolve_member_by_name(db_session, "Doc Of Med") == m.id
    assert resolve_member_by_name(db_session, "Doc  Of   Med") == m.id

    # Normalized name should be unique
    alias = db_session.query(PlayerNameAlias).filter(PlayerNameAlias.normalized_name == "docofmed").one()
    assert alias.member_id == m.id
    assert alias.is_current is True


def test_sync_wom_name_changes_monkeypatch(db_session, monkeypatch):
    # Create a member
    m = ClanMember(username="Roq_Ashby")
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    # Fake WOM payload
    fake_changes = [
        {"oldName": "roq_ashby", "newName": "Roq Ashby", "createdAt": "2025-05-01T12:00:00Z"},
        {"oldName": "roqa_shby", "newName": "roq ashby", "createdAt": "2025-06-01T12:00:00Z"},
    ]

    def _fake_fetch(username: str):
        return fake_changes

    from services import identity_service as ids
    monkeypatch.setattr(ids, "_fetch_wom_name_changes_by_username", _fake_fetch)

    # Run sync
    updated = sync_wom_name_changes(db_session, m.id, m.username)
    assert updated >= 2

    # Aliases should be present and resolve
    assert resolve_member_by_name(db_session, "roq_ashby") == m.id
    assert resolve_member_by_name(db_session, "Roq Ashby") == m.id
    assert resolve_member_by_name(db_session, "roq ashby") == m.id
