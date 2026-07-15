#!/usr/bin/env python3
"""Tests for the duplicate-issue guardrail logic (.github/scripts).

Only the pure, network-free functions are exercised here: text normalization,
similarity scoring, and candidate selection. The GitHub API glue lives behind
``main()`` and is not imported.
"""

import importlib.util
import os

import pytest

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__), '..', '.github', 'scripts', 'detect_duplicate_issues.py'
)


def _load():
    spec = importlib.util.spec_from_file_location('detect_duplicate_issues', _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dd = _load()


def test_normalize_strips_urls_code_and_punctuation():
    raw = "Add `.editorconfig`!! see https://example.com/x ```code```"
    out = dd.normalize_text(raw)
    assert 'http' not in out and '`' not in out and '!' not in out
    assert 'editorconfig' in out


def test_tokenize_drops_stopwords_and_short_tokens():
    tokens = dd.tokenize("Add an editorconfig file to the repo")
    assert 'editorconfig' in tokens
    assert 'an' not in tokens and 'to' not in tokens and 'the' not in tokens


def test_identical_titles_score_high():
    score = dd.similarity_score(
        "Add an .editorconfig file", "standardize formatting",
        "Add an .editorconfig file", "standardize formatting",
    )
    assert score > 0.95


def test_paraphrased_duplicate_scores_above_threshold():
    # Wording mirrors how real duplicate issues in this repo are phrased:
    # they share the key noun phrases even when reworded (calibrated against
    # actual repo issue pairs such as #20~#14 and #26~#17).
    score = dd.similarity_score(
        "Add automated duplicate-issue guardrail for triage quality",
        "detect near-duplicate issues on open and add a possible-duplicate label; keep decision manual",
        "Add automated duplicate issue guardrail to improve triage",
        "detect duplicate issues when opened and apply a possible-duplicate label; no auto close",
    )
    assert score >= dd.DEFAULT_THRESHOLD


def test_unrelated_issues_score_low():
    score = dd.similarity_score(
        "Add publish-time URL safety validation",
        "reject localhost and private IPs before writing jobs.json",
        "Update the README contributor list",
        "add new contributors to the hall of fame table",
    )
    assert score < dd.DEFAULT_THRESHOLD


def test_find_candidates_excludes_self_and_ranks():
    target = {"number": 10, "title": "Add duplicate issue guardrail",
              "body": "detect duplicate issues and label them"}
    others = [
        {"number": 10, "title": "Add duplicate issue guardrail",
         "body": "detect duplicate issues and label them"},   # self -> excluded
        {"number": 5, "title": "Add duplicate-issue detection guardrail",
         "body": "automatically find duplicate issues and label"},  # strong match
        {"number": 6, "title": "Fix typo in README", "body": "small doc fix"},  # no match
    ]
    candidates = dd.find_duplicate_candidates(target, others)
    numbers = [issue["number"] for issue, _ in candidates]
    assert 10 not in numbers
    assert numbers and numbers[0] == 5


def test_build_comment_contains_marker_and_numbers():
    candidates = [({"number": 42, "title": "Some issue", "state": "closed"}, 0.73)]
    body = dd.build_comment(candidates)
    assert dd.COMMENT_MARKER in body
    assert "#42" in body
    assert "73%" in body


def test_empty_others_returns_no_candidates():
    target = {"number": 1, "title": "anything", "body": "text"}
    assert dd.find_duplicate_candidates(target, []) == []
