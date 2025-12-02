"""Timestamp validation for migration filenames."""

import datetime


def has_valid_timestamp(filename: str) -> bool:
    """
    Validate that filename starts with YYYY-MM-DDTHHMMSS format.

    Validation rules:
    - Minimum length of 17 characters
    - Pattern: YYYY-MM-DDTHHMMSS where Y/M/D/H/M/S are digits
    - Hyphens at positions 4 and 7
    - 'T' at position 10
    - Month: 1-12
    - Day: 1-31 (adjusted for month and leap years)
    - Hour: 0-23
    - Minute: 0-59
    - Second: 0-59

    Args:
        filename: The filename to validate

    Returns:
        True if filename has valid timestamp prefix, False otherwise
    """
    # Check minimum length
    if len(filename) < 17:
        return False

    # Check pattern: YYYY-MM-DDTHHMMSS
    # Positions: 0123456789012345678
    pattern = "0000-00-00T000000"

    for i, c in enumerate(pattern):
        if c == "0":
            # Should be a digit
            if not filename[i].isdigit():
                return False
        else:
            # Should match the delimiter
            if filename[i] != c:
                return False

    # Parse and validate components
    try:
        year = int(filename[0:4])
        month = int(filename[5:7])
        day = int(filename[8:10])
        hour = int(filename[11:13])
        minute = int(filename[13:15])
        second = int(filename[15:17])
    except ValueError:
        return False

    # Validate ranges
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False
    if hour > 23:
        return False
    if minute > 59:
        return False
    if second > 59:
        return False

    # Validate days in month using datetime
    try:
        datetime.date(year, month, day)
    except ValueError:
        return False

    return True


def is_leap_year(year: int) -> bool:
    """Check if a year is a leap year."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
