"""
Tests for core.usernames.UsernameNormalizer

Comprehensive test suite covering:
- normalize() with various inputs (spaces, underscores, hyphens, unicode)
- canonical() for display-safe formatting
- are_same_user() for direct comparison
- validate() for input validation
"""

import pytest
from core.usernames import UsernameNormalizer


class TestUsernameNormalizerNormalize:
    """Test normalize() method with various inputs"""

    def test_normalize_basic_name(self):
        """Basic normalization should lowercase and strip"""
        assert UsernameNormalizer.normalize("John") == "john"
        assert UsernameNormalizer.normalize("JOHN") == "john"

    def test_normalize_spaces(self):
        """Multiple spaces should be removed in comparison mode"""
        assert UsernameNormalizer.normalize("J O H N") == "john"
        assert UsernameNormalizer.normalize("  John  ") == "john"
        assert UsernameNormalizer.normalize("Jo   hn") == "john"

    def test_normalize_underscores_hyphens(self):
        """Underscores and hyphens should be treated as spaces"""
        assert UsernameNormalizer.normalize("Jo_hn") == "john"
        assert UsernameNormalizer.normalize("Jo-hn") == "john"
        assert UsernameNormalizer.normalize("Jo_hn-Doe") == "johndoe"
        assert UsernameNormalizer.normalize("Jo_hn-Do e") == "johndoe"

    def test_normalize_unicode_spaces(self):
        """Unicode whitespace characters (non-breaking space, etc.) should be normalized"""
        # Non-breaking space (U+00A0)
        assert UsernameNormalizer.normalize("J\u00A0O\u00A0H\u00A0N") == "john"
        # Em space (U+2003)
        assert UsernameNormalizer.normalize("J\u2003O\u2003H\u2003N") == "john"

    def test_normalize_empty_string(self):
        """Empty or None input should return empty string"""
        assert UsernameNormalizer.normalize("") == ""
        assert UsernameNormalizer.normalize(None) == ""
        assert UsernameNormalizer.normalize("   ") == ""
        assert UsernameNormalizer.normalize("\t\n") == ""

    def test_normalize_non_string_input(self):
        """Non-string input should return empty string"""
        assert UsernameNormalizer.normalize(123) == ""
        assert UsernameNormalizer.normalize([]) == ""
        assert UsernameNormalizer.normalize({'name': 'john'}) == ""

    def test_normalize_overly_long_username(self):
        """Usernames exceeding 255 characters should return empty string"""
        long_name = "a" * 256
        assert UsernameNormalizer.normalize(long_name) == ""

    def test_normalize_for_display(self):
        """for_comparison=False should preserve structure but clean spaces"""
        # Note: in for_comparison=False mode, we still lowercase
        # but preserve the separation between parts
        result = UsernameNormalizer.normalize("Jo_hn-Doe", for_comparison=False)
        assert result == "jo hn doe"  # spaces replace underscores/hyphens, collapse multiple spaces

    def test_normalize_real_usernames(self):
        """Test with realistic usernames from the clan"""
        assert UsernameNormalizer.normalize("1 o 3 1 3") == "1o313"
        assert UsernameNormalizer.normalize("Doc Of Med") == "docofmed"
        assert UsernameNormalizer.normalize("Roq_Ashby") == "roqashby"
        assert UsernameNormalizer.normalize("le-chat") == "lechat"


class TestUsernameNormalizerCanonical:
    """Test canonical() method for display formatting"""

    def test_canonical_preserves_case(self):
        """Canonical should preserve original casing"""
        assert UsernameNormalizer.canonical("DocOfMed") == "DocOfMed"
        assert UsernameNormalizer.canonical("JOHN") == "JOHN"
        assert UsernameNormalizer.canonical("john") == "john"

    def test_canonical_normalizes_whitespace(self):
        """Canonical should normalize whitespace but preserve case"""
        assert UsernameNormalizer.canonical("Doc  Of  Med") == "Doc Of Med"
        assert UsernameNormalizer.canonical("  John  ") == "John"

    def test_canonical_unicode_spaces(self):
        """Canonical should handle unicode spaces"""
        assert UsernameNormalizer.canonical("Doc\u00A0Of\u00A0Med") == "Doc Of Med"

    def test_canonical_empty_input(self):
        """Canonical should return empty string for empty input"""
        assert UsernameNormalizer.canonical("") == ""
        assert UsernameNormalizer.canonical(None) == ""
        assert UsernameNormalizer.canonical("   ") == ""

    def test_canonical_non_string_input(self):
        """Canonical should return empty string for non-string input"""
        assert UsernameNormalizer.canonical(123) == ""
        assert UsernameNormalizer.canonical([]) == ""


class TestUsernameNormalizerAreSameUser:
    """Test are_same_user() method for user comparison"""

    def test_are_same_user_exact_match(self):
        """Exact matches should return True"""
        assert UsernameNormalizer.are_same_user("john", "john") is True
        assert UsernameNormalizer.are_same_user("JOHN", "john") is True

    def test_are_same_user_spaces_variation(self):
        """Different spacing should still match"""
        assert UsernameNormalizer.are_same_user("J O H N", "john") is True
        assert UsernameNormalizer.are_same_user("Jo hn", "john") is True

    def test_are_same_user_underscore_hyphen(self):
        """Underscores and hyphens should not affect matching"""
        assert UsernameNormalizer.are_same_user("Jo_hn", "john") is True
        assert UsernameNormalizer.are_same_user("Jo-hn", "john") is True
        assert UsernameNormalizer.are_same_user("Jo_hn-Doe", "johndoe") is True

    def test_are_same_user_unicode_spaces(self):
        """Unicode spaces should be handled"""
        assert UsernameNormalizer.are_same_user("J\u00A0O\u00A0H\u00A0N", "john") is True

    def test_are_same_user_different_users(self):
        """Different users should return False"""
        assert UsernameNormalizer.are_same_user("john", "jane") is False
        assert UsernameNormalizer.are_same_user("docofmed", "roqashby") is False

    def test_are_same_user_empty_handling(self):
        """Empty/None should only match if both empty"""
        assert UsernameNormalizer.are_same_user("", "") is True
        assert UsernameNormalizer.are_same_user(None, None) is True
        assert UsernameNormalizer.are_same_user("john", "") is False
        assert UsernameNormalizer.are_same_user("john", None) is False

    def test_are_same_user_real_examples(self):
        """Real examples from the clan"""
        assert UsernameNormalizer.are_same_user("1 o 3 1 3", "1o313") is True
        assert UsernameNormalizer.are_same_user("Doc Of Med", "docofmed") is True
        assert UsernameNormalizer.are_same_user("Roq_Ashby", "roq ashby") is True


class TestUsernameNormalizerValidate:
    """Test validate() method for input validation"""

    def test_validate_valid_username(self):
        """Valid usernames should pass validation"""
        valid, error = UsernameNormalizer.validate("john")
        assert valid is True
        assert error is None

        valid, error = UsernameNormalizer.validate("Doc Of Med")
        assert valid is True
        assert error is None

    def test_validate_empty_input(self):
        """Empty input should fail"""
        valid, error = UsernameNormalizer.validate("")
        assert valid is False
        assert error is not None

        valid, error = UsernameNormalizer.validate(None)
        assert valid is False
        assert error is not None

    def test_validate_overly_long(self):
        """Usernames exceeding 255 characters should fail"""
        long_name = "a" * 256
        valid, error = UsernameNormalizer.validate(long_name)
        assert valid is False
        assert "too long" in error.lower()

    def test_validate_non_string_input(self):
        """Non-string input should fail"""
        valid, error = UsernameNormalizer.validate(123)
        assert valid is False
        assert "must be string" in error.lower()

    def test_validate_no_alphanumeric(self):
        """Usernames with no letters or digits should fail"""
        valid, error = UsernameNormalizer.validate("___---")
        assert valid is False
        assert "at least one letter" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
