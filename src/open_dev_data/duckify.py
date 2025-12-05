"""Duckify subcommand for importing parquet files into DuckDB"""

import argparse
import re
import sys
from pathlib import Path

import duckdb
from rich.console import Console
from rich.table import Table

console = Console()


def sanitize_table_name(filename: str, prefix: str = "") -> str:
    """Convert filename to valid SQL table name."""
    # Remove .parquet extension
    name = filename.replace(".parquet", "")

    # Replace hyphens with underscores
    name = name.replace("-", "_")

    # Remove any characters that aren't alphanumeric or underscore
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)

    # Ensure doesn't start with a number
    if name and name[0].isdigit():
        name = f"_{name}"

    # Add prefix if specified
    if prefix:
        name = f"{prefix}{name}"

    return name


def import_parquet_to_duckdb(
    parquet_path: Path, table_name: str, conn: duckdb.DuckDBPyConnection
) -> bool:
    """Import a single parquet file into DuckDB as a table."""
    try:
        # Create table from parquet file
        conn.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{parquet_path}')"
        )
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to import {parquet_path.name}: {e}[/red]")
        return False


def get_table_info(
    table_name: str, conn: duckdb.DuckDBPyConnection
) -> tuple[list, int]:
    """Get table schema and row count."""
    try:
        # Get schema
        schema = conn.execute(f"DESCRIBE {table_name}").fetchall()

        # Get row count
        count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        count = count_result[0] if count_result else 0

        return schema, count
    except Exception:
        return [], 0


def cmd_duckify(args: argparse.Namespace) -> None:
    """Import parquet files into DuckDB database"""

    input_path = Path(args.input_dir)
    output_path = Path(args.output)

    # Validate input directory contains parquet files
    parquet_files = list(input_path.glob("*.parquet"))
    if not parquet_files:
        console.print(f"[red]Error: No parquet files found in {args.input_dir}[/red]")
        sys.exit(1)

    # Check if database already exists
    if output_path.exists() and not args.overwrite:
        console.print(
            f"[red]Error: Database {args.output} already exists. Use --overwrite to replace it.[/red]"
        )
        sys.exit(1)

    # Remove existing database if overwriting
    if output_path.exists() and args.overwrite:
        output_path.unlink()
        console.print(f"[yellow]Removed existing database: {args.output}[/yellow]")

    console.print(f"[cyan]Creating DuckDB database: {args.output}[/cyan]")
    console.print(f"[cyan]Found {len(parquet_files)} parquet files[/cyan]\n")

    # Connect to DuckDB
    conn = duckdb.connect(str(output_path))

    # Import each parquet file
    successful = 0
    failed = 0
    table_info_list = []

    for parquet_file in parquet_files:
        table_name = sanitize_table_name(parquet_file.name, args.table_prefix)

        console.print(f"[cyan]Creating table: {table_name}[/cyan]")

        if import_parquet_to_duckdb(parquet_file, table_name, conn):
            successful += 1
            console.print(
                f"[green]✓ Imported: {parquet_file.name} → {table_name}[/green]"
            )

            # Get table info for summary
            if args.show_schema:
                schema, count = get_table_info(table_name, conn)
                table_info_list.append((table_name, schema, count))
        else:
            failed += 1

    # Display schemas if requested
    if args.show_schema and table_info_list:
        console.print("\n[bold cyan]Table Schemas:[/bold cyan]\n")

        for table_name, schema, count in table_info_list:
            console.print(f"[bold]{table_name}[/bold] ({count:,} rows)")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Column", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Null", style="yellow")

            for col in schema:
                # Schema format: (column_name, column_type, null, key, default, extra)
                col_name = col[0]
                col_type = col[1]
                col_null = "YES" if col[2] == "YES" else "NO"
                table.add_row(col_name, col_type, col_null)

            console.print(table)
            console.print()

    # Close connection
    conn.close()

    # Get database file size
    db_size = output_path.stat().st_size
    db_size_mb = db_size / (1024 * 1024)

    # Display summary
    console.print("\n[bold]Import Summary:[/bold]")
    console.print(f"  [green]Successful: {successful}[/green]")
    if failed > 0:
        console.print(f"  [red]Failed: {failed}[/red]")
    console.print(f"  [cyan]Total: {len(parquet_files)}[/cyan]")
    console.print(f"  [cyan]Database size: {db_size_mb:.2f} MB[/cyan]")
    console.print(f"\n[green]Database created: {output_path.absolute()}[/green]")

    # Exit with error code if any imports failed
    if failed > 0:
        raise SystemExit(1)
