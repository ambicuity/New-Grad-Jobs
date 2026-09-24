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


# --------------------------------------------------------------------------- #
# Comment escaping (issue titles are attacker-controlled)
# --------------------------------------------------------------------------- #
def test_format_title_wraps_in_code_span_and_strips_backticks():
    out = dd.format_title("@everyone `rm -rf` [click](https://evil.example)\n# heading")
    assert out.startswith("`") and out.endswith("`")
    assert out.count("`") == 2  # inner backticks removed; span cannot be closed early
    assert "\n" not in out
    assert "@everyone" in out  # kept, but inert inside the code span


def test_format_title_handles_empty_and_long_titles():
    assert dd.format_title(None) == "_(untitled)_"
    assert dd.format_title("  `` ") == "_(untitled)_"
    long = dd.format_title("x" * 500)
    assert len(long) <= dd._MAX_TITLE_CHARS + 2
    assert long.endswith("…`")


def test_build_comment_escapes_mentions_and_markdown():
    candidates = [({"number": 7, "title": "@maintainer **pwn** `x`", "state": "open"}, 0.9)]
    body = dd.build_comment(candidates)
    line = next(ln for ln in body.splitlines() if ln.startswith("- #7"))
    assert "`@maintainer **pwn** x`" in line


def test_build_comment_normalizes_unknown_state():
    candidates = [({"number": 8, "title": "t", "state": "<b>weird</b>"}, 0.6)]
    assert "<b>" not in dd.build_comment(candidates)


# --------------------------------------------------------------------------- #
# API glue with a stubbed transport
# --------------------------------------------------------------------------- #
def test_already_flagged_paginates_until_marker_found(monkeypatch):
    requested = []

    def fake_request(method, url, token, payload=None):
        requested.append(url)
        if "page=1" in url:
            return [{"body": "unrelated"}] * dd._PER_PAGE
        return [{"body": f"hi {dd.COMMENT_MARKER}"}]

    monkeypatch.setattr(dd, "_request", fake_request)
    assert dd._already_flagged("o/r", "t", 3) is True
    assert any("page=2" in u for u in requested)


def test_already_flagged_stops_on_short_page(monkeypatch):
    calls = []

    def fake_request(method, url, token, payload=None):
        calls.append(url)
        return [{"body": "nothing here"}]

    monkeypatch.setattr(dd, "_request", fake_request)
    assert dd._already_flagged("o/r", "t", 3) is False
    assert len(calls) == 1


def _set_env(monkeypatch, number="12"):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("ISSUE_NUMBER", number)


@pytest.mark.parametrize(
    "exc",
    [
        dd.urllib.error.URLError("dns failure"),
        dd.urllib.error.HTTPError("https://api.github.com", 502, "bad gateway", None, None),
        TimeoutError("read timed out"),
    ],
)
def test_main_swallows_network_errors(monkeypatch, capsys, exc):
    _set_env(monkeypatch)

    def boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(dd, "_request", boom)
    assert dd.main() == 0
    assert "GitHub API request failed" in capsys.readouterr().out


def test_main_rejects_non_numeric_issue_number(monkeypatch, capsys):
    _set_env(monkeypatch, number="abc")
    assert dd.main() == 0
    assert "Invalid numeric setting" in capsys.readouterr().out


def test_main_posts_escaped_comment_for_duplicate(monkeypatch):
    _set_env(monkeypatch)
    target = {"number": 12, "title": "Add duplicate issue guardrail", "body": "detect duplicate issues"}
    other = {"number": 5, "title": "Add duplicate issue guardrail @someone", "body": "detect duplicate issues"}
    posts = []

    def fake_request(method, url, token, payload=None):
        if method == "POST":
            posts.append((url, payload))
            return {}
        if url.endswith("/issues/12"):
            return target
        if "/issues?" in url:
            return [target, other] if "page=1" in url else []
        if "/comments" in url:
            return []
        return {}  # label lookup: already exists

    monkeypatch.setattr(dd, "_request", fake_request)
    assert dd.main() == 0
    comment = next(p for u, p in posts if u.endswith("/comments"))["body"]
    assert "`Add duplicate issue guardrail @someone`" in comment
    assert any(u.endswith("/labels") for u, _ in posts)
