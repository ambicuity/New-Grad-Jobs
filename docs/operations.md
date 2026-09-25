# Operations Runbook

How the live board at <https://jobs.riteshrana.engineer> is produced, and what to do when
something goes wrong. For the code-level design see [architecture.md](architecture.md).

## How a refresh works

Everything runs in [`update-jobs.yml`](../.github/workflows/update-jobs.yml). It is the only
workflow that deploys the site.

| Trigger | When |
|---|---|
| `schedule` | `7,37 * * * *`: every 30 minutes, offset from :00/:30 because GitHub delays or drops scheduled runs at the top of the hour |
| `workflow_dispatch` | By hand (Actions tab, or `gh workflow run update-jobs.yml --ref main`) |
| `push` to `main` | When `scripts/**`, `config.yml`, `requirements.txt`, `site/**` or the workflow itself changes |

Runs queue rather than cancel (`concurrency: update-jobs`), so a scrape that is already
running always gets to finish and deploy.

1. **`scrape` job** (25 min timeout, read-only token):
   1. `pip install --require-hashes -r requirements.txt`
   2. `python scripts/update_jobs.py` fetches every enabled source, dedupes, filters and
      enriches the jobs, then writes `site/public/{jobs.json, jobs-index.json, descriptions/,
      jobs-extended.json, feed.xml, feeds/, health.json}`. It also updates `README.md` (COUNT markers and the
      CATEGORY-LISTINGS / COMPANY-LISTINGS blocks only) and `data/market-history.json`.
   3. `python scripts/check_integrity.py` validates every artifact against the others. It
      checks the jobs.json contract, index/shard/feed/health consistency and URL safety.
   4. `npm ci && npm run build` in `site/` bakes the data into `site/dist`. The build also
      writes the per-job pages (`/job/<job_id>/`), `sitemap.xml`, `robots.txt` and the CSP.
   5. The job uploads `site/dist` as the Pages artifact and `README.md` +
      `data/market-history.json` as the `persistent-state` artifact.
2. **`deploy` job** (`main` only): `actions/deploy-pages` publishes the artifact to the
   `github-pages` environment.
3. **`persist` job** (`main` only): commits `README.md` and `data/market-history.json` back
   to `main` as `🤖 Update job listings [skip ci]`. It rebases onto the latest `main`. If the
   rebase conflicts, it aborts and fails. It never pushes conflict markers or invalid JSON,
   and it retries the push up to 3 times.

`deploy` and `persist` are independent: a failed persist does not stop the site update.
The generated data is **not committed**. It only exists in the Pages deployment.

## Running it manually

```bash
# Re-run the full scrape → deploy on main
gh workflow run update-jobs.yml --ref main
gh run watch "$(gh run list --workflow update-jobs.yml --limit 1 --json databaseId --jq '.[0].databaseId')"

# Local scrape. This hits the real APIs and takes a few minutes. It writes to
# $NGJ_OUTPUT_DIR (default site/public) and ALSO rewrites README.md and
# data/market-history.json. Discard those two files afterwards.
NGJ_OUTPUT_DIR=/tmp/ngj make run
.venv/bin/python scripts/check_integrity.py /tmp/ngj
git checkout -- README.md data/market-history.json
```

If you dispatch `update-jobs.yml` on a branch other than `main`, it scrapes and builds but
skips `deploy` and `persist`. Use that to try a scraper change without publishing it.

## Monitoring

- **`health.json`** (<https://jobs.riteshrana.engineer/health.json>): `status` is `ok`,
  `degraded` or `failed`. A run is `failed` when it has 0 jobs. It is `degraded` when a
  source returned 0 jobs, a source hit the 403 cooldown or had more than 25% of its
  companies fail, or the URL safety gate blocked a job. Per-source detail (`sources.<name>`)
  lists errors by kind and up to 20 failed companies. Per-company errors are captured and
  reported here instead of failing the run.
- **Scraper watchdog** ([`scraper-watchdog.yml`](../.github/workflows/scraper-watchdog.yml),
  `23 */2 * * *`): reads the live `health.json`. If `last_run` is older than 180 minutes it
  re-dispatches `update-jobs.yml` (unless a run is already queued or running) and opens an
  issue labelled `scraper-stale`. It closes that issue once the data is fresh again.
- **Site chip**: the top bar shows LIVE / STALE (data older than 24 h) / OFFLINE.

## When something is wrong

### Data is stale (watchdog issue open, STALE chip)

1. Open **Actions → Update New Grad Jobs**. Check whether scheduled runs are still
   appearing.
2. **No runs at all:** GitHub has stopped firing the schedule. This happened once, in
   Aug 2026, when the site went stale for five weeks. Dispatch a run by hand, then push a
   no-op edit to `update-jobs.yml` to re-register the schedule. Also check that Actions is
   not disabled for the repo, for example after 60 days without activity on a fork.
3. **Runs failing:** read the failing step. See the sections below.

### Scrape fails with "Partial-collapse guard"

The scraper refuses to publish, and writes nothing, when either:
- the published total falls more than **40%** below the previous run, or
- a source that returned more than **100** jobs last time returns **0**.

The previous run is read from the output dir, else from the live `health.json` and
`jobs-index.json`. While the guard trips, the site keeps serving the last good data.

- **An upstream outage or block** (usually one source at 0): wait. The next runs publish
  on their own once the source recovers. Check `health.json` `sources` and the run log for
  403s or timeouts.
- **A legitimate drop** (you removed many companies, or tightened filters): the override
  is `NGJ_ALLOW_DROP=1`. The workflow has no input for it, so add
  `env: { NGJ_ALLOW_DROP: '1' }` to the *Run job scraper* step in a PR, let one run deploy,
  then revert.

### Scrape fails with "integrity" errors

`check_integrity.py` found artifacts that disagree with each other, such as a missing
shard, a count mismatch or an unsafe URL. Nothing was deployed. This is a code bug:
reproduce it locally with `make run` + `check_integrity.py`.

### `persist` fails

Usually the rebase onto `main` conflicted, or a branch rule rejected the bot push. The
site was still deployed. The next run regenerates `README.md` from the new `main`, so a
single failure needs no action. If it fails every run with "permission denied" or a rule
violation, check that the `PERSIST_DEPLOY_KEY` secret matches a write deploy key and that
the deploy key is still a bypass actor on the `main` ruleset (see Repository settings).

### A source returns far fewer jobs

- Look at `health.json` → `sources.<name>.errors.by_kind` and `failed_companies`.
- `forbidden` / `cooldown`: the domain returned repeated 403s, and the per-run circuit
  breaker (`scripts/source_cooldown.py`) skipped the rest. This is usually temporary.
- `http` 404 on an ATS board: the company moved ATS or renamed its board. Fix or remove the
  entry in `config.yml` and record it in [removed-companies.md](removed-companies.md).
- **Workday:** a cohort of enterprise tenants rejects the CXS jobs API with `HTTP 422` /
  `400` and an empty message. They do so even with the `CALYPSO_CSRF_TOKEN` retry and a
  primed `PLAY_SESSION` cookie. Behaviour varies by cluster (`wd1`/`wd5`/`wd10`), and
  there is no fix short of a real browser session. Treat these as known failures, visible
  per company in `health.json`.

### A bad deploy (broken site or bad data)

- **Fastest:** in Actions, open the last good *Update New Grad Jobs* run and re-run only
  its `deploy` job. This works while that run's `github-pages` artifact still exists
  (`upload-pages-artifact` keeps it for 1 day by default).
- **Otherwise:** revert the offending commit on `main` (`git revert <sha>` and merge). The
  push re-triggers `update-jobs.yml`, which rebuilds and redeploys from the reverted code.
- Never force-push `main` or rewrite history to "undo" a deploy. The deployment is not
  tied to git history.

## Repository settings this relies on

- **Pages:** Settings → Pages → Source = **GitHub Actions**. Custom domain
  `jobs.riteshrana.engineer`, taken from `site/public/CNAME` and served from the build.
- **Environment `github-pages`:** deployments allowed from `main`.
- **Required status checks on `main`:** `lint`, `typecheck`, `test (3.11)`, `test (3.13)`,
  `site` (from `ci.yml`, so do not rename those jobs), plus `Run Pre-commit Hooks` from
  `pre-commit.yml`.
- **Branch rules on `main`** (ruleset "Protect Main Branch"): required status checks above,
  no force pushes, no deletion; PRs are squash-merged. Bypass actors: the admin/maintain/write
  repository roles and the **deploy key** used by the `persist` job. The `github-actions` app
  cannot be a bypass actor on a personal repository, which is why `persist` pushes over SSH
  with a deploy key instead of `GITHUB_TOKEN`.
- **Security:** private vulnerability reporting, secret scanning with push protection,
  Dependabot alerts. Dependabot opens grouped weekly PRs for Actions and pip
  (`.github/dependabot.yml`). Pre-commit hook revisions are updated by hand with
  `pre-commit autoupdate --freeze`.
- **Secrets:** scraping and deploying need none (all sources are public endpoints;
  `GITHUB_TOKEN` covers the Pages deploy). `PERSIST_DEPLOY_KEY` is the private half of the
  write deploy key "update-jobs persist" that the `persist` job pushes README.md and
  `data/market-history.json` with. To rotate it: `ssh-keygen -t ed25519 -N '' -f key`,
  `gh repo deploy-key add key.pub --allow-write --title "update-jobs persist"`,
  `gh secret set PERSIST_DEPLOY_KEY < key`, delete the old deploy key and both local files.
  `CODECOV_TOKEN` is optional; coverage upload is skipped without it.
- **Labels:** `bash .github/create-labels.sh` recreates the labels in
  [`.github/labels.md`](../.github/labels.md). The watchdog creates `scraper-stale` itself.
