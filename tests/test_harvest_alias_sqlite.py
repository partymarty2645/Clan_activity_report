import sqlite3

from scripts.harvest_sqlite import resolve_member_id_sqlite


def _setup_in_memory_db():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE clan_members (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE)"
    )
    cursor.execute(
        "CREATE TABLE player_name_aliases (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, normalized_name TEXT UNIQUE)"
    )
    return conn, cursor


def test_resolve_member_id_prefers_alias_lookup():
    conn, cursor = _setup_in_memory_db()
    try:
        cursor.execute("INSERT INTO clan_members (username) VALUES ('currentname')")
        member_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO player_name_aliases (member_id, normalized_name) VALUES (?, ?)",
            (member_id, "oldname"),
        )

        resolved = resolve_member_id_sqlite(cursor, "oldname")
        assert resolved == member_id
    finally:
        conn.close()


def test_resolve_member_id_falls_back_to_clan_members():
    conn, cursor = _setup_in_memory_db()
    try:
        cursor.execute("INSERT INTO clan_members (username) VALUES ('uniqueuser')")
        member_id = cursor.lastrowid

        resolved = resolve_member_id_sqlite(cursor, "uniqueuser")
        assert resolved == member_id
    finally:
        conn.close()


def test_resolve_member_id_returns_none_when_missing():
    conn, cursor = _setup_in_memory_db()
    try:
        resolved = resolve_member_id_sqlite(cursor, "nonexistent")
        assert resolved is None
    finally:
        conn.close()
