#!/usr/bin/env bash
# create-labels.sh
# Creates all GitHub Labels for the New Grad Jobs repository.
# Usage: bash .github/create-labels.sh
# Requires: gh CLI authenticated (gh auth login)

set -euo pipefail

REPO="ambicuity/New-Grad-Jobs"
echo "🏷️  Creating labels for ${REPO}..."
echo ""

create_label() {
  local name="$1"
  local color="$2"
  local description="$3"

  if gh label create "${name}" \
      --repo "${REPO}" \
      --color "${color}" \
      --description "${description}" \
      --force 2>/dev/null; then
    echo "  ✅  ${name}"
  else
    echo "  ⚠️   ${name} — skipped (check gh auth or repo permissions)"
  fi
}

# ============================================================
# TYPE LABELS
# ============================================================
echo "── Type Labels ──────────────────────────────────────"
create_label "bug"           "d73a4a"  "Something isn't working"
create_label "enhancement"   "a2eeef"  "New feature or request"
create_label "documentation" "0075ca"  "Improvements or additions to documentation"
create_label "architecture"  "e4e669"  "Major structural change proposal"
create_label "chore"         "fef2c0"  "Maintenance or housekeeping task"
create_label "security"      "ee0701"  "Security vulnerability or concern"

# ============================================================
# STATUS LABELS
# ============================================================
echo ""
echo "── Status Labels ────────────────────────────────────"
create_label "needs-triage"    "ededed"  "Awaiting maintainer review and categorization"
create_label "status: in-progress"   "fbca04"  "Actively being worked on"
create_label "awaiting-response"  "d4c5f9"  "Waiting for the contributor to respond or update"
create_label "stale"           "cccccc"  "No activity in 30+ days"
create_label "blocked"         "b60205"  "Cannot proceed until a blocker is resolved"
create_label "help wanted"     "008672"  "Extra attention needed from the community"
create_label "good first issue" "7057ff" "Good for newcomers — welcoming entry point"
create_label "good first issue candidate" "e4e669" "Potential GFI — needs maintainer review before assignment"
create_label "plan-me"         "0075ca"  "Triggers CodeRabbit to generate an implementation plan"
create_label "duplicate"       "cfd3d7"  "This issue or PR already exists"
create_label "wontfix"         "ffffff"  "This will not be worked on"
create_label "merge-conflict"  "e11d48"  "This PR has merge conflicts that must be resolved"
create_label "automated pr"    "0e8a16"  "PR created by an automation (Dependabot, Actions bot)"

# ============================================================
# JOB DATA LABELS
# ============================================================
echo ""
echo "── Job Data Labels ──────────────────────────────────"
create_label "new-role"           "0e8a16"  "Submission of a new job posting"
create_label "edit-role"          "5319e7"  "Request to close or update an existing listing"
create_label "link-expired"       "b60205"  "The application link is dead or returns 404"
create_label "needs-verification" "cccccc"  "Job posting needs to be manually verified before publish"

# ============================================================
# PRIORITY LABELS
# ============================================================
echo ""
echo "── Priority Labels ──────────────────────────────────"
create_label "priority: critical" "b60205"  "Must fix immediately (data loss, CI broken, site down)"
create_label "priority: high"     "e11d48"  "Important — should be addressed this week"
create_label "priority: medium"   "f59e0b"  "Nice to have — scheduled for next cycle"
create_label "priority: low"      "94a3b8"  "Minor — backlog"

# ============================================================
# WORK AUTHORIZATION / VISA LABELS
# ============================================================
echo ""
echo "── Visa / Work Authorization Labels ─────────────────"
create_label "visa: sponsorship-available" "1d76db"  "Company explicitly sponsors H-1B / work visas"
create_label "visa: opt-cpt-friendly"      "5319e7"  "Accepts international students on OPT/CPT"
create_label "visa: us-citizens-only"      "e4e669"  "Requires US Citizenship (Defense / Gov clearance)"

# ============================================================
# WORK MODEL & LOCATION LABELS
# ============================================================
echo ""
echo "── Location Labels ──────────────────────────────────"
create_label "location: remote"  "0e8a16"  "100% Remote role"
create_label "location: hybrid"  "fbca04"  "Hybrid — some in-office expected"
create_label "location: onsite"  "d73a4a"  "Requires full on-site presence"

# ============================================================
# ROLE CATEGORY LABELS
# ============================================================
echo ""
echo "── Role Category Labels ─────────────────────────────"
create_label "role: swe"                "0075ca"  "Software Engineering"
create_label "role: systems-engineering" "1d76db" "Hardware, Network, or Systems Engineering"
create_label "role: ai-ml"             "7057ff"  "Data Science, AI, or Machine Learning"
create_label "role: product"           "a2eeef"  "Product Management (PM)"

# ============================================================
# DIFFICULTY TIER LABELS (issue complexity tiers)
# ============================================================
echo ""
echo "── Difficulty Tier Labels ───────────────────────────"
create_label "beginner"      "c2e0c6"  "Requires some prior contribution experience; beyond GFI"
create_label "intermediate"  "ffd33d"  "Requires codebase familiarity; 2-3 functions involved"
create_label "advanced"      "e6192a"  "Requires deep scraper knowledge; high-impact change"
create_label "ci-cd"         "bfdadc"  "Changes to GitHub Actions workflows or CI configuration"

echo ""
echo "✅  Done! All labels have been processed for ${REPO}."
echo "    View them at: https://github.com/${REPO}/labels"
