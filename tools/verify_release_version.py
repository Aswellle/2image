#!/usr/bin/env python3
"""
tools/verify_release_version.py — release consistency gate (CI)
───────────────────────────────────────────────────────────────
Fails the release build unless ALL of the following hold:

  1. the tag matches vMAJOR.MINOR.PATCH
  2. version.json version == tag without the leading "v"
  3. release-notes/v<version>.md exists
  4. (--min-version given) the tag is strictly greater than the latest
     already-published stable version

A release whose tag and version.json disagree must never be built —
the updater and the manifest both rely on them being identical.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.updater.version import parse_version  # noqa: E402

TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="verify_release_version",
        description="Verify tag / version.json / release notes consistency")
    parser.add_argument("--tag", help="release tag (vX.Y.Z); "
                                      "defaults to $GITHUB_REF_NAME")
    parser.add_argument("--min-version", default="",
                        help="latest published stable version; the new tag "
                             "must be strictly greater")
    args = parser.parse_args()

    tag = args.tag or __import__("os").environ.get("GITHUB_REF_NAME", "")
    problems: list[str] = []

    if not TAG_RE.match(tag or ""):
        problems.append(f"tag {tag!r} does not match vX.Y.Z")
        version = None
    else:
        version = tag[1:]

    if version is not None:
        try:
            declared = json.loads(
                (ROOT / "version.json").read_text(encoding="utf-8"))["version"]
            if str(declared).strip() != version:
                problems.append(
                    f"version.json says {declared!r} but tag is {tag!r}")
        except Exception as exc:
            problems.append(f"cannot read version.json: {exc}")

        notes = ROOT / "release-notes" / f"v{version}.md"
        if not notes.is_file():
            problems.append(f"release notes missing: {notes}")

    if args.min_version:
        try:
            if version is not None and not (
                    parse_version(tag) > parse_version(args.min_version)):
                problems.append(
                    f"{tag} is not newer than published {args.min_version}")
        except ValueError as exc:
            problems.append(f"min-version invalid: {exc}")

    if problems:
        for problem in problems:
            print(f"[verify-release] FAIL: {problem}", file=sys.stderr)
        return 1
    print(f"[verify-release] OK: tag={tag} version.json and release notes "
          f"consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
