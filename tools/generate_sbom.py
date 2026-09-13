"""
tools/generate_sbom.py — Generate SPDX SBOM and build metadata
──────────────────────────────────────────────────────────────────
Called by CI during release to generate:
  - build-metadata.json (version, git SHA, Python, PyInstaller, timestamp)
  - SBOM.spdx.json (SPDX 2.3 JSON with all Python dependencies)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=os.path.dirname(__file__),
            text=True
        ).strip()
    except Exception:
        return "unknown"


def get_git_tag() -> str:
    try:
        return subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            cwd=os.path.dirname(__file__), text=True
        ).strip()
    except Exception:
        return "unknown"


def get_python_version() -> str:
    return sys.version.split()[0]


def get_pyinstaller_version() -> str:
    try:
        import PyInstaller
        return PyInstaller.__version__
    except Exception:
        return "unknown"


def get_dependencies() -> list[dict]:
    """Get installed pip packages as SPDX packages."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True
        )
        packages = json.loads(result.stdout)
        return [
            {
                "SPDXID": f"SPDXRef-Package-{p['name']}",
                "name": p["name"],
                "versionInfo": p["version"],
                "downloadLocation": "https://pypi.org/project/" + p["name"],
            }
            for p in packages
        ]
    except Exception:
        return []


def generate_sbom(src_dir: str = ".", out_dir: str = "dist") -> dict:
    """Generate build-metadata.json and SBOM.spdx.json."""
    src_path = Path(src_dir).resolve()
    out_path = Path(out_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    # Read version
    version_file = src_path / "version.json"
    version = "0.0.0"
    if version_file.exists():
        version = json.loads(version_file.read_text()).get("version", version)

    # Build metadata
    build_meta = {
        "version": version,
        "git_sha": get_git_sha(),
        "git_tag": get_git_tag(),
        "python": get_python_version(),
        "pyinstaller": get_pyinstaller_version(),
        "build_time": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = out_path / "build-metadata.json"
    meta_path.write_text(json.dumps(build_meta, indent=2), encoding="utf-8")

    # SPDX SBOM
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"text2image-pro-{version}",
        "documentNamespace": f"https://github.com/Aswellle/2image/{version}",
        "creationInfo": {
            "created": datetime.now(timezone.utc).isoformat(),
            "creators": [
                "Tool: text2image-build",
                f"Person: build@{os.environ.get('COMPUTERNAME', 'ci')}",
            ],
        },
        "packages": [
            {
                "SPDXID": "SPDXRef-RootPackage",
                "name": "text2image-pro",
                "versionInfo": version,
                "downloadLocation": "https://github.com/Aswellle/2image",
                "filesAnalyzed": False,
            },
        ] + get_dependencies(),
        "relationships": [],
    }
    sbom_path = out_path / "SBOM.spdx.json"
    sbom_path.write_text(json.dumps(sbom, indent=2), encoding="utf-8")

    print(f"Generated: {meta_path}")
    print(f"Generated: {sbom_path}")
    return build_meta


if __name__ == "__main__":
    generate_sbom()
