"""Command-line interface handler for crypto-ecosystems taxonomy."""

import sys
import os
import argparse
from typing import Optional

from . import taxonomy


def default_migrations_path() -> str:
    """Get the default migrations directory path."""
    return os.path.realpath("migrations")


def print_usage() -> None:
    """Print usage information."""
    print("""Usage: ce [-h | --help] <command> [<args>]

Commands:
  validate                 Validate all of the migrations
      -r, --root DIR       The direction containing the migrations file (default ./migrations)

  export                   Export the taxonomy to a json file
      -r, --root DIR       The direction containing the migrations file (default ./migrations)
      -e, --ecosystem STR  The name of an ecosystem if you only want to export one
      -m, --max-date STR   The maximum date to run migrations until.
                           One can export the taxonomy state at specific past dates with this param.
      <output>             The output file

  help                     Show this help message
  version                  Show program version
""")


def print_version() -> None:
    """Print version information."""
    print("2.0")


def cmd_validate(args: argparse.Namespace) -> None:
    """Execute the validate command."""
    root = args.root if args.root else default_migrations_path()

    tax = taxonomy.Taxonomy()
    try:
        tax.load(root, None)
    except taxonomy.ValidationFailed:
        sys.exit(1)

    stats = tax.stats()

    # Print statistics with colored output
    magenta = "\x1b[35m"
    reset = "\x1b[0m"

    print(f"{magenta}┃{reset} {stats.migration_count:<6} Migrations")
    print(f"{magenta}┃{reset} {stats.eco_count:<6} Ecosystems")
    print(f"{magenta}┃{reset} {stats.repo_count:<6} Repos")
    print(f"{magenta}┃{reset} {stats.tag_count:<6} Tags")


def cmd_export(args: argparse.Namespace) -> None:
    """Execute the export command."""
    if not args.output:
        print("Please specify an output path for export\n", file=sys.stderr)
        print_usage()
        sys.exit(1)

    root = args.root if args.root else default_migrations_path()

    tax = taxonomy.Taxonomy()
    try:
        tax.load(root, args.max_date)
    except taxonomy.ValidationFailed:
        sys.exit(1)

    try:
        tax.export_json(args.output, args.ecosystem)
    except taxonomy.InvalidEcosystem as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Crypto Ecosystems Taxonomy Tool", add_help=False
    )

    # Add global help
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", add_help=False)
    validate_parser.add_argument(
        "-h", "--help", action="store_true", help="Show help for validate"
    )
    validate_parser.add_argument(
        "-r", "--root", type=str, help="Directory containing migrations"
    )

    # Export command
    export_parser = subparsers.add_parser("export", add_help=False)
    export_parser.add_argument(
        "-h", "--help", action="store_true", help="Show help for export"
    )
    export_parser.add_argument(
        "-r", "--root", type=str, help="Directory containing migrations"
    )
    export_parser.add_argument(
        "-e", "--ecosystem", type=str, help="Export only this ecosystem"
    )
    export_parser.add_argument(
        "-m",
        "--max-date",
        type=str,
        dest="max_date",
        help="Maximum date for migrations",
    )
    export_parser.add_argument("output", nargs="?", help="Output file path")

    # Help command
    help_parser = subparsers.add_parser("help", add_help=False)

    # Version command
    version_parser = subparsers.add_parser("version", add_help=False)

    # Parse arguments
    if len(sys.argv) < 2:
        print_usage()
        return

    args = parser.parse_args()

    # Handle global help
    if args.help or args.command == "help":
        print_usage()
        return

    # Handle version
    if args.command == "version":
        print_version()
        return

    # Handle command-specific help
    if hasattr(args, "help") and args.help:
        print_usage()
        return

    # Execute commands
    if args.command == "validate":
        cmd_validate(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        print_usage()
