#!/usr/bin/env python3
"""Automated duplicate-issue guardrail (resolves #230).

On issue ``opened``/``edited`` this script compares the triggering issue against
recent open **and** closed issues. When it finds highly similar issues it:

  * adds the ``possible-duplicate`` label (creating it if missing), and
  * posts a single, non-destructive comment listing the candidate duplicates.

The final decision stays with a human — nothing is ever auto-closed. The text
similarity is computed with the standard library only (``difflib`` +
token-set overlap), so there is no external database, service, or orchestrator.

The pure functions (``normalize_text``, ``tokenize``, ``similarity_score``,
``find_duplicate_candidates``) are import-safe and unit-tested; the GitHub API
calls only run under ``main()``.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

# Tunables (overridable via workflow env).
DEFAULT_THRESHOLD = 0.55
DEFAULT_MAX_CANDIDATES = 5
DEFAULT_LOOKBACK = 200  # most recent issues to compare against

# Marker kept in the bot comment so repeated "edited" events stay idempotent.
COMMENT_MARKER = "<!-- possible-duplicate-guardrail -->"
DUPLICATE_LABEL = "possible-duplicate"

_STOPWORDS = frozenset(
    """
    a an the and or but if then else for to of in on at by with without from into
    is are was were be been being this that these those it its as we you they i
    add adds added make makes making fix fixes fixed feature bug issue please
    should would could when where which what how why not no yes can will
    """.split()
)

_URL_RE = re.compile(r"https?://\S+")
_CODEBLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_NONWORD_RE = re.compile(r"[^a-z0-9\s]+")
_WS_RE = re.compile(r"\s+")


def normalize_text(text: Optional[str]) -> str:
    """Lowercase and strip URLs, code blocks, markdown, and punctuation."""
    if not text:
        return ""
    text = text.lower()
    text = _CODEBLOCK_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = _NONWORD_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def tokenize(text: Optional[str]) -> frozenset:
    """Return a set of meaningful tokens (length >= 3, minus stopwords)."""
    normalized = normalize_text(text)
    return frozenset(
        tok for tok in normalized.split() if len(tok) >= 3 and tok not in _STOPWORDS
    )


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity_score(
    title_a: str, body_a: str, title_b: str, body_b: str
) -> float:
    """Combined title + body similarity in ``[0, 1]``.

    Title similarity (sequence ratio on normalized titles) is weighted most,
    since near-duplicate issues almost always share a title. Body similarity
    uses token-set overlap so wording/order differences don't hide a match.
    """
    nt_a, nt_b = normalize_text(title_a), normalize_text(title_b)
    title_ratio = SequenceMatcher(None, nt_a, nt_b).ratio() if nt_a and nt_b else 0.0
    title_tokens = _jaccard(tokenize(title_a), tokenize(title_b))
    body_tokens = _jaccard(
        tokenize(f"{title_a} {body_a}"), tokenize(f"{title_b} {body_b}")
    )
    return round(0.5 * title_ratio + 0.2 * title_tokens + 0.3 * body_tokens, 4)


def find_duplicate_candidates(
    target: Dict[str, Any],
    others: List[Dict[str, Any]],
    threshold: float = DEFAULT_THRESHOLD,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> List[Tuple[Dict[str, Any], float]]:
    """Return ``[(issue, score), ...]`` above ``threshold``, best first.

    ``target``/``others`` are dicts with ``number``, ``title``, ``body`` keys.
    The target itself (matching ``number``) is always excluded.
    """
    target_title = target.get("title", "") or ""
    target_body = target.get("body", "") or ""
    target_number = target.get("number")

    scored: List[Tuple[Dict[str, Any], float]] = []
    for other in others:
        if other.get("number") == target_number:
            continue
        score = similarity_score(
            target_title, target_body, other.get("title", "") or "", other.get("body", "") or ""
        )
        if score >= threshold:
            scored.append((other, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:max_candidates]


def build_comment(candidates: List[Tuple[Dict[str, Any], float]]) -> str:
    """Render the maintainer-friendly comment body."""
    lines = [
        COMMENT_MARKER,
        "🔁 **Possible duplicate detected**",
        "",
        "This issue looks similar to the following existing issue(s). "
        "A maintainer will confirm — this is only a heads-up, nothing is closed automatically:",
        "",
    ]
    for issue, score in candidates:
        state = issue.get("state", "open")
        lines.append(
            f"- #{issue['number']} — {issue.get('title', '').strip()} "
            f"_(similarity {int(round(score * 100))}%, {state})_"
        )
    lines += [
        "",
        "If this is **not** a duplicate, please remove the "
        f"`{DUPLICATE_LABEL}` label or leave a comment explaining the difference.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# GitHub API glue (only exercised in the workflow, not in unit tests)
# --------------------------------------------------------------------------- #
_API_ROOT = "https://api.github.com"


def _request(method: str, url: str, token: str, payload: Optional[dict] = None) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "duplicate-issue-guardrail")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
    return json.loads(body) if body else None


def _fetch_recent_issues(repo: str, token: str, lookback: int) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    page = 1
    while len(issues) < lookback and page <= 5:
        url = (
            f"{_API_ROOT}/repos/{repo}/issues"
            f"?state=all&per_page=100&page={page}&sort=created&direction=desc"
        )
        batch = _request("GET", url, token) or []
        if not batch:
            break
        # Skip pull requests (the issues endpoint returns both).
        issues.extend(i for i in batch if "pull_request" not in i)
        page += 1
    return issues[:lookback]


def _ensure_label(repo: str, token: str) -> None:
    """Create the possible-duplicate label if it does not already exist."""
    try:
        _request("GET", f"{_API_ROOT}/repos/{repo}/labels/{DUPLICATE_LABEL}", token)
        return  # already exists
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    payload = {
        "name": DUPLICATE_LABEL,
        "color": "cfd3d7",
        "description": "This issue may be a duplicate — needs confirmation",
    }
    try:
        _request("POST", f"{_API_ROOT}/repos/{repo}/labels", token, payload)
    except urllib.error.HTTPError as exc:
        if exc.code != 422:  # already exists (race)
            raise


def _already_flagged(repo: str, token: str, number: int) -> bool:
    comments = _request(
        "GET", f"{_API_ROOT}/repos/{repo}/issues/{number}/comments?per_page=100", token
    ) or []
    return any(COMMENT_MARKER in (c.get("body") or "") for c in comments)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    number_raw = os.environ.get("ISSUE_NUMBER", "")
    if not (token and repo and number_raw):
        print("Missing GITHUB_TOKEN / GITHUB_REPOSITORY / ISSUE_NUMBER; skipping.")
        return 0

    threshold = float(os.environ.get("DUP_THRESHOLD", DEFAULT_THRESHOLD))
    max_candidates = int(os.environ.get("DUP_MAX_CANDIDATES", DEFAULT_MAX_CANDIDATES))
    lookback = int(os.environ.get("DUP_LOOKBACK", DEFAULT_LOOKBACK))
    number = int(number_raw)

    try:
        target = _request("GET", f"{_API_ROOT}/repos/{repo}/issues/{number}", token)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network guard
        print(f"Could not fetch issue #{number}: {exc}")
        return 0
    if not target or "pull_request" in target:
        print("Trigger is not an issue; skipping.")
        return 0

    others = _fetch_recent_issues(repo, token, lookback)
    candidates = find_duplicate_candidates(target, others, threshold, max_candidates)
    if not candidates:
        print(f"No likely duplicates for issue #{number}.")
        return 0

    if _already_flagged(repo, token, number):
        print(f"Issue #{number} already flagged; not re-commenting.")
        return 0

    _ensure_label(repo, token)
    try:
        _request(
            "POST",
            f"{_API_ROOT}/repos/{repo}/issues/{number}/labels",
            token,
            {"labels": [DUPLICATE_LABEL]},
        )
        _request(
            "POST",
            f"{_API_ROOT}/repos/{repo}/issues/{number}/comments",
            token,
            {"body": build_comment(candidates)},
        )
    except urllib.error.HTTPError as exc:  # pragma: no cover - network guard
        print(f"Failed to annotate issue #{number}: {exc}")
        return 0

    listed = ", ".join(f"#{i['number']}({int(round(s * 100))}%)" for i, s in candidates)
    print(f"Flagged issue #{number} as possible duplicate of: {listed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
