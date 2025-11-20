"""Command-line interface handler for crypto-ecosystems taxonomy."""

import argparse
import os
import sys
from pathlib import Path

from . import taxonomy
from .download import cmd_download
from .duckify import cmd_duckify
from .tui import cmd_tui


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

  download                 Download parquet files from manifest
      -o, --output DIR     Output directory for downloaded files (required)
      -w, --workers NUM    Number of concurrent downloads (default: 4)
      --retry NUM          Number of retry attempts per file (default: 5)
      --dry-run            Preview downloads without executing
      --resume             Skip files that already exist
      --force              Overwrite existing files

  duckify                  Import parquet files into DuckDB database
      -i, --input DIR      Input directory containing parquet files (required)
      -o, --output FILE    Output DuckDB database file path (required)
      --table-prefix STR   Prefix to add to all table names
      --overwrite          Overwrite database if it exists
      --show-schema        Print table schemas after creation

  tui                      Open an interactive SQL interface to explore Open Dev Data
      --lite               Download only core files for lightweight exploration
      --refresh            Force re-download of cached files
      --clear-cache        Clear cache and exit (doesn't open TUI)
      --db FILE            Path to an existing DuckDB file to open directly

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
    subparsers.add_parser("help", add_help=False)

    # Version command
    subparsers.add_parser("version", add_help=False)

    # Download command
    download_parser = subparsers.add_parser("download", add_help=False)
    download_parser.add_argument(
        "-h", "--help", action="store_true", help="Show help for download"
    )
    download_parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="Output directory for downloaded files",
    )
    download_parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent downloads (default: 4)",
    )
    download_parser.add_argument(
        "--retry",
        type=int,
        default=5,
        help="Number of retry attempts per file (default: 5)",
    )
    download_parser.add_argument(
        "--dry-run", action="store_true", help="Preview downloads without executing"
    )
    download_parser.add_argument(
        "--resume", action="store_true", help="Skip files that already exist"
    )
    download_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing files"
    )

    # Duckify command
    duckify_parser = subparsers.add_parser("duckify", add_help=False)
    duckify_parser.add_argument(
        "-h", "--help", action="store_true", help="Show help for duckify"
    )
    duckify_parser.add_argument(
        "-i",
        "--input-dir",
        type=str,
        required=False,
        dest="input_dir",
        help="Input directory containing parquet files",
    )
    duckify_parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="Output DuckDB database file path",
    )
    duckify_parser.add_argument(
        "--table-prefix", type=str, default="", help="Prefix to add to all table names"
    )
    duckify_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite database if it exists"
    )
    duckify_parser.add_argument(
        "--show-schema", action="store_true", help="Print table schemas after creation"
    )

    # TUI command
    tui_parser = subparsers.add_parser("tui", add_help=False)
    tui_parser.add_argument(
        "-h", "--help", action="store_true", help="Show help for tui"
    )
    tui_parser.add_argument(
        "--lite",
        action="store_true",
        help="Download only core files for lightweight exploration",
    )
    tui_parser.add_argument(
        "--refresh", action="store_true", help="Force re-download of cached files"
    )
    tui_parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache and exit (doesn't open TUI)",
    )
    tui_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to an existing DuckDB file to open directly",
    )

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
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "duckify":
        cmd_duckify(args)
    elif args.command == "tui":
        cmd_tui(args)
    else:
        print_usage()
