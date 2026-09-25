#!/usr/bin/env python3
"""The committed signal-parity fixture must match the Python matcher it was generated from.

site/src/lib/signals.js is tested against site/test/fixtures/signal-parity.json;
this guard fails when ngj.filters changes without re-running
scripts/export_signal_parity.py, so the two implementations cannot drift apart silently.
"""

import json

from export_signal_parity import FIXTURE_PATH, build_fixture


def test_committed_parity_fixture_is_current():
    committed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert committed == build_fixture(), "run scripts/export_signal_parity.py and commit the fixture"


def test_fixture_covers_every_matcher_and_is_well_formed():
    fixture = build_fixture()
    assert len(fixture["new_grad"]) == len(fixture["titles"])
    assert all(len(row) == len(fixture["signals"]) for row in fixture["new_grad"] + fixture["track"])
    assert all(len(row) == len(fixture["exclusions"]) for row in fixture["excluded"])
    # Sanity: the fixture exercises both outcomes of each matcher.
    for key in ("new_grad", "track", "excluded"):
        flat = [v for row in fixture[key] for v in row]
        assert True in flat and False in flat, key
