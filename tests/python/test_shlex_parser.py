"""Unit tests for shell-like lexer."""

import unittest
from src.shlex_parser import split


class TestShlexParser(unittest.TestCase):
    """Test shell-like lexer functionality."""

    def test_basic_tokenization(self):
        """Test basic whitespace-separated tokenization."""
        tokens = split("hello world test")
        self.assertEqual(["hello", "world", "test"], tokens)

    def test_quoted_strings(self):
        """Test quoted string handling."""
        tokens = split("command \"quoted string\" 'single'")
        self.assertEqual(["command", "quoted string", "single"], tokens)

    def test_escaped_characters(self):
        """Test escape sequence handling."""
        tokens = split('escaped\\ space "quoted\\"quote"')
        self.assertEqual(["escaped space", 'quoted"quote'], tokens)

    def test_unterminated_quote(self):
        """Test that unterminated quotes raise an error."""
        with self.assertRaises(ValueError):
            split('"unterminated')

    def test_internal_quotes(self):
        """Test quotes within quoted strings."""
        tokens = split('repadd "Mckee\'s Rocks" https://blah.com')
        self.assertEqual(["repadd", "Mckee's Rocks", "https://blah.com"], tokens)

    def test_empty_string(self):
        """Test empty string returns empty list."""
        tokens = split("")
        self.assertEqual([], tokens)

    def test_whitespace_only(self):
        """Test whitespace-only string returns empty list."""
        tokens = split("   \t  \n  ")
        self.assertEqual([], tokens)

    def test_multiple_spaces(self):
        """Test multiple spaces between tokens."""
        tokens = split("hello    world")
        self.assertEqual(["hello", "world"], tokens)


if __name__ == "__main__":
    unittest.main()
