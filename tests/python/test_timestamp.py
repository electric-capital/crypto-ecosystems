"""Unit tests for timestamp validation."""

import unittest
from src.timestamp import has_valid_timestamp, is_leap_year


class TestTimestamp(unittest.TestCase):
    """Test timestamp validation functionality."""

    def test_valid_timestamps(self):
        """Test that valid timestamps are recognized."""
        self.assertTrue(has_valid_timestamp("2024-01-16T020000_test.txt"))
        self.assertTrue(has_valid_timestamp("2024-02-29T235959_leap.txt"))
        self.assertTrue(has_valid_timestamp("2024-12-31T000000"))

    def test_invalid_month(self):
        """Test that invalid months are rejected."""
        self.assertFalse(has_valid_timestamp("2024-13-01T000000_test.txt"))
        self.assertFalse(has_valid_timestamp("2024-00-01T000000_test.txt"))

    def test_invalid_day(self):
        """Test that invalid days are rejected."""
        self.assertFalse(has_valid_timestamp("2024-04-31T000000_test.txt"))
        self.assertFalse(has_valid_timestamp("2024-01-32T000000_test.txt"))
        self.assertFalse(has_valid_timestamp("2024-01-00T000000_test.txt"))

    def test_invalid_leap_year(self):
        """Test that leap year validation works."""
        self.assertFalse(has_valid_timestamp("2023-02-29T000000_test.txt"))
        self.assertTrue(has_valid_timestamp("2024-02-29T000000_test.txt"))
        self.assertTrue(has_valid_timestamp("2000-02-29T000000_test.txt"))
        self.assertFalse(has_valid_timestamp("1900-02-29T000000_test.txt"))

    def test_invalid_time(self):
        """Test that invalid times are rejected."""
        self.assertFalse(has_valid_timestamp("2024-01-16T240000_test.txt"))
        self.assertFalse(has_valid_timestamp("2024-01-16T006000_test.txt"))
        self.assertFalse(has_valid_timestamp("2024-01-16T000060_test.txt"))

    def test_invalid_format(self):
        """Test that incorrectly formatted timestamps are rejected."""
        self.assertFalse(has_valid_timestamp("not_a_timestamp.txt"))
        self.assertFalse(has_valid_timestamp("2024-01-16_no_time.txt"))
        self.assertFalse(has_valid_timestamp("20240116T020000_test.txt"))
        self.assertFalse(has_valid_timestamp("2024-01-16-020000_test.txt"))

    def test_too_short(self):
        """Test that short filenames are rejected."""
        self.assertFalse(has_valid_timestamp("2024-01-16"))
        self.assertFalse(has_valid_timestamp(""))

    def test_leap_year(self):
        """Test leap year calculation."""
        self.assertTrue(is_leap_year(2024))
        self.assertTrue(is_leap_year(2000))
        self.assertFalse(is_leap_year(2023))
        self.assertFalse(is_leap_year(1900))


if __name__ == "__main__":
    unittest.main()
