#!/usr/bin/env python3
"""Tests for the config URL extractor in .github/scripts/verify_new_urls.py.

The script is the CI gate that verifies newly added ATS URLs in config.yml are
reachable. These tests lock in the diff-parsing behaviour so the gate keeps
matching the intended keys (and only those) across quoted, unquoted, and
commented-out lines.
"""

import importlib.util
import os

import pytest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')
_MODULE_PATH = os.path.join(_REPO_ROOT, '.github', 'scripts', 'verify_new_urls.py')


def _load_module():
    """Load verify_new_urls.py by path (it lives outside the scripts/ package)."""
    import sys

    sys.path.insert(0, os.path.abspath(_REPO_ROOT))
    spec = importlib.util.spec_from_file_location('verify_new_urls', _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - dependency import guard
        pytest.skip(f"verify_new_urls could not be imported: {exc}")
    return module


verify_new_urls = _load_module()
get_new_urls_from_diff = verify_new_urls.get_new_urls_from_diff


def _diff(*lines):
    return "\n".join(lines)


def test_matches_standard_quoted_url():
    diff = _diff('+        url: "https://boards.greenhouse.io/acme"')
    assert get_new_urls_from_diff(diff) == ['https://boards.greenhouse.io/acme']


def test_matches_single_quoted_url():
    diff = _diff("+        url: 'https://jobs.lever.co/acme'")
    assert get_new_urls_from_diff(diff) == ['https://jobs.lever.co/acme']


def test_matches_unquoted_yaml_url():
    """YAML allows unquoted scalars; the gate must still verify them."""
    diff = _diff('+        url: https://unquoted.example.com')
    assert get_new_urls_from_diff(diff) == ['https://unquoted.example.com']


def test_matches_workday_and_endpoint_keys():
    diff = _diff(
        '+        workday_url: "https://acme.wd1.myworkdayjobs.com/x"',
        '+        endpoint: "https://api.example.com/graphql"',
    )
    assert set(get_new_urls_from_diff(diff)) == {
        'https://acme.wd1.myworkdayjobs.com/x',
        'https://api.example.com/graphql',
    }


def test_matches_url_with_no_space_after_quote():
    """Regression for the original bug: the old regex required a literal space."""
    diff = _diff('+        url: "https://no-space.example.com"')
    assert get_new_urls_from_diff(diff) == ['https://no-space.example.com']


@pytest.mark.parametrize('key', ['callback_url', 'source_url', 'redirect_url'])
def test_ignores_similarly_named_keys(key):
    """Keys that merely end in `url` must not be treated as ATS URL fields."""
    diff = _diff(f'+        {key}: "https://not-an-ats.example.com"')
    assert get_new_urls_from_diff(diff) == []


def test_ignores_commented_out_lines():
    diff = _diff('+        # url: "https://malicious.example.com"')
    assert get_new_urls_from_diff(diff) == []


def test_ignores_context_and_removed_lines():
    diff = _diff(
        '         url: "https://context.example.com"',
        '-        url: "https://removed.example.com"',
        '+++ b/config.yml',
    )
    assert get_new_urls_from_diff(diff) == []


def test_deduplicates_repeated_urls():
    diff = _diff(
        '+        url: "https://dup.example.com"',
        '+        url: "https://dup.example.com"',
    )
    assert get_new_urls_from_diff(diff) == ['https://dup.example.com']
