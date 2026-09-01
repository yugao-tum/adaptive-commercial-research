#!/usr/bin/env python3
"""Store an authorized raw payload by content hash and append its provenance record."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(prefix: str, value: object) -> str:
    return f"{prefix}-{hashlib.sha256(stable_json(value).encode('utf-8')).hexdigest()[:24]}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected a JSON object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name}:{line_no}: expected a JSON object")
        rows.append(value)
    return rows


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    rendered = "".join(stable_json(row) + "\n" for row in rows)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_directory")
    p.add_argument("payload")
    p.add_argument("--target-id", required=True)
    p.add_argument("--attempt-id", required=True)
    p.add_argument("--source-id")
    p.add_argument("--locator", required=True)
    p.add_argument("--retrieved-at", required=True)
    p.add_argument("--route-version", required=True)
    p.add_argument("--media-type")
    p.add_argument("--access-class", choices=("public", "internal", "private", "restricted"), default="public")
    return p


def main() -> int:
    args = parser().parse_args()
    root = Path(args.run_directory).expanduser().resolve()
    payload = Path(args.payload).expanduser().resolve()
    if not payload.is_file():
        raise ValueError(f"payload is not a file: {payload}")
    manifest = load_json(root / "run_manifest.json")
    content_hash = sha256_file(payload)
    suffix = payload.suffix.lower()
    if not suffix or len(suffix) > 12 or not suffix[1:].isalnum():
        suffix = ".bin"
    relative_path = Path("raw") / "sha256" / content_hash[:2] / f"{content_hash}{suffix}"
    destination = (root / relative_path).resolve()
    if root not in destination.parents:
        raise ValueError("raw artifact destination escaped the run directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stored_new = False
    if destination.exists():
        if sha256_file(destination) != content_hash:
            raise ValueError("existing content-addressed artifact has the wrong hash")
    else:
        shutil.copyfile(payload, destination)
        stored_new = True

    artifact_id = stable_id(
        "RAW",
        {
            "run_id": manifest.get("run_id"),
            "target_id": args.target_id,
            "attempt_id": args.attempt_id,
            "sha256": content_hash,
        },
    )
    row = {
        "raw_artifact_id": artifact_id,
        "run_id": manifest.get("run_id"),
        "target_id": args.target_id,
        "attempt_id": args.attempt_id,
        "source_id": args.source_id,
        "sha256": content_hash,
        "relative_path": relative_path.as_posix(),
        "bytes": payload.stat().st_size,
        "media_type": args.media_type or mimetypes.guess_type(payload.name)[0] or "application/octet-stream",
        "locator": args.locator,
        "retrieved_at": args.retrieved_at,
        "route_version": args.route_version,
        "access_class": args.access_class,
        "storage_state": "stored",
    }
    registry_path = root / "raw_artifacts.jsonl"
    existing = load_jsonl(registry_path)
    by_id = {str(item.get("raw_artifact_id")): item for item in existing}
    if len(by_id) != len(existing):
        raise ValueError("raw_artifacts.jsonl contains duplicate raw_artifact_id values")
    existing_row = by_id.get(artifact_id)
    if existing_row is not None and existing_row != row:
        raise ValueError(f"raw artifact {artifact_id} conflicts with its existing registry row")
    appended = existing_row is None
    if appended:
        atomic_write_jsonl(registry_path, existing + [row])
    print(
        json.dumps(
            {
                "raw_artifact_id": artifact_id,
                "sha256": content_hash,
                "relative_path": relative_path.as_posix(),
                "stored_new": stored_new,
                "registry_appended": appended,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
