"""
TwinNode External Dataset Download Manager
Handles resilient downloading, progress tracking, resume, checksum verification,
safe ZIP extraction, duplicate detection, history logging, and manual local dataset import.
"""

import os
import sys
import json
import time
import uuid
import hashlib
import zipfile
import asyncio
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable

from backend.app.data.external_dataset_catalog import (
    EXTERNAL_DATASET_CATALOG,
    is_url_allowed
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXTERNAL_ROOT = BASE_DIR / "datasets" / "external"
PROCESSED_ROOT = BASE_DIR / "datasets" / "processed"
HISTORY_FILE = EXTERNAL_ROOT / "download_history.json"

class ExternalDatasetManager:
    def __init__(self):
        EXTERNAL_ROOT.mkdir(parents=True, exist_ok=True)
        PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self._ensure_history_file()

    def _ensure_history_file(self):
        if not HISTORY_FILE.exists():
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_history(self) -> List[Dict[str, Any]]:
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _record_history(self, record: Dict[str, Any]):
        history = self.get_history()
        history.insert(0, record)
        # Keep latest 100 entries
        history = history[:100]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"[DatasetManager] Failed to write history: {e}")

    def list_catalog(self) -> List[Dict[str, Any]]:
        """List catalog entries merged with local download and processing status."""
        catalog_list = []
        for key, entry in EXTERNAL_DATASET_CATALOG.items():
            dataset_dir = EXTERNAL_ROOT / key
            processed_dir = PROCESSED_ROOT / key
            
            # Check local raw files
            raw_files = []
            total_raw_bytes = 0
            if dataset_dir.exists():
                for f in dataset_dir.glob("*"):
                    if f.is_file() and not f.name.startswith("."):
                        raw_files.append({
                            "name": f.name,
                            "size_bytes": f.stat().st_size,
                            "modified": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()
                        })
                        total_raw_bytes += f.stat().st_size

            # Check local processed files
            processed_files = []
            if processed_dir.exists():
                for f in processed_dir.glob("*"):
                    if f.is_file() and not f.name.startswith("."):
                        processed_files.append({
                            "name": f.name,
                            "size_bytes": f.stat().st_size,
                            "modified": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()
                        })

            is_downloaded = len(raw_files) > 0
            is_processed = len(processed_files) > 0

            item = dict(entry)
            item["is_downloaded"] = is_downloaded
            item["is_processed"] = is_processed
            item["raw_files"] = raw_files
            item["processed_files"] = processed_files
            item["total_local_bytes"] = total_raw_bytes
            item["local_dir"] = str(dataset_dir)
            catalog_list.append(item)

        return catalog_list

    def get_download_status(self, download_id: str) -> Optional[Dict[str, Any]]:
        return self.active_tasks.get(download_id)

    async def start_download(
        self,
        dataset_id: str,
        custom_url: Optional[str] = None,
        force_redownload: bool = False
    ) -> Dict[str, Any]:
        """Initiate background asynchronous download with progress tracking and integrity validation."""
        if dataset_id not in EXTERNAL_DATASET_CATALOG:
            raise ValueError(f"Unknown dataset_id: {dataset_id}. Must be one of {list(EXTERNAL_DATASET_CATALOG.keys())}")

        cat_entry = EXTERNAL_DATASET_CATALOG[dataset_id]
        target_url = custom_url or cat_entry.get("download_url")

        if not target_url:
            raise ValueError(
                f"Dataset '{cat_entry['name']}' requires authorized registration. {cat_entry.get('auth_instructions', '')}"
            )

        # Security check: strict domain allowlist
        if not is_url_allowed(target_url):
            raise PermissionError(
                f"Download URL '{target_url}' is not in the server-side authorized domain allowlist."
            )

        filename = cat_entry.get("filename") or Path(target_url.split("?")[0]).name or f"{dataset_id}.csv"
        # Sanitize filename
        filename = Path(filename).name

        dataset_dir = EXTERNAL_ROOT / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dataset_dir / filename

        # Duplicate download detection
        if dest_path.exists() and not force_redownload:
            size = dest_path.stat().st_size
            if size > 100: # non-empty existing file
                return {
                    "download_id": "ALREADY_EXISTS",
                    "status": "COMPLETED",
                    "dataset_id": dataset_id,
                    "filename": filename,
                    "file_path": str(dest_path),
                    "bytes_downloaded": size,
                    "total_bytes": size,
                    "progress_percent": 100.0,
                    "message": "File already exists. Use force_redownload=True to re-download."
                }

        download_id = f"DL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        task_info = {
            "download_id": download_id,
            "dataset_id": dataset_id,
            "dataset_name": cat_entry["name"],
            "url": target_url,
            "filename": filename,
            "dest_path": str(dest_path),
            "status": "QUEUED",
            "progress_percent": 0.0,
            "bytes_downloaded": 0,
            "total_bytes": cat_entry.get("approx_size_bytes") or 0,
            "speed_kbps": 0.0,
            "sha256": None,
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None
        }
        self.active_tasks[download_id] = task_info

        # Launch background task
        asyncio.create_task(self._execute_download_async(download_id))
        return task_info

    async def _execute_download_async(self, download_id: str):
        task = self.active_tasks[download_id]
        url = task["url"]
        dest_path = Path(task["dest_path"])
        part_path = dest_path.with_suffix(dest_path.suffix + ".part")

        task["status"] = "DOWNLOADING"
        headers = {
            "User-Agent": "Mozilla/5.0 (TwinNode-Industrial-Supervisor/1.0)",
            "Accept": "*/*"
        }

        # Check resume capability
        start_byte = 0
        if part_path.exists():
            start_byte = part_path.stat().st_size
            if start_byte > 0:
                headers["Range"] = f"bytes={start_byte}-"

        max_retries = 3
        backoff = 2

        for attempt in range(max_retries):
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._stream_download, download_id, url, part_path, headers, start_byte)
                
                # Download finished; rename .part to final
                if part_path.exists():
                    part_path.replace(dest_path)

                # Compute SHA256 checksum
                sha256 = self._compute_sha256(dest_path)
                task["sha256"] = sha256
                task["status"] = "COMPLETED"
                task["progress_percent"] = 100.0
                task["bytes_downloaded"] = dest_path.stat().st_size
                task["total_bytes"] = dest_path.stat().st_size
                task["completed_at"] = datetime.now(timezone.utc).isoformat()

                # If zip archive, perform safe extraction
                if dest_path.suffix.lower() == ".zip":
                    self._safe_extract_zip(dest_path, dest_path.parent)

                # Log to history
                self._record_history({
                    "event_type": "DOWNLOAD",
                    "download_id": download_id,
                    "dataset_id": task["dataset_id"],
                    "dataset_name": task["dataset_name"],
                    "filename": task["filename"],
                    "size_bytes": dest_path.stat().st_size,
                    "sha256": sha256,
                    "url": url,
                    "provenance": "PUBLIC_DATASET",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "SUCCESS"
                })
                return

            except Exception as e:
                task["error"] = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    task["status"] = "FAILED"
                    task["completed_at"] = datetime.now(timezone.utc).isoformat()
                    self._record_history({
                        "event_type": "DOWNLOAD",
                        "download_id": download_id,
                        "dataset_id": task["dataset_id"],
                        "dataset_name": task["dataset_name"],
                        "filename": task["filename"],
                        "error": str(e),
                        "status": "FAILED",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

    def _stream_download(
        self,
        download_id: str,
        url: str,
        part_path: Path,
        headers: Dict[str, str],
        start_byte: int
    ):
        """Blocking stream download executed in thread pool."""
        task = self.active_tasks[download_id]
        req = urllib.request.Request(url, headers=headers)

        open_mode = "ab" if start_byte > 0 else "wb"
        with urllib.request.urlopen(req, timeout=60) as resp, open(part_path, open_mode) as out_f:
            content_length = resp.headers.get("Content-Length")
            total_bytes = (int(content_length) + start_byte) if content_length else task.get("total_bytes", 0)
            task["total_bytes"] = total_bytes

            chunk_size = 64 * 1024 # 64KB
            bytes_so_far = start_byte
            start_time = time.perf_counter()

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_f.write(chunk)
                bytes_so_far += len(chunk)
                elapsed = time.perf_counter() - start_time
                speed = (bytes_so_far - start_byte) / (elapsed * 1024) if elapsed > 0 else 0

                task["bytes_downloaded"] = bytes_so_far
                task["speed_kbps"] = round(speed, 1)
                if total_bytes > 0:
                    task["progress_percent"] = round(min(100.0, (bytes_so_far / total_bytes) * 100.0), 2)

    def _compute_sha256(self, filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(128 * 1024):
                h.update(chunk)
        return h.hexdigest()

    def _safe_extract_zip(self, zip_path: Path, target_dir: Path):
        """
        Safely extract ZIP archive, checking for path traversal (Zip Slip vulnerability).
        Never extract executable binaries or execute scripts.
        """
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.infolist():
                # Disallow executable extensions
                lower_name = member.filename.lower()
                if lower_name.endswith((".exe", ".bat", ".sh", ".cmd", ".vbs", ".ps1")):
                    continue

                target_file = target_dir / member.filename
                # Ensure resolved target path is within target_dir
                resolved_target = target_file.resolve()
                resolved_base = target_dir.resolve()
                if not str(resolved_target).startswith(str(resolved_base)):
                    raise SecurityError(f"Attempted path traversal in ZIP member: {member.filename}")

                z.extract(member, target_dir)

    def import_local_file(
        self,
        dataset_id: str,
        source_path_or_buffer,
        original_filename: str
    ) -> Dict[str, Any]:
        """
        Safely import a locally provided dataset file (e.g. for SWaT or Edge-IIoTset).
        """
        clean_name = Path(original_filename).name
        ext = Path(clean_name).suffix.lower()

        if ext not in [".csv", ".parquet", ".zip", ".txt"]:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: .csv, .parquet, .zip, .txt")

        dataset_dir = EXTERNAL_ROOT / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dataset_dir / clean_name

        if isinstance(source_path_or_buffer, (str, Path)):
            src = Path(source_path_or_buffer)
            if not src.exists():
                raise FileNotFoundError(f"Source file not found: {src}")
            import shutil
            shutil.copy2(src, dest_file)
        else:
            with open(dest_file, "wb") as f:
                f.write(source_path_or_buffer)

        if ext == ".zip":
            self._safe_extract_zip(dest_file, dataset_dir)

        sha256 = self._compute_sha256(dest_file)
        rec = {
            "event_type": "MANUAL_IMPORT",
            "dataset_id": dataset_id,
            "filename": clean_name,
            "size_bytes": dest_file.stat().st_size,
            "sha256": sha256,
            "provenance": "PUBLIC_DATASET",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "SUCCESS"
        }
        self._record_history(rec)
        return rec

dataset_manager = ExternalDatasetManager()
