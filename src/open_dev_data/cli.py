#!/usr/bin/env python3
"""Convenience script for running crypto-ecosystems taxonomy commands."""

if __name__ == "__main__":
    import os
    import sys

    # Add parent directory to path so imports work when run directly
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

    from src.open_dev_data.commands import main

    main()
