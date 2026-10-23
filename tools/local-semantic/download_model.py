#!/usr/bin/env python3
"""Download one pinned public model's assets without credentials or remote Python code."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data/experiments/local-semantic-v1.json"
OUTPUT = ROOT / "results/local-semantic/model"
FILES = ("onnx/model.onnx", "tokenizer.json", "config.json", "1_Pooling/config.json")


def main():
    config = json.loads(CONFIG.read_text())
    manifest_path = OUTPUT / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for name, record in manifest["files"].items():
            if hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() != record["sha256"]:
                raise SystemExit("Saved model asset hash mismatch; refusing a repeat download")
        print("Pinned model assets already present and verified; no download")
        return
    if any((OUTPUT / name).exists() for name in FILES):
        raise SystemExit("Partial model download exists; inspect it before any repeat request")
    manifest = {
        "model": config["model"],
        "revision": config["revision"],
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
        "files": {},
    }
    for name in FILES:
        path = OUTPUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/{config['model']}/resolve/{config['revision']}/{name}"
        digest, size = hashlib.sha256(), 0
        with urlopen(url, timeout=60) as source, path.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                if size > 150_000_000:
                    raise SystemExit("Model asset exceeds experiment's 150 MB per-file limit")
                digest.update(chunk)
                target.write(chunk)
        manifest["files"][name] = {"bytes": size, "sha256": digest.hexdigest()}
        print(f"Saved {name}: {size} bytes")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
