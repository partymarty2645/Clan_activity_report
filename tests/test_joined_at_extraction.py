import datetime
from scripts.harvest_sqlite import _extract_joined_at


def test_extract_joined_at_accepts_camel_case():
    m = {"joinedAt": "2025-03-01T10:20:30.000Z"}
    iso = _extract_joined_at(m)
    assert iso is not None
    # Should be parseable and UTC
    dt = datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))
    assert dt.tzinfo is not None


def test_extract_joined_at_accepts_snake_case():
    m = {"joined_at": "2025-03-02T11:22:33Z"}
    iso = _extract_joined_at(m)
    assert iso is not None
    dt = datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))
    assert dt.tzinfo is not None


def test_extract_joined_at_handles_missing():
    m = {}
    assert _extract_joined_at(m) is None


def test_extract_joined_at_handles_bad_format():
    m = {"joinedAt": "not-a-date"}
    assert _extract_joined_at(m) is None
