#!/usr/bin/env python3
"""Guard: the site's contributor list must match the all-contributors source.

The live contributors view (docs/terminal/*) reads ``docs/contributors.json``,
which is a mirror of the ``contributors`` array in ``.all-contributorsrc`` (the
file the all-contributors workflow updates, and which drives ``CONTRIBUTORS.md``).
These two drifted once — a contributor added to ``.all-contributorsrc`` was
missing from the site — so this test keeps them in lockstep.
"""

import json
import os

_REPO = os.path.join(os.path.dirname(__file__), "..")


def _load(*parts):
    with open(os.path.join(_REPO, *parts), encoding="utf-8") as f:
        return json.load(f)


def test_site_contributors_match_all_contributorsrc():
    arc = _load(".all-contributorsrc")["contributors"]
    site = _load("docs", "contributors.json")["contributors"]

    arc_logins = [c["login"] for c in arc]
    site_logins = [c["login"] for c in site]
    missing_on_site = set(arc_logins) - set(site_logins)
    extra_on_site = set(site_logins) - set(arc_logins)

    assert not missing_on_site, (
        f"contributors in .all-contributorsrc but missing from "
        f"docs/contributors.json: {sorted(missing_on_site)}"
    )
    assert not extra_on_site, (
        f"contributors on the site but not in .all-contributorsrc: "
        f"{sorted(extra_on_site)}"
    )
    # Full parity (order + fields) so the site never shows a stale roster.
    assert site == arc


def test_contributors_json_is_wellformed():
    site = _load("docs", "contributors.json")["contributors"]
    assert site, "docs/contributors.json has no contributors"
    for c in site:
        assert {"login", "name", "avatar_url", "profile", "contributions"} <= set(c)
        assert c["contributions"], f"{c['login']} has no contributions"
