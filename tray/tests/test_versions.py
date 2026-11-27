"""
test_versions.py — The release-tag ordering rule (versions.py).

Must agree with get.sh's git version sort; the sample list and expected order
are the same as in testing/test-installer-guards.sh.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import versions

# Same tags and order as testing/test-installer-guards.sh ("sample order").
SAMPLE = ["v0.4.1", "v0.5.0", "v2.0.0-beta1", "v2.0.0-beta2", "v2.0.0-rc1",
          "v2.0.0", "v2.0.1", "v2.1.0-beta1", "backup-x"]
GET_SH_ORDER = ["v2.1.0-beta1", "v2.0.1", "v2.0.0", "v2.0.0-rc1", "v2.0.0-beta2",
                "v2.0.0-beta1", "v0.5.0", "v0.4.1"]


def test_order_matches_get_sh():
    releases = [t for t in SAMPLE if versions.is_release_tag(t)]
    assert sorted(releases, key=versions.parse, reverse=True) == GET_SH_ORDER


def test_latest_of_sample():
    assert versions.latest(SAMPLE) == "v2.1.0-beta1"


@pytest.mark.parametrize("lower, higher", [
    ("v0.5.0",       "v2.0.0-beta1"),
    ("v2.0.0-beta1", "v2.0.0-beta2"),
    ("v2.0.0-beta2", "v2.0.0-rc1"),
    ("v2.0.0-rc1",   "v2.0.0"),
    ("v2.0.0",       "v2.0.1"),
    ("v2.0.0-alpha3", "v2.0.0-beta1"),
    ("v2.0.0-beta9", "v2.0.0-beta10"),   # numeric, not lexicographic
    ("v0.1.9",       "v0.1.10"),
])
def test_pairwise(lower, higher):
    assert versions.parse(lower) < versions.parse(higher)


def test_v_prefix_optional():
    assert versions.parse("2.0.0-beta1") == versions.parse("v2.0.0-beta1")


@pytest.mark.parametrize("bad", ["", "unknown", "nightly", "backup-x", "v",
                                 "0.1.x", "v2.0.0-foo1", "v2.0.0-beta1x", None])
def test_unparseable_is_none(bad):
    assert versions.parse(bad) is None


def test_unparseable_tags_skipped_not_zero():
    assert versions.latest(["backup-x", "nightly", "v0.0.1"]) == "v0.0.1"
    assert versions.latest(["backup-x", "nightly"]) is None
    assert versions.latest([]) is None


def test_only_v_digit_tags_are_releases():
    # get.sh lists 'v[0-9]*' only; a bare '9.9.9' tag is not a release.
    assert versions.latest(["9.9.9", "v0.5.0"]) == "v0.5.0"
