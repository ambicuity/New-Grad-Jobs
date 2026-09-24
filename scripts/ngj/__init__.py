"""New Grad Jobs aggregator package.

The scraper pipeline, split by responsibility:

- ``settings``      frozen run Settings built once from config.yml + env
- ``models``        SourceResult / SourceError returned by every source adapter
- ``http``          pooled session, per-domain limiter, shared fetch/retry wrapper
- ``sources/*``     one adapter per job source (Greenhouse, Lever, Ashby, ...)
- ``text``, ``dates``, ``compensation``   pure parsing helpers
- ``filters``       new-grad / recency / location / exclusion filtering
- ``taxonomy``      categories and company tiers
- ``dedup``, ``enrich``   post-fetch transforms (never mutate their inputs)
- ``outputs/*``     jobs.json, RSS, health and market-history writers
- ``pipeline``      orchestration and the CLI ``main``

``scripts/`` must be on ``sys.path`` (the CLI entrypoint and tests/conftest.py
arrange that); sibling helper modules such as ``url_safety`` are imported as
top-level modules.
"""
