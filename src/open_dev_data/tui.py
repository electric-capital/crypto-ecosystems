"""TUI subcommand for interactive SQL exploration with cached data"""

import argparse
import asyncio
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
import duckdb
from harlequin import Harlequin
from harlequin.plugins import load_adapter_plugins
from platformdirs import user_cache_dir
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .download import compute_blake3, download_file, fetch_manifest
from .duckify import import_parquet_to_duckdb, sanitize_table_name

console = Console()

# Lite dataset files to download
LITE_FILES = [
    "eco_mads.parquet",
    "ecosystems_repos.parquet",
    "ecosystems.parquet",
    "repos.parquet",
]


def get_cache_dir() -> Path:
    """Get the cache directory for open-dev-data."""
    cache_dir = Path(user_cache_dir("open-dev-data", "electric-capital"))
    return cache_dir


def get_metadata_path() -> Path:
    """Get the metadata file path."""
    return get_cache_dir() / "metadata.json"


def load_metadata() -> Dict[str, Any]:
    """Load metadata from cache directory."""
    metadata_path = get_metadata_path()
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_metadata(metadata: Dict[str, Any]) -> None:
    """Save metadata to cache directory."""
    metadata_path = get_metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


async def validate_cache(files_to_check: List[str]) -> tuple[bool, List[str], str]:
    """Validate cached files against remote checksums.

    Returns:
        (all_valid, files_to_download, version): Tuple of validity, files to download, and version
    """
    cache_dir = get_cache_dir()
    parquet_dir = cache_dir / "parquet"

    # Fetch manifest to get version and resource info
    try:
        manifest = await fetch_manifest()
        version = manifest["dataset"]["version"]
        resources_by_name = {
            r["path"].split("/")[-1]: r
            for r in manifest.get("dataset", {}).get("resources", [])
        }
    except Exception:
        # If manifest fetch fails, re-download all
        return False, files_to_check, ""

    # Check version-specific directory
    version_dir = parquet_dir / version
    if not version_dir.exists():
        return False, files_to_check, version

    metadata = load_metadata()
    files_to_download = []

    # Check each file
    for filename in files_to_check:
        local_path = version_dir / filename

        # Check if file exists locally
        if not local_path.exists():
            files_to_download.append(filename)
            continue

        # Get resource info from manifest
        resource = resources_by_name.get(filename)
        if not resource:
            files_to_download.append(filename)
            continue

        # Get expected size and blake3 from manifest
        expected_size = resource.get("size_bytes", 0)
        expected_b3sum = resource.get("b3sum", None)

        # Check size first
        local_size = local_path.stat().st_size
        if expected_size > 0 and local_size != expected_size:
            files_to_download.append(filename)
            continue

        # If size matches, check blake3 if available
        if expected_b3sum:
            local_b3sum = compute_blake3(local_path)
            if local_b3sum != expected_b3sum:
                files_to_download.append(filename)
                continue

    all_valid = len(files_to_download) == 0
    return all_valid, files_to_download, version


async def download_lite_dataset(files_to_download: List[str], version: str) -> bool:
    """Download lite dataset files with progress display.

    Args:
        files_to_download: List of filenames to download
        version: Version string for creating versioned subfolder

    Returns:
        True if all downloads succeeded, False otherwise
    """
    cache_dir = get_cache_dir()
    parquet_dir = cache_dir / "parquet"
    version_dir = parquet_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)

    # Fetch manifest
    try:
        manifest = await fetch_manifest()
    except Exception as e:
        console.print(f"[red]✗ Failed to fetch manifest: {e}[/red]")
        return False

    # Filter resources to only lite files
    resources_by_name = {
        r["path"].split("/")[-1]: r
        for r in manifest.get("dataset", {}).get("resources", [])
    }

    resources_to_download = []
    for filename in files_to_download:
        if filename in resources_by_name:
            resources_to_download.append(resources_by_name[filename])

    if not resources_to_download:
        console.print("[yellow]No files to download[/yellow]")
        return True

    # Create progress displays
    overall_progress = Progress(
        TextColumn("[bold cyan]{task.description}", justify="left"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
    )

    file_progress = Progress(
        TextColumn("[bold blue]{task.description}", justify="left"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
    )

    # Create panel with progress
    title_panel = Panel(
        "[bold cyan]Open Dev Data[/bold cyan]\n[dim]Downloading Lite Dataset[/dim]",
        border_style="cyan",
    )

    progress_group = Group(title_panel, overall_progress, file_progress)

    # Create TCP connector with keepalive
    connector = aiohttp.TCPConnector(
        limit=2,
        limit_per_host=2,
        ttl_dns_cache=300,
        keepalive_timeout=90,
        force_close=False,
    )

    # Track download results
    completed_files = []
    failed_files = []
    completed_count = {"value": 0}

    # Start download with live display
    with Live(progress_group, console=console, refresh_per_second=10):
        overall_task = overall_progress.add_task(
            f"Overall: 0/{len(resources_to_download)} files",
            total=len(resources_to_download),
        )

        def log_callback(filename: str, success: bool):
            completed_count["value"] += 1
            overall_progress.advance(overall_task, 1)
            overall_progress.update(
                overall_task,
                description=f"Overall: {completed_count['value']}/{len(resources_to_download)} files",
            )
            if success:
                completed_files.append(filename)
                console.print(f"[green]✓ {filename}[/green]")
            else:
                failed_files.append(filename)
                console.print(f"[red]✗ {filename}[/red]")

        semaphore = asyncio.Semaphore(2)  # Limit to 2 concurrent downloads

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for resource in resources_to_download:
                filename = resource["path"].split("/")[-1]
                url = resource["path"]
                if not url.startswith("http"):
                    url = f"https://data.opendevdata.org{url}"

                output_path = version_dir / filename
                expected_b3sum = resource.get("b3sum", None)

                task = download_file(
                    session=session,
                    url=url,
                    output_path=output_path,
                    progress=file_progress,
                    semaphore=semaphore,
                    expected_b3sum=expected_b3sum,
                    retry_count=5,
                    log_callback=log_callback,
                )
                tasks.append(task)

            # Wait for all downloads
            results = await asyncio.gather(*tasks, return_exceptions=True)

    # Save metadata
    metadata = {
        "version": version,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "files": {},
    }

    for filename in completed_files:
        file_path = version_dir / filename
        if file_path.exists():
            metadata["files"][filename] = {
                "size": file_path.stat().st_size,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }

    save_metadata(metadata)

    # Check if all downloads succeeded
    if failed_files:
        console.print(f"\n[red]✗ Failed to download {len(failed_files)} file(s)[/red]")
        return False

    console.print(f"\n[green]✓ Downloaded {len(completed_files)} file(s)[/green]")
    return True


def import_to_duckdb(version: str) -> bool:
    """Import cached parquet files into DuckDB.

    Args:
        version: Version string for the dataset

    Returns:
        True if import succeeded, False otherwise
    """
    cache_dir = get_cache_dir()
    parquet_dir = cache_dir / "parquet"
    version_dir = parquet_dir / version
    db_path = cache_dir / "data.duckdb"

    if not version_dir.exists():
        console.print(
            f"[red]✗ No cached parquet files found for version {version}[/red]"
        )
        return False

    # Remove existing database to avoid stale data
    if db_path.exists():
        db_path.unlink()

    console.print("\n[cyan]Importing parquet files into DuckDB...[/cyan]")

    # Connect to database
    conn = duckdb.connect(str(db_path))

    # Import each parquet file
    imported = 0
    failed = 0

    for parquet_file in sorted(version_dir.glob("*.parquet")):
        table_name = sanitize_table_name(parquet_file.name)

        try:
            import_parquet_to_duckdb(parquet_file, table_name, conn)

            # Get row count
            count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            count = count_result[0] if count_result else 0

            console.print(f"[green]✓ {table_name}[/green] ({count:,} rows)")
            imported += 1
        except Exception as e:
            console.print(f"[red]✗ {parquet_file.name}: {e}[/red]")
            failed += 1

    conn.close()

    if failed > 0:
        console.print(f"\n[red]✗ Failed to import {failed} file(s)[/red]")
        return False

    console.print(f"\n[green]✓ Imported {imported} table(s) to {db_path}[/green]")
    return True


def launch_harlequin(db_path: Path | None = None) -> None:
    """Launch Harlequin TUI with DuckDB connection.

    Args:
        db_path: Optional path to DuckDB file. If not provided, uses cached database.
    """
    if db_path is None:
        cache_dir = get_cache_dir()
        db_path = cache_dir / "data.duckdb"

    if not db_path.exists():
        console.print(f"[red]✗ Database not found: {db_path}[/red]")
        return

    console.print(f"\n[cyan]Launching Harlequin...[/cyan]")
    console.print(f"[dim]Database: {db_path}[/dim]\n")

    # Launch harlequin using the library
    try:
        # Load adapter plugins and get the DuckDB adapter
        adapters = load_adapter_plugins()
        adapter_cls = adapters.get("duckdb")

        if adapter_cls is None:
            console.print("[red]✗ DuckDB adapter not found[/red]")
            console.print(
                "[yellow]The DuckDB adapter should be available with harlequin[/yellow]"
            )
            sys.exit(1)

        # Instantiate the adapter with the connection string
        adapter_instance = adapter_cls(conn_str=(str(db_path),))

        # Create and run the Harlequin app
        app = Harlequin(adapter=adapter_instance)
        app.run()
    except Exception as e:
        console.print(f"[red]✗ Failed to launch Harlequin: {e}[/red]")
        console.print("[yellow]Make sure harlequin is properly installed[/yellow]")
        sys.exit(1)


def clear_cache_dir() -> None:
    """Clear cache directory and show summary."""
    cache_dir = get_cache_dir()

    if not cache_dir.exists():
        console.print("[yellow]Cache directory does not exist[/yellow]")
        return

    # Calculate cache size and file count
    total_size = 0
    file_count = 0

    for file_path in cache_dir.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size
            file_count += 1

    # Remove cache directory
    shutil.rmtree(cache_dir)

    # Format size
    size_mb = total_size / (1024 * 1024)
    if size_mb > 1024:
        size_str = f"{size_mb / 1024:.1f} GB"
    else:
        size_str = f"{size_mb:.1f} MB"

    console.print(
        f"[green]✓ Cleared {file_count} file(s) ({size_str}) from cache[/green]"
    )
    console.print(f"[dim]Cache directory: {cache_dir}[/dim]")


def cmd_tui(args: argparse.Namespace) -> None:
    """Open an interactive SQL interface to explore Open Dev Data."""

    # Handle clear cache
    if args.clear_cache:
        clear_cache_dir()
        return

    # Handle direct database file
    if args.db:
        launch_harlequin(args.db)
        return

    # Require either --lite or --db
    if not args.lite:
        console.print(
            "[red]Error: Either --lite or --db must be specified.[/red]\n"
            "Use --lite to download and cache the lite dataset,\n"
            "or --db <path> to open an existing DuckDB file."
        )
        sys.exit(1)

    # Determine which files to work with
    files_to_work_with = LITE_FILES

    cache_dir = get_cache_dir()
    version = None

    # Check cache validity
    if not args.refresh:
        console.print("[cyan]Checking cache...[/cyan]")
        cache_valid, files_to_download, version = asyncio.run(
            validate_cache(files_to_work_with)
        )

        if cache_valid:
            metadata = load_metadata()
            downloaded_at = metadata.get("downloaded_at", "unknown")
            dataset_version = metadata.get("version", version)
            console.print(
                f"[green]✓ Using cached data from {cache_dir}[/green]\n"
                f"[cyan]Version: {dataset_version}[/cyan]\n"
                f"[dim]Downloaded: {downloaded_at}[/dim]\n"
            )
            # Import to DuckDB before launching
            success = import_to_duckdb(version)
            if not success:
                console.print("[red]✗ Import failed. Exiting.[/red]")
                return
            # Skip download, go straight to launching Harlequin
            launch_harlequin()
            return
        else:
            console.print(
                f"[yellow]⚠ Cache invalid or incomplete. "
                f"Downloading {len(files_to_download)} file(s)...[/yellow]\n"
            )
    else:
        # Force refresh - clear cache and download all files
        console.print("[cyan]Refreshing cache...[/cyan]")
        parquet_dir = cache_dir / "parquet"
        if parquet_dir.exists():
            shutil.rmtree(parquet_dir)
        files_to_download = files_to_work_with
        # Fetch version from manifest
        try:
            manifest = asyncio.run(fetch_manifest())
            version = manifest["dataset"]["version"]
        except Exception as e:
            console.print(f"[red]✗ Failed to fetch manifest: {e}[/red]")
            return

    # Download files
    success = asyncio.run(download_lite_dataset(files_to_download, version))

    if not success:
        console.print("[red]✗ Download failed. Exiting.[/red]")
        return

    # Import to DuckDB
    success = import_to_duckdb(version)

    if not success:
        console.print("[red]✗ Import failed. Exiting.[/red]")
        return

    # Launch Harlequin
    launch_harlequin()
