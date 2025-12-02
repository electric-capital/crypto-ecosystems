"""Download subcommand for fetching parquet files from manifest"""

import argparse
import asyncio
import socket
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List
from urllib.parse import urljoin

import aiohttp
import blake3
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

MANIFEST_URL = "https://data.opendevdata.org/manifest.json"


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


def compute_blake3(file_path: Path) -> str:
    """Compute blake3 checksum of a file."""
    hasher = blake3.blake3()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


async def download_file(
    session: aiohttp.ClientSession,
    url: str,
    output_path: Path,
    progress: Progress,
    semaphore: asyncio.Semaphore,
    expected_b3sum: str | None = None,
    expected_size: int = 0,
    retry_count: int = 5,
    log_callback: Callable[[str, bool], None] = None,
) -> bool:
    """Download a single file with progress tracking, resumable retry logic, and blake3 validation.

    Uses HTTP Range requests to resume partial downloads on connection errors,
    which is critical for large files (e.g., 16GB) that may experience
    ClientPayloadError or other transient network issues.
    """
    task_id = None
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    async with semaphore:
        # Create progress task when download starts
        task_id = progress.add_task(
            f"⏳ {output_path.name}",
            total=0,
        )

        for attempt in range(retry_count):
            try:
                # Check if we have a partial download to resume
                downloaded = 0
                if temp_path.exists():
                    downloaded = temp_path.stat().st_size

                # Use sock_read timeout instead of total timeout for large files
                # This only times out if no data is received for 120 seconds
                timeout = aiohttp.ClientTimeout(
                    total=None,  # No total timeout
                    connect=60,  # 60s to establish connection
                    sock_read=120,  # 120s between reads (increased for slow connections)
                )

                # Set up headers for Range request if resuming
                headers = {}
                if downloaded > 0:
                    headers["Range"] = f"bytes={downloaded}-"
                    console.print(
                        f"[cyan]↻ {output_path.name}: Resuming from {downloaded:,} bytes[/cyan]"
                    )

                async with session.get(url, timeout=timeout, headers=headers) as response:
                    # Handle both 200 (full content) and 206 (partial content)
                    if response.status == 416:
                        # Range not satisfiable - file might be complete or server doesn't support ranges
                        # Check if temp file matches expected size
                        if expected_size > 0 and downloaded >= expected_size:
                            # File is complete, just rename it
                            temp_path.rename(output_path)
                            progress.update(task_id, total=expected_size, completed=expected_size, visible=False)
                            if log_callback:
                                log_callback(output_path.name, True)
                            return True
                        else:
                            # Delete and restart
                            temp_path.unlink()
                            downloaded = 0
                            continue

                    response.raise_for_status()

                    # Determine total size and whether we're resuming
                    if response.status == 206:
                        # Partial content - parse Content-Range header
                        content_range = response.headers.get("Content-Range", "")
                        if "/" in content_range:
                            total_size = int(content_range.split("/")[-1])
                        else:
                            total_size = downloaded + int(response.headers.get("content-length", 0))
                    else:
                        # Full content - server may not support Range or sent full file
                        total_size = int(response.headers.get("content-length", 0))
                        if downloaded > 0:
                            # Server didn't honor Range request, restart download
                            downloaded = 0
                            if temp_path.exists():
                                temp_path.unlink()

                    progress.update(task_id, total=total_size, completed=downloaded)

                    # Stream download to disk with larger chunks for better throughput
                    chunk_size = 1024 * 1024  # 1MB chunks for large files
                    mode = "ab" if downloaded > 0 and response.status == 206 else "wb"

                    with open(temp_path, mode) as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.update(task_id, completed=downloaded)

                # Verify downloaded size matches expected
                final_size = temp_path.stat().st_size
                if expected_size > 0 and final_size != expected_size:
                    raise ValueError(
                        f"Size mismatch: expected {expected_size:,}, got {final_size:,}"
                    )

                # Atomic rename after successful download
                temp_path.rename(output_path)

                # Validate blake3 checksum if provided
                if expected_b3sum:
                    progress.update(task_id, description=f"🔍 {output_path.name} (verifying)")
                    actual_b3sum = compute_blake3(output_path)
                    if actual_b3sum != expected_b3sum:
                        # Checksum mismatch, remove file and fail
                        output_path.unlink()
                        raise ValueError(
                            f"Blake3 checksum mismatch: expected {expected_b3sum}, got {actual_b3sum}"
                        )

                # Hide progress task and log completion
                progress.update(task_id, visible=False)

                if log_callback:
                    log_callback(output_path.name, True)

                return True

            except aiohttp.ClientPayloadError as e:
                # Connection error during download - this is resumable
                if attempt < retry_count - 1:
                    wait_time = min(2 ** (attempt + 1), 60)  # Exponential backoff, max 60s
                    progress.update(
                        task_id,
                        description=f"⚠ {output_path.name} (retry {attempt + 1}/{retry_count})",
                    )
                    console.print(
                        f"[yellow]⚠ {output_path.name}: Connection interrupted at "
                        f"{downloaded:,} bytes - resuming in {wait_time}s...[/yellow]"
                    )
                    await asyncio.sleep(wait_time)
                    # Don't delete temp file - we'll resume from it
                else:
                    if task_id is not None:
                        progress.update(task_id, visible=False)
                    if log_callback:
                        log_callback(
                            f"{output_path.name} - {type(e).__name__}: {e}", False
                        )
                    # Keep temp file for manual resume on next run
                    console.print(
                        f"[yellow]Partial download saved: {temp_path} ({downloaded:,} bytes)[/yellow]"
                    )
                    return False

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # Other connection errors - also resumable
                if attempt < retry_count - 1:
                    wait_time = min(2 ** (attempt + 1), 60)
                    progress.update(
                        task_id,
                        description=f"⚠ {output_path.name} (retry {attempt + 1}/{retry_count})",
                    )
                    console.print(
                        f"[yellow]⚠ {output_path.name}: {type(e).__name__} - retrying in {wait_time}s...[/yellow]"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    if task_id is not None:
                        progress.update(task_id, visible=False)
                    if log_callback:
                        log_callback(
                            f"{output_path.name} - {type(e).__name__}: {e}", False
                        )
                    if temp_path.exists() and downloaded > 0:
                        console.print(
                            f"[yellow]Partial download saved: {temp_path} ({downloaded:,} bytes)[/yellow]"
                        )
                    return False

            except ValueError as e:
                # Checksum or size mismatch - not resumable, need full re-download
                if attempt < retry_count - 1:
                    wait_time = min(2 ** (attempt + 1), 60)
                    progress.update(
                        task_id,
                        description=f"⚠ {output_path.name} (retry {attempt + 1}/{retry_count})",
                    )
                    console.print(
                        f"[yellow]⚠ {output_path.name}: {e} - retrying...[/yellow]"
                    )
                    # Delete temp/output file to force fresh download
                    if temp_path.exists():
                        temp_path.unlink()
                    if output_path.exists():
                        output_path.unlink()
                    await asyncio.sleep(wait_time)
                else:
                    if task_id is not None:
                        progress.update(task_id, visible=False)
                    if log_callback:
                        log_callback(f"{output_path.name} - {e}", False)
                    return False

            except Exception as e:
                # Unexpected error
                if attempt < retry_count - 1:
                    wait_time = min(2 ** (attempt + 1), 60)
                    progress.update(
                        task_id,
                        description=f"⚠ {output_path.name} (retry {attempt + 1}/{retry_count})",
                    )
                    console.print(
                        f"[yellow]⚠ {output_path.name}: {type(e).__name__} - retrying...[/yellow]"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    if task_id is not None:
                        progress.update(task_id, visible=False)
                    if log_callback:
                        log_callback(
                            f"{output_path.name} - {type(e).__name__}: {e}", False
                        )
                    if temp_path.exists():
                        temp_path.unlink()
                    return False

    return False


async def download_all_files(
    resources: List[Dict[str, str]],
    output_dir: Path,
    version: str,
    workers: int,
    retry: int,
    resume: bool,
) -> tuple[int, int, int]:
    """Download all files concurrently with progress bars."""
    # Create version-specific subfolder
    version_dir = output_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)

    # Create semaphore to limit concurrent downloads
    semaphore = asyncio.Semaphore(workers)

    # Prepare download list and validate existing files if resuming
    downloads = []
    skipped = 0
    mismatches = 0

    for resource in resources:
        path = resource["path"]
        # Resolve relative paths against manifest base URL
        if not path.startswith("http"):
            url = urljoin(MANIFEST_URL, path)
        else:
            url = path

        filename = Path(path).name
        output_path = version_dir / filename

        # Get expected size and blake3 checksum from manifest
        expected_size = resource.get("size_bytes", 0)
        expected_b3sum = resource.get("b3sum", None)

        # Check for partial download (.tmp file) from previous interrupted run
        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        if resume and temp_path.exists():
            partial_size = temp_path.stat().st_size
            console.print(
                f"[cyan]↻ Found partial download: {filename} ({partial_size:,} / {expected_size:,} bytes)[/cyan]"
            )
            downloads.append((url, output_path, expected_b3sum, expected_size))
            continue

        # Check if file already exists and validate size + blake3
        if resume and output_path.exists():
            local_size = output_path.stat().st_size

            # First check size
            if expected_size > 0 and local_size == expected_size:
                # Size matches, check blake3 if available
                if expected_b3sum:
                    local_b3sum = compute_blake3(output_path)
                    if local_b3sum == expected_b3sum:
                        # File is valid, skip
                        skipped += 1
                        console.print(
                            f"[dim]⊙ Skipping {filename} (verified: {local_size:,} bytes, blake3 OK)[/dim]"
                        )
                        continue
                    else:
                        # Blake3 mismatch, re-download
                        mismatches += 1
                        console.print(
                            f"[yellow]⚠ Re-downloading {filename} (blake3 mismatch)[/yellow]"
                        )
                else:
                    # No blake3 in manifest, just trust size
                    skipped += 1
                    console.print(
                        f"[dim]⊙ Skipping {filename} (size matches: {local_size:,} bytes)[/dim]"
                    )
                    continue
            else:
                # Size mismatch, re-download
                mismatches += 1
                console.print(
                    f"[yellow]⚠ Re-downloading {filename} (size mismatch: local={local_size:,}, expected={expected_size:,})[/yellow]"
                )

        downloads.append((url, output_path, expected_b3sum, expected_size))

    if mismatches > 0:
        console.print(f"[yellow]Found {mismatches} file(s) with mismatches[/yellow]\n")

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
        # This prevents routers/NATs/firewalls from dropping idle connections
        socket_options = [
            # Enable TCP keepalive
            (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
        ]
        # Add platform-specific keepalive tuning (Linux only)
        if hasattr(socket, "TCP_KEEPIDLE"):
            socket_options.extend([
                # Send first keepalive probe after 60s of idle
                (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60),
                # Send keepalive probes every 15s
                (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 15),
                # Consider connection dead after 4 failed probes
                (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 4),
            ])

        connector = aiohttp.TCPConnector(
            limit=workers,  # Limit total connections
            limit_per_host=workers,  # Limit per host
            ttl_dns_cache=300,  # Cache DNS for 5 minutes
            keepalive_timeout=90,  # Keep connections alive for 90s
            force_close=False,  # Reuse connections
            enable_cleanup_closed=True,
            socket_options=socket_options,
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
                    expected_b3sum,
                    expected_size,
                    retry,
                    log_completion,
                )
                for url, output_path, expected_b3sum, expected_size in downloads
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

    # Extract version and resources
    try:
        version = manifest["dataset"]["version"]
        resources = manifest["dataset"]["resources"]
    except KeyError as e:
        console.print(f"[red]Error: Invalid manifest format (missing {e})[/red]")
        sys.exit(1)

    console.print(f"[green]Found {len(resources)} files in manifest[/green]")
    console.print(f"[cyan]Dataset version: {version}[/cyan]")

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
        download_all_files(
            resources, output_dir, version, args.workers, args.retry, args.resume
        )
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
    console.print(f"\n[green]Files saved to: {output_dir.absolute() / version}[/green]")

    # Exit with error code if any downloads failed
    if failed > 0:
        raise SystemExit(1)
