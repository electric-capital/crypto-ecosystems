"""Download subcommand for fetching parquet files from manifest"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List
from urllib.parse import urljoin

import aiohttp
from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console()

MANIFEST_URL = "https://data.developerreport.com/manifest.json"


async def fetch_manifest() -> Dict[str, Any]:
    """Fetch and parse the manifest JSON file."""
    async with aiohttp.ClientSession() as session:
        async with session.get(MANIFEST_URL) as response:
            response.raise_for_status()
            return await response.json()


async def get_remote_file_size(session: aiohttp.ClientSession, url: str) -> int:
    """Get the expected file size from HTTP headers using HEAD request."""
    try:
        async with session.head(url, allow_redirects=True) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length", "0")
            return int(content_length)
    except Exception:
        # If HEAD request fails, return 0 to trigger re-download
        return 0


async def download_file(
    session: aiohttp.ClientSession,
    url: str,
    output_path: Path,
    progress: Progress,
    semaphore: asyncio.Semaphore,
    retry_count: int = 3,
    log_callback: Callable[[str, bool], None] = None,
) -> bool:
    """Download a single file with progress tracking and retry logic."""
    task_id = None
    async with semaphore:
        # Create progress task when download starts
        task_id = progress.add_task(
            f"⏳ {output_path.name}",
            total=0,
        )

        for attempt in range(retry_count):
            try:
                # Download to temporary file first
                temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

                # Use sock_read timeout instead of total timeout for large files
                # This only times out if no data is received for 60 seconds
                timeout = aiohttp.ClientTimeout(
                    total=None,  # No total timeout
                    connect=30,  # 30s to establish connection
                    sock_read=60,  # 60s between reads
                )

                async with session.get(url, timeout=timeout) as response:
                    response.raise_for_status()

                    # Get file size for progress tracking
                    total_size = int(response.headers.get("content-length", 0))
                    progress.update(task_id, total=total_size)

                    # Stream download to disk with larger chunks for better throughput
                    downloaded = 0
                    chunk_size = 1024 * 1024  # 1MB chunks for large files
                    with open(temp_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.update(task_id, completed=downloaded)

                # Atomic rename after successful download
                temp_path.rename(output_path)

                # Hide progress task and log completion
                progress.update(task_id, visible=False)

                if log_callback:
                    log_callback(output_path.name, True)

                return True

            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    progress.update(
                        task_id,
                        description=f"⚠ {output_path.name} (retry {attempt + 1}/{retry_count})",
                    )
                    # Log the error type for debugging large file issues
                    console.print(
                        f"[yellow]⚠ {output_path.name}: {type(e).__name__} - retrying...[/yellow]"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Hide progress task and log failure
                    if task_id is not None:
                        progress.update(task_id, visible=False)

                    if log_callback:
                        log_callback(
                            f"{output_path.name} - {type(e).__name__}: {e}", False
                        )

                    # Clean up temp file if it exists
                    if temp_path.exists():
                        temp_path.unlink()
                    return False

    return False


async def download_all_files(
    resources: List[Dict[str, str]],
    output_dir: Path,
    workers: int,
    retry: int,
    resume: bool,
) -> tuple[int, int, int]:
    """Download all files concurrently with progress bars."""
    # Create semaphore to limit concurrent downloads
    semaphore = asyncio.Semaphore(workers)

    # Prepare download list and validate existing files if resuming
    downloads = []
    skipped = 0
    size_mismatches = 0

    # Create a session for checking file sizes
    async with aiohttp.ClientSession() as check_session:
        for resource in resources:
            path = resource["path"]
            # Resolve relative paths against manifest base URL
            if not path.startswith("http"):
                url = urljoin(MANIFEST_URL, path)
            else:
                url = path

            filename = Path(path).name
            output_path = output_dir / filename

            # Check if file already exists and validate size
            if resume and output_path.exists():
                local_size = output_path.stat().st_size
                remote_size = await get_remote_file_size(check_session, url)

                if remote_size > 0 and local_size == remote_size:
                    # File exists and size matches, skip
                    skipped += 1
                    console.print(
                        f"[dim]⊙ Skipping {filename} (size matches: {local_size:,} bytes)[/dim]"
                    )
                    continue
                elif remote_size > 0:
                    # File exists but size doesn't match, re-download
                    size_mismatches += 1
                    console.print(
                        f"[yellow]⚠ Re-downloading {filename} (size mismatch: local={local_size:,}, remote={remote_size:,})[/yellow]"
                    )

            downloads.append((url, output_path))

    if size_mismatches > 0:
        console.print(
            f"[yellow]Found {size_mismatches} file(s) with size mismatches[/yellow]\n"
        )

    if not downloads:
        return 0, 0, skipped

    # Set up overall progress (for file counts)
    overall_progress = Progress(
        TextColumn("[bold cyan]{task.description}", justify="left"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
    )

    # Set up file download progress (for individual files with bytes/speed)
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

    # Create overall progress task
    overall_task = overall_progress.add_task(
        f"[cyan]Overall: 0/{len(downloads)} files",
        total=len(downloads),
    )

    # Track completed count for updating description
    completed_count = {"value": 0}

    # Callback to log completed downloads and update overall progress
    def log_completion(filename: str, success: bool):
        completed_count["value"] += 1
        overall_progress.advance(overall_task, 1)
        overall_progress.update(
            overall_task,
            description=f"[cyan]Overall: {completed_count['value']}/{len(downloads)} files",
        )
        if success:
            console.print(f"[green]✓ Downloaded: {filename}[/green]")
        else:
            console.print(f"[red]✗ Failed: {filename}[/red]")

    # Combine progress displays
    progress_group = Group(overall_progress, file_progress)

    # Use Live to pin progress at bottom
    with Live(
        progress_group,
        console=console,
        refresh_per_second=10,
        transient=False,
        screen=False,
        auto_refresh=True,
    ):
        # Configure TCP keepalive for long downloads
        connector = aiohttp.TCPConnector(
            limit=workers,  # Limit total connections
            limit_per_host=workers,  # Limit per host
            ttl_dns_cache=300,  # Cache DNS for 5 minutes
            keepalive_timeout=90,  # Keep connections alive for 90s
            force_close=False,  # Reuse connections
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            # Create tasks for all downloads
            tasks = [
                download_file(
                    session,
                    url,
                    output_path,
                    file_progress,
                    semaphore,
                    retry,
                    log_completion,
                )
                for url, output_path in downloads
            ]

            # Wait for all downloads to complete
            results = await asyncio.gather(*tasks)

    successful = sum(results)
    failed = len(results) - successful

    return successful, failed, skipped


def cmd_download(args: argparse.Namespace) -> None:
    """Download all parquet files from the manifest"""

    output_dir = Path(args.output)

    # Validate output directory
    if output_dir.exists():
        if not output_dir.is_dir():
            console.print(
                f"[red]Error: {args.output} exists and is not a directory[/red]"
            )
            sys.exit(1)
        if not (args.resume or args.force) and list(output_dir.iterdir()):
            console.print(
                f"[red]Error: {args.output} is not empty. Use --resume or --force[/red]"
            )
            sys.exit(1)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch manifest
    console.print(f"[cyan]Fetching manifest from {MANIFEST_URL}...[/cyan]")

    try:
        manifest = asyncio.run(fetch_manifest())
    except Exception as e:
        console.print(f"[red]Error fetching manifest: {e}[/red]")
        sys.exit(1)

    # Extract resources
    try:
        resources = manifest["dataset"]["resources"]
    except KeyError:
        console.print("[red]Error: Invalid manifest format[/red]")
        sys.exit(1)

    console.print(f"[green]Found {len(resources)} files in manifest[/green]")

    # Dry run mode
    if args.dry_run:
        console.print("\n[yellow]Dry run - files to download:[/yellow]")
        for i, resource in enumerate(resources, 1):
            path = resource["path"]
            filename = Path(path).name
            description = resource.get("description", "No description")
            console.print(f"  {i}. {filename}")
            console.print(f"     {description}")
        return

    # Perform download
    console.print(f"\n[cyan]Starting download with {args.workers} workers...[/cyan]\n")

    successful, failed, skipped = asyncio.run(
        download_all_files(resources, output_dir, args.workers, args.retry, args.resume)
    )

    # Display summary
    console.print()
    console.print("[bold]Download Summary:[/bold]")
    console.print(f"  [green]Successful: {successful}[/green]")
    if failed > 0:
        console.print(f"  [red]Failed: {failed}[/red]")
    if skipped > 0:
        console.print(f"  [yellow]Skipped: {skipped}[/yellow]")
    console.print(f"  [cyan]Total: {len(resources)}[/cyan]")
    console.print(f"\n[green]Files saved to: {output_dir.absolute()}[/green]")

    # Exit with error code if any downloads failed
    if failed > 0:
        raise SystemExit(1)
