# Repo cleanup implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean the local fork of `ambicuity/New-Grad-Jobs` to a minimal state mirroring upstream — remove root-level cruft, stale planning docs, ~36 community-bot workflows, and merged/PR-mirror local branches. No remote operations.

**Architecture:** Six sequential commits on a new branch `chore/repo-cleanup`. Each commit is independently revertable. Verification gate (`pre-commit run --all-files`, `.venv/bin/python -m pytest -q`) runs after every commit.

**Tech Stack:** Python 3.11, pytest, pre-commit, GitHub Actions YAML, git.

**Spec:** [`docs/superpowers/specs/2026-05-18-repo-cleanup-design.md`](../specs/2026-05-18-repo-cleanup-design.md)

---

## Task 0: Set up clean branch

**Files:**
- Branch: create `chore/repo-cleanup` from current `fix/derive-counts-from-data`

- [ ] **Step 0.1: Confirm clean starting state**

Run:

```bash
git status --short
git branch --show-current
```

Expected: current branch is `fix/derive-counts-from-data`. Untracked screenshots and `.playwright-mcp/`, `junit.xml` may be present — that's fine, Task 1 handles them.

- [ ] **Step 0.2: Create cleanup branch**

```bash
git checkout -b chore/repo-cleanup
```

- [ ] **Step 0.3: Snapshot baseline test status**

```bash
.venv/bin/python -m pytest -q 2>&1 | tail -5
```

Record the pass/fail count so later commits can be compared against it. Do NOT proceed if the baseline is broken — fix or document first.

---

## Task 1: Commit 1 — gitignore + cruft purge

**Files:**
- Modify: `.gitignore` (append section)
- Delete tracked: `.DS_Store`, `.url_failures`, `.coverage`, `coverage.xml`, `pr_diff.txt`, `pr_review.md`, `fix.py`
- Delete untracked: `terminal-*.png` (12 files), `.playwright-mcp/`, `__pycache__/`, `.pytest_cache/`, `junit.xml`

- [ ] **Step 1.1: Extend `.gitignore`**

Append to `.gitignore`:

```gitignore

# ============================================================
# Local artifacts (added by repo cleanup 2026-05-18)
# ============================================================
junit.xml
.playwright-mcp/
.url_failures
/terminal-*.png
/pr_diff.txt
/pr_review.md
```

(Note: `.DS_Store`, `__pycache__/`, `.pytest_cache/`, `.coverage`, `coverage.xml` are already covered by existing rules earlier in the file — no need to duplicate.)

- [ ] **Step 1.2: Remove tracked cruft from git**

```bash
git rm -f .DS_Store .url_failures .coverage coverage.xml pr_diff.txt pr_review.md fix.py
```

Expected: 7 files staged for deletion. If any file isn't tracked (`fatal: pathspec '...' did not match any files`), use `rm -f <file>` for that one and continue.

- [ ] **Step 1.3: Remove untracked cruft from working tree**

```bash
rm -f terminal-*.png junit.xml
rm -rf .playwright-mcp __pycache__ .pytest_cache
```

- [ ] **Step 1.4: Verify clean state**

```bash
git status --short
```

Expected: only `.gitignore` modification and the seven file deletions from step 1.2. No untracked `terminal-*.png` or caches remaining.

- [ ] **Step 1.5: Run pre-commit + tests**

```bash
.venv/bin/python -m pytest -q
# pre-commit on staged-only (full --all-files has pre-existing failures unrelated to cleanup):
git diff --cached --name-only | xargs -r .venv/bin/pre-commit run --files
```

Both must pass. If `pre-commit` reformats files, re-run it and re-stage.

- [ ] **Step 1.6: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore local artifacts and purge tracked cruft

Remove tracked .DS_Store, .url_failures, coverage outputs, fix.py,
pr_diff.txt, pr_review.md. Extend .gitignore for the screenshot/
playwright-mcp/junit artifacts created by local tooling."
```

---

## Task 2: Commit 2 — delete stale planning docs and agent meta

**Files:**
- Delete: `ROADMAP.md`, `OPTIMIZATION_CHANGELOG.md`, `PERFORMANCE_OPTIMIZATIONS.md`, `SCALING_TO_1000_COMPANIES.md`, `JOB_SCRAPING_APIS.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.coderabbit.yaml`

- [ ] **Step 2.1: Verify nothing references these docs**

```bash
grep -rln "ROADMAP\.md\|OPTIMIZATION_CHANGELOG\|PERFORMANCE_OPTIMIZATIONS\|SCALING_TO_1000_COMPANIES\|JOB_SCRAPING_APIS\|AGENTS\.md\|GEMINI\.md\|\.cursorrules\|\.coderabbit" \
  --include="*.md" --include="*.yml" --include="*.yaml" --include="*.py" \
  . 2>/dev/null | grep -v "^./docs/superpowers/" | grep -v __pycache__ | grep -v .venv
```

Expected: only matches inside the docs being deleted themselves (self-references), or none at all. If `README.md` or `CONTRIBUTING.md` links to any of these, decide whether to remove the link in this commit or in a follow-up; if removing, edit those files in this commit too.

- [ ] **Step 2.2: Delete the files**

```bash
git rm -f \
  ROADMAP.md OPTIMIZATION_CHANGELOG.md PERFORMANCE_OPTIMIZATIONS.md \
  SCALING_TO_1000_COMPANIES.md JOB_SCRAPING_APIS.md \
  AGENTS.md GEMINI.md \
  .cursorrules .coderabbit.yaml
```

- [ ] **Step 2.3: Run pre-commit + tests**

```bash
.venv/bin/python -m pytest -q
# pre-commit on staged-only (full --all-files has pre-existing failures unrelated to cleanup):
git diff --cached --name-only | xargs -r .venv/bin/pre-commit run --files
```

Both must pass.

- [ ] **Step 2.4: Commit**

```bash
git commit -m "chore: remove stale planning docs and unused agent meta files

Delete ROADMAP, OPTIMIZATION_CHANGELOG, PERFORMANCE_OPTIMIZATIONS,
SCALING_TO_1000_COMPANIES, JOB_SCRAPING_APIS, AGENTS, GEMINI,
.cursorrules, .coderabbit.yaml. Solo fork doesn't need community
planning docs or multi-agent rule files."
```

---

## Task 3: Commit 3 — relocate stray root Python

**Files:**
- Delete: `verify_companies.py`, `purify_config.py` (both have hard-coded absolute paths to local Downloads)
- Move: `test_config.py` → `scripts/validate_config.py`
- Move: `tests/test_test_config.py` → `tests/test_validate_config.py`, update its import
- Modify: `.github/workflows/ci.yml` lines 44, 45, 75

- [ ] **Step 3.1: Delete local-only scripts**

```bash
git rm -f verify_companies.py purify_config.py
```

- [ ] **Step 3.2: Move test_config.py into scripts/**

```bash
git mv test_config.py scripts/validate_config.py
```

- [ ] **Step 3.3: Move the test file**

```bash
git mv tests/test_test_config.py tests/test_validate_config.py
```

- [ ] **Step 3.4: Update the import in the moved test file**

`tests/conftest.py` adds `scripts/` to `sys.path` (verified — line 18: `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))`). So modules inside `scripts/` are imported as top-level, not as `scripts.module`.

Edit `tests/test_validate_config.py` line 3:

Old:

```python
from test_config import validate_config
```

New:

```python
from validate_config import validate_config
```

- [ ] **Step 3.5: Verify pytest can import the renamed module**

```bash
pytest tests/test_validate_config.py -v
```

Expected: all 6 tests pass (`test_validate_config_warning_path`, `_threshold_success`, `_file_not_found`, `_invalid_yaml`, `_missing_required_key`, `_empty_file`).

If `ModuleNotFoundError: No module named 'validate_config'`, double-check `tests/conftest.py` still contains the `sys.path.insert` line. If a `scripts/__init__.py` exists that turns `scripts/` into a package (it does not as of this writing), the import line should be `from scripts.validate_config import validate_config` instead.

- [ ] **Step 3.6: Update ci.yml references**

Edit `.github/workflows/ci.yml`. Three changes:

Line 44 — change step name:

Old:

```yaml
      - name: Syntax check — test_config.py
```

New:

```yaml
      - name: Syntax check — scripts/validate_config.py
```

Line 45 — change py_compile target:

Old:

```yaml
        run: python -m py_compile test_config.py
```

New:

```yaml
        run: python -m py_compile scripts/validate_config.py
```

Line 75 — change invocation:

Old:

```yaml
        run: python test_config.py
```

New:

```yaml
        run: python scripts/validate_config.py
```

- [ ] **Step 3.7: Confirm no stale references**

```bash
grep -rn "test_config\|verify_companies\|purify_config\|fix\.py" \
  --include="*.py" --include="*.yml" --include="*.yaml" \
  --include="Makefile" --include="*.toml" \
  . 2>/dev/null | grep -v __pycache__ | grep -v .venv | grep -v docs/superpowers
```

Expected: no output. Matches inside `docs/superpowers/` (spec and plan files) are fine.

- [ ] **Step 3.8: Run pre-commit + tests**

```bash
.venv/bin/python -m pytest -q
# pre-commit on staged-only (full --all-files has pre-existing failures unrelated to cleanup):
git diff --cached --name-only | xargs -r .venv/bin/pre-commit run --files
python scripts/validate_config.py
```

All three must pass. The validate_config.py invocation will exit non-zero if `config.yml` is below threshold — that's expected current behavior; capture the exit and treat the command as "ran without traceback" rather than "exit 0."

- [ ] **Step 3.9: Commit**

```bash
git commit -m "refactor: move test_config.py to scripts/validate_config.py

Delete local-only verify_companies.py and purify_config.py (both
had absolute paths to ~/Downloads). Rename test_config.py to its
real purpose (scripts/validate_config.py) and update the matching
test file plus ci.yml references."
```

---

## Task 4: Commit 4 — prune CI to solo-minimal set

**Files:**
- Delete 38 workflows in `.github/workflows/` (full list below)
- Delete `.github/workflows/shared/` (markdown only, unreferenced)
- Delete `.release-please-config.json`, `.release-please-manifest.json` (orphaned by release-please.yml deletion)
- Modify: `.github/workflows/ci.yml` (add merged `test` job from tests.yml)
- Modify: `codecov.yml` if it references deleted workflow names

- [ ] **Step 4.1: Add merged `test` job to ci.yml**

Append the following to `.github/workflows/ci.yml` (after the existing `lint-and-validate` job). Keep `permissions: read-all` at file scope; the job opts into the writes it needs.

```yaml

  test:
    name: Run Unit Tests
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run unit tests with coverage
        run: pytest tests/ -v --cov=scripts --cov-report=term-missing --cov-report=xml --junitxml=junit.xml -o junit_family=legacy

      - name: Upload coverage to Codecov
        if: ${{ !cancelled() && secrets.CODECOV_TOKEN != '' }}
        uses: codecov/codecov-action@671740ac38dd9b0130fbe1cec585b89eea48d3de # v5
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          flags: unittests
          name: coverage-report
          fail_ci_if_error: false
          verbose: true

      - name: Upload test results to Codecov
        if: ${{ !cancelled() && secrets.CODECOV_TOKEN != '' }}
        uses: codecov/test-results-action@0fa95f0e1eeaafde2c782583b36b28ad0d8c77d3 # v1
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          flags: unittests
```

Also extend the existing top-of-file `on.push.paths` to include `tests/**` so the test job triggers on test changes. Edit `.github/workflows/ci.yml` near line 8:

Old:

```yaml
    paths:
      - 'scripts/**'
      - 'config.yml'
      - 'requirements.txt'
      - '.github/workflows/**'
```

New:

```yaml
    paths:
      - 'scripts/**'
      - 'tests/**'
      - 'config.yml'
      - 'requirements.txt'
      - 'pyproject.toml'
      - '.github/workflows/**'
```

- [ ] **Step 4.2: Validate ci.yml YAML syntax locally**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

Expected: no output (silent success). If a `yaml.YAMLError` is raised, fix indentation.

- [ ] **Step 4.3: Delete the 38 workflows + shared dir**

```bash
cd .github/workflows && git rm -f \
  all-contributors.yml auto-merge-scraper.yml auto-thank.yml \
  bot-gfi-candidate-notify.yml bot-linked-issue-enforcer.yml \
  bot-merge-conflict.yml bot-pr-draft-ready-reminder.yml \
  bot-pr-inactivity-reminder.yml bot-pr-protected-files.yml \
  bot-pr-test-reminder.yml bot-pr-title-check.yml check-links.yml \
  daily-backlog-burner.lock.yml daily-backlog-burner.md \
  daily-test-improver.lock.yml daily-test-improver.md \
  dependabot-auto-merge.yml evaluate-jobs.yml first-interaction.yml \
  generate-contributors.yml issue-ops.yml \
  issue-triage-agent.lock.yml issue-triage-agent.md \
  pipeline-integrity.yml pr-auto-merge.yml pr-fix.lock.yml \
  pr-fix.md pr-size.yml reaper-bot.yml release-please.yml \
  sbom.yml scorecard.yml slash-commands.yml stale.yml \
  tests.yml trivy.yml validate-submissions.yml watchdog.yml \
&& git rm -rf shared/ \
&& cd ../..
```

- [ ] **Step 4.4: Delete orphaned release-please config**

```bash
git rm -f .release-please-config.json .release-please-manifest.json
```

- [ ] **Step 4.5: Inspect codecov.yml for references to removed workflows**

```bash
grep -nE "tests\.yml|evaluate-jobs|all-contributors|release-please|generate-contributors|pipeline-integrity" codecov.yml || echo "no stale refs"
```

If matches exist, open `codecov.yml` and remove the offending lines (flags, ignore patterns, status checks referring to deleted workflow names). If `"no stale refs"` prints, skip the edit.

- [ ] **Step 4.6: Verify the kept workflow set**

```bash
ls .github/workflows/
```

Expected output (exactly 5 files):

```text
ci.yml
codeql.yml
pages-deployment.yml
pre-commit.yml
update-jobs.yml
```

- [ ] **Step 4.7: Verify no kept workflow references a deleted one**

```bash
for f in .github/workflows/*.yml; do
  grep -nE "tests\.yml|evaluate-jobs|stale\.yml|validate-submissions|release-please|all-contributors|generate-contributors|workflow_run" "$f" \
    | grep -v "^.*:#" || true
done
```

Expected: no output. (A `workflow_run` trigger in any kept workflow would indicate a cross-workflow chain that just broke.)

- [ ] **Step 4.8: Run pre-commit + tests**

```bash
.venv/bin/python -m pytest -q
# pre-commit on staged-only (full --all-files has pre-existing failures unrelated to cleanup):
git diff --cached --name-only | xargs -r .venv/bin/pre-commit run --files
```

Both must pass.

- [ ] **Step 4.9: Commit**

```bash
git commit -m "ci: collapse to solo-minimal workflow set

Keep ci.yml (now also runs pytest+coverage merged from tests.yml),
codeql.yml, pages-deployment.yml, pre-commit.yml, update-jobs.yml.
Delete 36 community-bot/automation workflows plus shared/ dir and
orphaned release-please config. Verified none of the kept workflows
reference deleted ones via workflow_run/workflow_call/needs."
```

---

## Task 5: Commit 5 — prune local branches

**Files:**
- No file changes — git branch operations only.
- Commit message records deleted branch SHAs for recovery.

- [ ] **Step 5.1: Enumerate deletion candidates**

```bash
echo "=== Merged into main (safe with -d) ==="
git branch --merged main | grep -vE "^\*|main$|chore/repo-cleanup$|fix/derive-counts-from-data$" | sort

echo
echo "=== PR-mirror branches (force-delete with -D) ==="
git branch | grep -E "^\s*(pr-[0-9]+|pr-[0-9]+-(head|merge|review|fix|local|finalize|refresh)|backup-pr[0-9]+.*)$" | sort
```

Save both lists. Pass them to the operator for confirmation.

- [ ] **Step 5.2: Record SHAs for recovery (in commit message footer)**

```bash
{
  echo "Deleted local branches and their tip SHAs:"
  echo
  for b in $(git branch --merged main | grep -vE "^\*|main$|chore/repo-cleanup$|fix/derive-counts-from-data$" | tr -d ' '); do
    printf "  merged: %s %s\n" "$(git rev-parse "$b")" "$b"
  done
  for b in $(git branch | grep -E "^\s*(pr-[0-9]+|pr-[0-9]+-(head|merge|review|fix|local|finalize|refresh)|backup-pr[0-9]+.*)$" | tr -d ' '); do
    printf "  pr-mirror: %s %s\n" "$(git rev-parse "$b")" "$b"
  done
} > /tmp/cleanup-deleted-branches.txt
cat /tmp/cleanup-deleted-branches.txt
```

- [ ] **Step 5.3: Operator confirmation**

Show the operator the deletion lists from Step 5.1 plus any `feat/*` branches that aren't in either list. Ask explicitly: "delete these? Y/n. Any branch to spare?" Wait for response.

This is the safety gate. Do not proceed without explicit "yes."

- [ ] **Step 5.4: Delete merged branches (safe)**

```bash
git branch --merged main \
  | grep -vE "^\*|main$|chore/repo-cleanup$|fix/derive-counts-from-data$" \
  | xargs -r git branch -d
```

`-d` will refuse to delete anything unmerged — safety net.

- [ ] **Step 5.5: Force-delete PR-mirror branches**

```bash
git branch \
  | grep -E "^\s*(pr-[0-9]+|pr-[0-9]+-(head|merge|review|fix|local|finalize|refresh)|backup-pr[0-9]+.*)$" \
  | tr -d ' ' \
  | xargs -r git branch -D
```

These mirror upstream PRs and live on `origin` — local deletion doesn't lose the work.

- [ ] **Step 5.6: Verify branch list shrank as intended**

```bash
git branch
```

Expected: ~3-10 branches remaining. Should include `main`, `chore/repo-cleanup` (current, marked with `*`), `fix/derive-counts-from-data`, and any `feat/*` the operator chose to spare in Step 5.3.

- [ ] **Step 5.7: Empty commit recording the branch deletions**

```bash
git commit --allow-empty -F - <<EOF
chore(branches): prune merged + PR-mirror local branches

Deleted all branches merged into main and all pr-* mirror branches
that exist on origin (resurrectable from GitHub). Kept main, the
cleanup branch, and any feat/* branches still in active local work.

$(cat /tmp/cleanup-deleted-branches.txt)
EOF
```

---

## Task 6: Commit 6 — final verification

**Files:**
- No code changes (verification only).
- Commit only if something requires an adjustment surfaced during verification.

- [ ] **Step 6.1: Re-run full test suite from clean slate**

```bash
rm -rf .pytest_cache __pycache__
.venv/bin/python -m pytest -q
# pre-commit on staged-only (full --all-files has pre-existing failures unrelated to cleanup):
git diff --cached --name-only | xargs -r .venv/bin/pre-commit run --files --cov=scripts --cov-report=term-missing
```

Both must pass. Coverage should match or exceed the Task 0 baseline (no test count regression).

- [ ] **Step 6.2: Stale-reference smoke check**

```bash
grep -rE "test_config\.py|fix\.py|purify_config|verify_companies" \
  .github/ scripts/ tests/ Makefile pyproject.toml requirements.txt 2>/dev/null \
  | grep -v __pycache__ | grep -v docs/superpowers || echo "OK: no stale refs"

grep -rE "evaluate-jobs|validate-submissions|all-contributors|release-please|stale\.yml|tests\.yml" \
  .github/ codecov.yml 2>/dev/null || echo "OK: no stale workflow refs"
```

Both must print `OK: ...`.

- [ ] **Step 6.3: Confirm docs/ is untouched**

```bash
git log --oneline -- docs/ | head -5
```

Expected: the most recent commit affecting `docs/` should be the brainstorming spec/plan write (`docs/superpowers/...`), not anything in the live site directory (`docs/index.html`, `docs/jobs.json`, `docs/app.js`, etc.).

- [ ] **Step 6.4: Confirm kept workflow set**

```bash
ls .github/workflows/ | sort
```

Expected (exactly 5):

```text
ci.yml
codeql.yml
pages-deployment.yml
pre-commit.yml
update-jobs.yml
```

- [ ] **Step 6.5: If any check above failed, fix in-place and commit**

If all checks pass, no extra commit needed — Task 6 is verification only.

If a fix is needed:

```bash
# ...make the fix...
.venv/bin/python -m pytest -q
# pre-commit on staged-only (full --all-files has pre-existing failures unrelated to cleanup):
git diff --cached --name-only | xargs -r .venv/bin/pre-commit run --files
git commit -am "chore: fix issue surfaced during cleanup verification"
```

- [ ] **Step 6.6: Final summary**

Print the final state:

```bash
echo "=== final commit log on cleanup branch ==="
git log --oneline main..chore/repo-cleanup

echo
echo "=== final branch list ==="
git branch

echo
echo "=== final workflow list ==="
ls .github/workflows/

echo
echo "=== final root file count (excluding hidden) ==="
ls -1 | wc -l
```

Report to the operator. Done.

---

## Rollback procedures

**Per-commit rollback:**

```bash
git revert <sha>
```

Each of the six commits is independently revertable.

**Branch resurrection** (if Task 5 deleted something needed):

```bash
# Read the SHA from the Task 5 commit message footer
git log chore/repo-cleanup --grep="prune merged" -1 --format=%B \
  | grep "^\s*\(merged\|pr-mirror\):"

# Recreate any branch by name from its recorded SHA
git branch <name> <sha>
```

**Whole-cleanup abort:**

```bash
git checkout fix/derive-counts-from-data
git branch -D chore/repo-cleanup
# Then restore any untracked screenshots from .Trash if needed (macOS)
```
