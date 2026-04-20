import pytest

from skills_inventory.versions import (
    highest_tag,
    normalize_tag,
    parse_semver,
    sort_semver_tags_desc,
)


def test_parse_semver_accepts_plain_and_v_prefix():
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("v1.2.3") == (1, 2, 3)


def test_parse_semver_rejects_non_core_formats():
    assert parse_semver("1.2") is None
    assert parse_semver("1.2.3.4") is None
    assert parse_semver("v1.2.3-beta.1") is None
    assert parse_semver("abc") is None


def test_normalize_tag_returns_plain_triplet():
    assert normalize_tag("10.20.30") == "10.20.30"
    assert normalize_tag("v10.20.30") == "10.20.30"


def test_normalize_tag_raises_for_invalid():
    with pytest.raises(ValueError):
        normalize_tag("v1.2")


def test_sort_semver_tags_desc_filters_invalid_and_sorts():
    tags = ["foo", "v1.2.0", "1.10.0", "1.2.9", "v2.0.0", "1.2"]
    assert sort_semver_tags_desc(tags) == ["v2.0.0", "1.10.0", "1.2.9", "v1.2.0"]


def test_highest_tag_returns_normalized_highest():
    tags = ["foo", "v1.2.0", "1.10.0", "1.2.9"]
    assert highest_tag(tags) == "1.10.0"


def test_highest_tag_returns_none_when_no_valid_tags():
    assert highest_tag(["foo", "bar"]) is None
