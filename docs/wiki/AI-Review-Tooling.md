# 🤖 AI Review Tooling Strategy

> **Last Updated**: March 2026
> **Decision Owner**: @ambicuity (Solo Maintainer)

This document defines which AI tools are used for code review in this repository, why they were chosen, and when to use each one.

---

## Active AI Reviewers

| Tool | Role | Trigger |
|------|------|---------|
| **GitHub Copilot** | PR reviewer, coding agent | Auto-reviews every PR via `.github/copilot-review-settings.yml` |
| **Gemini Code Assist** | Deep code reviewer | Auto-reviews every PR via `.coderabbit.yaml` instructions |
| **CodeRabbit** | Expert reviewer persona | Configured as Senior Principal Engineer in `.coderabbit.yaml` |

---

## When to Use What

### GitHub Copilot — The Speed King
**Best for**: Daily PR triage, quick fixes, background CI.

- Auto-reviews every PR and flags security issues inline.
- The Copilot Coding Agent can be assigned GitHub issues directly — it will branch, write code, and open a PR autonomously.
- Swap underlying models on the fly (faster model for tests, heavier model for logic).
- **Context window**: ~128K tokens.

**Solo maintainer value**: You scan Copilot's review first. If it says "LGTM," you skim the diff and merge. If it flags something, you dig in. Saves 5–10 minutes per PR.

### Gemini Code Assist — The Context Heavyweight
**Best for**: Large refactors, architecture reviews, multi-file changes.

- 1M+ token context window. Can ingest the entire repository at once.
- Agent Mode plans and executes multi-file changes autonomously.
- Scores higher on reasoning benchmarks (SWE-bench) for complex logic.
- Provides detailed analysis with edge cases and alternative approaches.

**Solo maintainer value**: When a contributor opens a 500-line PR touching the scraper core, Gemini will catch the subtle issues Copilot misses — thread safety, pagination edge cases, API contract violations.

### How They Complement Each Other

```
Contributor opens PR
        │
        ├──► Copilot auto-review (instant, security-focused)
        │
        ├──► Gemini auto-review (deep, architecture-focused)
        │
        ├──► CodeRabbit review (engineering standards)
        │
        └──► You review (final sign-off, merge decision)
```

**The layering strategy**: Three AI reviewers catch different classes of bugs. You only spend time on the issues that survive all three filters.

---

## Decision Rationale

| Consideration | Copilot | Gemini |
|---------------|---------|--------|
| Context window | ~128K tokens | 1M+ tokens |
| Autonomous agent | Copilot Coding Agent | Gemini Agent Mode |
| Ecosystem fit | Native GitHub integration | Deep Google Cloud integration |
| Vulnerability catch rate | Background CI scanning | Analytical codebase scanning |
| Speed vs. depth | Speed — instant suggestions | Depth — detailed reasoning |
| Cost | Included with GitHub plan | Free for public repos |

**Bottom line**: Use both. Copilot for speed, Gemini for depth. They don't overlap — they stack.

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.coderabbit.yaml` | CodeRabbit review persona and rules |
| `.github/copilot-review-settings.yml` | Copilot auto-review triggers (if configured) |
| `.gemini/settings.json` | Gemini agent features and context rules |
