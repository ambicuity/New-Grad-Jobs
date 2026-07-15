# ADR-0002: GitHub Pages for Frontend Deployment

**Date:** 2026-01-17
**Status:** Accepted
**Deciders:** Ritesh Rana (maintainer)

---

## Context

The job dataset (`jobs.json`) is updated every 5 minutes. Users need a browsable, searchable interface to explore the listings without requiring a backend server, database, or authentication.

Options considered:

1. **GitHub Pages with Vanilla JS** — Static files in `/docs`, served directly from the repository
2. **Vercel / Netlify deployment** — External hosting with build step (e.g., Next.js or React)
3. **GitHub Gist + Observable** — Notebook-style data exploration

---

## Decision

**Option 1 — GitHub Pages** was chosen, originally implemented as a Vanilla JS frontend.

The frontend is served as static files from the `/docs` folder of the main branch with **no build step**, and `jobs.json` is mirrored into `/docs` by the update workflow.

> **Update (NGJ terminal redesign):** the frontend framework later changed — the original vanilla HTML/CSS/JS (`docs/app.js`, `docs/styles.css`) was replaced by a React UI under `docs/terminal/*.jsx`, transpiled in-browser via Babel Standalone. The **hosting decision recorded here is unchanged** (static files from `/docs`, no build step); only the client-side implementation evolved. The Rationale table below reflects the original Vanilla JS reasoning as of the decision date.

---

## Rationale

| Criterion | GitHub Pages + Vanilla JS | Vercel/Next.js | Gist/Observable |
|-----------|--------------------------|----------------|-----------------|
| Deploy complexity | Zero — automatic on push | Requires Vercel account + config | Requires Observable account |
| External dependencies | None | Vercel platform dependency | Observable platform dependency |
| Load time | Very fast (no hydration) | Fast (SSG) / Slow (SSR) | Moderate |
| Contributor accessibility | Any HTML/CSS/JS knowledge | Requires React/Node understanding | Limited customization |
| Cost | Free forever | Free tier (limits apply) | Free |
| Data freshness | `jobs.json` updated by same workflow | Requires separate deployment trigger | Manual |

The zero-deployment-overhead model is critical for a 5-minute update cycle. GitHub Actions can commit `jobs.json` to `/docs` and GitHub Pages serves it instantly — no additional deployment pipelines required.

---

## Consequences

- **Positive**: No external platform dependencies. The website continues to work as long as GitHub exists.
- **Positive**: The same workflow that updates data also deploys the frontend — atomic updates.
- **Positive**: Any developer who knows HTML/CSS/JS can contribute to the frontend.
- **Negative**: No server-side rendering — all filtering/search is client-side JavaScript. Performance degrades if `jobs.json` exceeds ~10MB (currently ~1.2MB).
- **Negative**: No dynamic routes — the site is strictly single-page.

---

## Review Trigger

This decision should be revisited when:
- `jobs.json` exceeds 5MB (client-side load time becomes perceptible on mobile)
- We need server-side features (authentication, personalized job alerts, API endpoints)
- We need SEO-optimized individual job pages (not possible with pure SPA on GitHub Pages)
