import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import httpx

from mnemolith.config import (
    get_backup_dir,
    get_backup_keep,
    get_collection_name,
    get_postgres_conn_params,
    get_qdrant_api_key,
    get_qdrant_url,
)

logger = logging.getLogger(__name__)

PG_DUMP_FILE = "pg_dump.sql"
QDRANT_SNAPSHOT_FILE = "qdrant_snapshot.snapshot"
BACKUP_NAME_RE = re.compile(r"\d{8}_\d{6}")

# Docker compose service name for PostgreSQL
PG_SERVICE = "postgres"


def _docker_compose_prefix() -> list[str]:
    """Return the docker compose command prefix with project directory."""
    compose_file = os.environ.get("COMPOSE_FILE")
    if compose_file:
        return ["docker", "compose", "-f", compose_file]
    return ["docker", "compose"]


def backup_postgres(backup_path: Path) -> Path:
    params = get_postgres_conn_params()
    cmd = [
        *_docker_compose_prefix(),
        "exec", "-T", PG_SERVICE,
        "pg_dump", "--clean", "-U", params["user"], params["dbname"],
    ]
    try:
        result = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        raise RuntimeError("docker compose not found. Install Docker.")
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr.decode()}")
    dump_file = backup_path / PG_DUMP_FILE
    dump_file.write_bytes(result.stdout)
    return dump_file


def restore_postgres(backup_path: Path) -> None:
    dump_file = backup_path / PG_DUMP_FILE
    if not dump_file.exists():
        raise FileNotFoundError(f"{PG_DUMP_FILE} not found in {backup_path}")
    params = get_postgres_conn_params()
    cmd = [
        *_docker_compose_prefix(),
        "exec", "-T", PG_SERVICE,
        "psql", "-U", params["user"], "-d", params["dbname"],
    ]
    try:
        result = subprocess.run(cmd, input=dump_file.read_bytes(), capture_output=True)
    except FileNotFoundError:
        raise RuntimeError("docker compose not found. Install Docker.")
    if result.returncode != 0:
        raise RuntimeError(f"psql restore failed: {result.stderr.decode()}")


def _qdrant_headers() -> dict[str, str]:
    api_key = get_qdrant_api_key()
    if api_key:
        return {"api-key": api_key}
    return {}


def backup_qdrant(backup_path: Path) -> Path:
    from mnemolith.qdrant_store import QdrantStore
    store = QdrantStore()
    collection = get_collection_name()
    snapshot = store.client.create_snapshot(collection, wait=True)

    url = f"{get_qdrant_url()}/collections/{collection}/snapshots/{snapshot.name}"
    snapshot_file = backup_path / QDRANT_SNAPSHOT_FILE
    try:
        with httpx.Client() as http, http.stream("GET", url, headers=_qdrant_headers()) as response:
            response.raise_for_status()
            with open(snapshot_file, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
    finally:
        # Snapshots live in the container's writable layer and would pile up forever
        store.client.delete_snapshot(collection, snapshot.name)
    return snapshot_file


def restore_qdrant(backup_path: Path) -> None:
    snapshot_file = backup_path / QDRANT_SNAPSHOT_FILE
    if not snapshot_file.exists():
        raise FileNotFoundError(f"{QDRANT_SNAPSHOT_FILE} not found in {backup_path}")

    collection = get_collection_name()
    url = f"{get_qdrant_url()}/collections/{collection}/snapshots/upload"
    with open(snapshot_file, "rb") as f:
        response = httpx.post(
            url,
            files={"snapshot": f},
            headers=_qdrant_headers(),
        )
    response.raise_for_status()


def backup_vector_store(backup_path: Path) -> Path | None:
    backend = os.environ.get("VECTOR_BACKEND", "qdrant")
    if backend == "qdrant":
        return backup_qdrant(backup_path)
    elif backend == "pgvector":
        # pgvector data is in PostgreSQL, already covered by backup_postgres
        return None
    raise ValueError(f"Unknown vector backend: {backend}")


def restore_vector_store(backup_path: Path) -> None:
    backend = os.environ.get("VECTOR_BACKEND", "qdrant")
    if backend == "qdrant":
        restore_qdrant(backup_path)
    elif backend == "pgvector":
        # pgvector data is in PostgreSQL, already covered by restore_postgres
        pass
    else:
        raise ValueError(f"Unknown vector backend: {backend}")


def create_backup(backup_dir: Path | None = None) -> Path:
    if backup_dir is None:
        backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)
    try:
        backup_postgres(backup_path)
        backup_vector_store(backup_path)
    except Exception:
        # A partial backup would count against BACKUP_KEEP and push out a good one
        shutil.rmtree(backup_path, ignore_errors=True)
        raise
    prune_backups(backup_dir, get_backup_keep())
    return backup_path


def prune_backups(backup_dir: Path, keep: int) -> list[Path]:
    if keep <= 0:
        return []
    backups = sorted(p for p in backup_dir.iterdir() if p.is_dir() and BACKUP_NAME_RE.fullmatch(p.name))
    removed = backups[:-keep]
    for path in removed:
        shutil.rmtree(path)
    if removed:
        logger.info("Pruned %d old backup(s), keeping the %d most recent", len(removed), keep)
    return removed


def restore_backup(backup_path: Path) -> None:
    if not backup_path.is_dir():
        raise FileNotFoundError(f"Backup directory not found: {backup_path}")
    restore_postgres(backup_path)
    restore_vector_store(backup_path)
