"""
versions.py — Release-tag ordering for source installs.

The shared ordering rule. get.sh picks the release to install with

    git -c versionsort.suffix=-alpha -c versionsort.suffix=-beta \\
        -c versionsort.suffix=-rc tag --list 'v[0-9]*' --sort=-version:refname

and the tray's update check (updater.py) must rank tags exactly the same way.
If the two disagree, the tray offers a tag that get.sh will not install, and
the offer comes back after every "update" — a loop. Change both together;
testing/test-installer-guards.sh pins get.sh's order and
tray/tests/test_versions.py pins this one, on the same sample list.

The rule:
  • A release tag is 'v' + dotted numbers, optionally followed by
    -alphaN, -betaN or -rcN (N optional, e.g. v2.0.0-beta1, v2.0.0-rc).
  • Numbers compare numerically (0.1.10 > 0.1.9).
  • Pre-releases sort below their release, alpha < beta < rc, then by N:
      v0.5.0 < v2.0.0-beta1 < v2.0.0-beta2 < v2.0.0-rc1 < v2.0.0 < v2.0.1
  • Anything else (backup-x, nightly, v2.0.0-foo) is not a release: it is
    skipped, never ranked as 0.

Versions without the leading 'v' (as local_version() returns them) parse the
same way.
"""

import re

_STAGES = {"alpha": 0, "beta": 1, "rc": 2}
_RELEASE = 3  # ranks above every pre-release stage

_VERSION_RE = re.compile(
    r"v?(?P<nums>\d+(?:\.\d+)*)(?:-(?P<stage>alpha|beta|rc)(?P<n>\d*))?"
)


def parse(v: str) -> tuple | None:
    """Sort key for a release version ('2.0.0-beta1' or 'v2.0.0-beta1'),
    or None when v is not a release version."""
    if not isinstance(v, str):
        return None
    m = _VERSION_RE.fullmatch(v.strip())
    if not m:
        return None
    nums = tuple(int(x) for x in m["nums"].split("."))
    if m["stage"]:
        return (nums, _STAGES[m["stage"]], int(m["n"] or 0))
    return (nums, _RELEASE, 0)


def is_release_tag(tag: str) -> bool:
    """True for tags get.sh considers (v<digit>…) that also parse."""
    return tag.startswith("v") and tag[1:2].isdigit() and parse(tag) is not None


def latest(tags) -> str | None:
    """The highest release tag, as named (with its 'v'), or None."""
    ranked = [(parse(t), t) for t in tags if is_release_tag(t)]
    return max(ranked)[1] if ranked else None
