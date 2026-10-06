"""
services/updater/version.py — current version source + SemVer compare
─────────────────────────────────────────────────────────────────────
Comparison is numeric per SemVer — never plain string comparison, so
"2.10.0" correctly outranks "2.9.0".  A leading "v"/"V" and a
pre-release suffix ("-beta.1") are tolerated; a release always
outranks a pre-release of the same triple.  Downgrades are refused by
``is_newer`` returning False.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from functools import total_ordering

_SEMVER_RE = re.compile(
    r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z][0-9A-Za-z.\-]*))?$")


class VersionError(ValueError):
    """The given text is not a valid SemVer version."""


@dataclass(frozen=True, eq=True)
@total_ordering
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple = ()

    def _cmp_key(self):
        # Per SemVer: pre-release < release for the same triple.  Encode
        # that as a leading rank (release=2 beats pre-release=1); the
        # identifiers themselves compare numerically when numeric and
        # alphanumerically otherwise, with numeric < alphanumeric.
        pre_key = tuple(
            (0, int(p), "") if p.isdigit() else (1, 0, p)
            for p in self.prerelease)
        return (self.major, self.minor, self.patch,
                2 if not self.prerelease else 1, pre_key)

    def __lt__(self, other):
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._cmp_key() < other._cmp_key()

    def __str__(self) -> str:
        core = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            core += "-" + ".".join(self.prerelease)
        return core


def parse_version(text: str) -> SemVer:
    """Parse "v2.6.1" / "2.6.1" / "2.7.0-beta.1"; raise VersionError otherwise."""
    m = _SEMVER_RE.match(str(text or "").strip())
    if not m:
        raise VersionError(f"invalid SemVer: {text!r}")
    major, minor, patch = (int(g) for g in m.groups()[:3])
    pre = tuple(m.group(4).split(".")) if m.group(4) else ()
    return SemVer(major, minor, patch, pre)


def is_newer(latest: str, current: str) -> bool:
    """True only when ``latest`` parses strictly greater than ``current``.

    Unparsable input on either side yields False (fail-safe: never
    downgrade, never false-positive an update).
    """
    try:
        return parse_version(latest) > parse_version(current)
    except VersionError:
        return False


def is_packaged() -> bool:
    """True when running as a PyInstaller-frozen executable."""
    return bool(getattr(sys, "frozen", False))


def get_current_version() -> str:
    """Current app version.

    In packaged builds version.json is bundled next to the executable
    via PyInstaller ``datas`` (``sys._MEIPASS``); from source the repo
    root copy is used.  Unreadable/missing files fall back to "0.0.0"
    so update checks can never crash the app.
    """
    candidates = []
    if is_packaged():
        candidates.append(
            __import__("os").path.join(
                getattr(sys, "_MEIPASS", "."), "version.json"))
    candidates.append(str(_repo_root() / "version.json"))
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                ver = str(json.load(fh)["version"]).strip()
            if ver:
                return ver
        except Exception:
            continue
    return "0.0.0"


def _repo_root():
    return __import__("pathlib").Path(__file__).resolve().parents[2]
