"""SemVer parsing/comparison matrix (§28.1): numeric compare, prerelease
ordering, downgrade refusal, invalid input rejection."""
import pytest

from services.updater import is_newer
from services.updater.version import (
    SemVer,
    VersionError,
    get_current_version,
    parse_version,
)


# ── parse ────────────────────────────────────────────────────

def test_parse_plain_and_v_prefix():
    assert parse_version("2.6.1") == SemVer(2, 6, 1)
    assert parse_version("v2.6.1") == SemVer(2, 6, 1)
    assert parse_version(" V3.0.0 ") == SemVer(3, 0, 0)


def test_parse_prerelease():
    v = parse_version("2.7.0-beta.1")
    assert (v.major, v.minor, v.patch) == (2, 7, 0)
    assert v.prerelease == ("beta", "1")


@pytest.mark.parametrize("bad", ["", "2.6", "2.6.x", "abc", "v2", "2.6.1.2"])
def test_parse_invalid_raises(bad):
    with pytest.raises(VersionError):
        parse_version(bad)


# ── compare ──────────────────────────────────────────────────

def test_compare_numeric_not_lexicographic():
    assert is_newer("2.10.0", "2.9.0") is True
    assert is_newer("v2.10.0", "2.9.9") is True
    assert is_newer("0.10.0", "0.9.0") is True


def test_equal_is_not_newer():
    assert is_newer("2.6.1", "2.6.1") is False


def test_downgrade_refused():
    assert is_newer("2.5.9", "2.6.0") is False
    assert is_newer("v1.0.0", "2.6.0") is False


def test_prerelease_lower_than_release():
    assert parse_version("2.7.0-beta.1") < parse_version("2.7.0")
    assert is_newer("2.7.0-beta.1", "2.7.0") is False


def test_prerelease_identifier_semantics():
    assert parse_version("1.0.0-alpha.2") > parse_version("1.0.0-alpha.1")
    assert parse_version("1.0.0-alpha.2") < parse_version("1.0.0-alpha.10")
    assert parse_version("1.0.0-alpha") < parse_version("1.0.0-alpha.1")
    assert parse_version("1.0.0-alpha") < parse_version("1.0.0-beta")
    assert parse_version("1.0.0-alpha.1") < parse_version("1.0.0-alpha.beta")


def test_is_newer_invalid_input_fails_safe():
    assert is_newer("not-a-version", "2.6.0") is False
    assert is_newer("2.7.0", "") is False


def test_get_current_version_shape():
    ver = get_current_version()
    assert ver == "0.0.0" or parse_version(ver)
