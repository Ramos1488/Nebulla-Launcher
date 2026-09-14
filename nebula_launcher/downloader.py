"""Simple concurrent downloader used for client jar / libraries / assets."""
from __future__ import annotations
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

ProgressCallback = Optional[Callable[[int, int, str], None]]  # done, total, label


def _sha1_matches(path: Path, expected: Optional[str]) -> bool:
    if not expected or not path.exists():
        return False
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest() == expected


def download_file(url: str, dest: Path, sha1: Optional[str] = None) -> None:
    if _sha1_matches(dest, sha1):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                if chunk:
                    f.write(chunk)
    tmp.replace(dest)


def download_many(
    jobs: list[tuple[str, Path, Optional[str]]],
    progress: ProgressCallback = None,
    max_workers: int = 8,
) -> None:
    """jobs: list of (url, dest_path, sha1_or_None)."""
    total = len(jobs)
    done = 0
    if progress:
        progress(0, total, "Starting download...")

    def _run(job):
        url, dest, sha1 = job
        download_file(url, dest, sha1)
        return dest.name

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run, job): job for job in jobs}
        for fut in as_completed(futures):
            done += 1
            exc = fut.exception()
            if exc:
                raise exc
            name = fut.result()
            if progress:
                progress(done, total, name)
