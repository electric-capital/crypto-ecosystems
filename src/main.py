#!/usr/bin/env python3
"""Main entry point for crypto-ecosystems taxonomy tool."""

import sys
from src.commands import main


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
