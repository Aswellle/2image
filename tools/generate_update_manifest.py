#!/usr/bin/env python3
"""
tools/generate_update_manifest.py — build update.json from real artifacts
─────────────────────────────────────────────────────────────────────────
CI-only.  Computes size + SHA-256 from the freshly built installer
(never hand-edited), assembles the update.json payload and validates it
with the exact rules the client enforces in
services/updater/manifest.py before writing it out.  A release whose
manifest fails this validation cannot ship.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.updater.manifest import REPO_NAME, REPO_OWNER, validate_manifest  # noqa: E402


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="generate_update_manifest",
        description="Generate the update.json release asset")
    parser.add_argument("--version", required=True, help="2.6.1")
    parser.add_argument("--tag", required=True, help="v2.6.1")
    parser.add_argument("--installer", required=True,
                        help="path of the built installer exe")
    parser.add_argument("--out", required=True,
                        help="where to write update.json")
    parser.add_argument("--published-at", default="",
                        help="ISO-8601 timestamp (defaults to now UTC)")
    args = parser.parse_args()

    installer = Path(args.installer)
    if not installer.is_file():
        print(f"[update-manifest] FAIL: installer missing: {installer}",
              file=sys.stderr)
        return 1

    file_name = installer.name
    size = installer.stat().st_size
    sha256 = sha256_of(installer)
    published = args.published_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    release_url = (f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
                   f"/releases/tag/{args.tag}")

    payload = {
        "schemaVersion": 1,
        "channel": "stable",
        "version": args.version,
        "tag": args.tag,
        "publishedAt": published,
        "releaseUrl": release_url,
        "releaseNotesUrl": release_url,
        "mandatory": False,
        "minimumSupportedVersion": "0.0.0",
        "assets": {
            "windows-x64-installer": {
                "fileName": file_name,
                "downloadUrl": (f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
                                f"/releases/download/{args.tag}/{file_name}"),
                "size": size,
                "sha256": sha256,
            },
        },
    }

    # Same gate the client applies — a manifest that would be rejected
    # by the app must never be published.
    try:
        validate_manifest(payload)
    except Exception as exc:
        print(f"[update-manifest] FAIL: generated manifest invalid: {exc}",
              file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[update-manifest] OK: {out} "
          f"({file_name}, {size} bytes, sha256={sha256[:16]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
