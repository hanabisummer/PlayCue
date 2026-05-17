from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_source_info(source_path: Path, calculate_hash: bool = True) -> dict[str, Any]:
    source_path = source_path.resolve()
    stat = source_path.stat()
    info = {
        "source_path": str(source_path),
        "source_filename": source_path.name,
        "source_size_bytes": stat.st_size,
        "source_modified_time": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
        "source_created_time": datetime.fromtimestamp(stat.st_ctime).astimezone().isoformat(),
        "processing_started_at": datetime.now().astimezone().isoformat(),
    }
    if calculate_hash:
        info["sha256_before"] = calculate_sha256(source_path)
    return info


def assert_safe_output_path(source_path: Path, output_path: Path, outputs_root: Path) -> None:
    source = source_path.resolve()
    output = output_path.resolve()
    root = outputs_root.resolve()
    if source == output:
        raise ValueError(f"入力動画と出力先が同一です: {output}")
    if root == root.parent:
        raise ValueError(f"危険な出力ルートです: {root}")
    if root not in output.parents and output != root:
        raise ValueError(f"出力先は outputs 配下に限定します: {output}")


def verify_source_unchanged(before_info: dict[str, Any], source_path: Path, calculate_hash: bool = True) -> dict[str, Any]:
    stat = source_path.stat()
    result = {
        "source_size_after_bytes": stat.st_size,
        "source_modified_time_after": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
    }
    unchanged = stat.st_size == before_info["source_size_bytes"]
    if calculate_hash and before_info.get("sha256_before"):
        result["sha256_after"] = calculate_sha256(source_path)
        unchanged = unchanged and result["sha256_after"] == before_info["sha256_before"]
    result["source_unchanged"] = unchanged
    return result

