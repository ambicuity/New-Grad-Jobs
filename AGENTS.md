# Agent Startup Policy (Project)

All agents working in this repository must use KINDX first.

## Required startup steps
1. Run `kindx --index ngj status`.
2. Run `kindx --index ngj collection list`.
3. Use KINDX for discovery/search before other repo-wide search tools when possible:
   - `kindx --index ngj query "..."`
   - `kindx --index ngj search "..."`
   - `kindx --index ngj get kindx://<collection>/<path>`

## RBAC-aware usage
- Prefer `--index ngj` for all KINDX commands in this repo.
- Respect tenant/collection restrictions in multi-tenant mode.

## Fallback
If KINDX is unavailable or errors block progress, continue with local tools and report the KINDX failure explicitly.
