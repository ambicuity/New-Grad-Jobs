# GitHub Labels — New Grad Jobs

All labels used in this repository, grouped by category.
To recreate them after a fork or fresh repo setup, run the shell script below.

---

## Label Definitions

### 🔴 Type Labels
| Label | Color | Description |
|-------|-------|-------------|
| `bug` | `#d73a4a` | Something isn't working |
| `enhancement` | `#a2eeef` | New feature or request |
| `documentation` | `#0075ca` | Improvements or additions to documentation |
| `architecture` | `#e4e669` | Major structural change proposal |
| `chore` | `#fef2c0` | Maintenance or housekeeping task |
| `security` | `#ee0701` | Security vulnerability or concern |

### 🟡 Status Labels
| Label | Color | Description |
|-------|-------|-------------|
| `needs-triage` | `#ededed` | Awaiting maintainer review and categorization |
| `in-progress` | `#fbca04` | Actively being worked on |
| `stale` | `#cccccc` | No activity in 30+ days |
| `blocked` | `#b60205` | Cannot proceed until a blocker is resolved |
| `help wanted` | `#008672` | Extra attention needed from the community |
| `good first issue` | `#7057ff` | Good for newcomers — welcoming entry point |
| `duplicate` | `#cfd3d7` | This issue or PR already exists in the tracker |
| `wontfix` | `#ffffff` | This will not be worked on |

### 🟢 Job Data Labels
| Label | Color | Description |
|-------|-------|-------------|
| `new-role` | `#0e8a16` | Submission of a new job posting |
| `edit-role` | `#5319e7` | Request to close or update an existing listing |
| `link-expired` | `#b60205` | The application link is dead or returns 404 |
| `needs-verification` | `#cccccc` | Job posting needs to be manually verified before publish |

### 🚨 Priority Labels
| Label | Color | Description |
|-------|-------|-------------|
| `priority: critical` | `#b60205` | Must fix immediately (data loss, CI broken, site down) |
| `priority: high` | `#e11d48` | Important — should be addressed this week |
| `priority: medium` | `#f59e0b` | Nice to have — scheduled for next cycle |
| `priority: low` | `#94a3b8` | Minor — backlog |

### 🛂 Work Authorization / Visa Labels
| Label | Color | Description |
|-------|-------|-------------|
| `visa: sponsorship-available` | `#1d76db` | Company explicitly sponsors H-1B / work visas |
| `visa: opt-cpt-friendly` | `#5319e7` | Accepts international students on OPT/CPT |
| `visa: us-citizens-only` | `#e4e669` | Requires US Citizenship (Defense / Gov clearance) |

### 🗺️ Work Model & Location Labels
| Label | Color | Description |
|-------|-------|-------------|
| `location: remote` | `#0e8a16` | 100% Remote role |
| `location: hybrid` | `#fbca04` | Hybrid — some in-office expected |
| `location: onsite` | `#d73a4a` | Requires full on-site presence |

### 💼 Role Category Labels
| Label | Color | Description |
|-------|-------|-------------|
| `role: swe` | `#0075ca` | Software Engineering |
| `role: systems-engineering` | `#1d76db` | Hardware, Network, or Systems Engineering |
| `role: ai-ml` | `#7057ff` | Data Science, AI, or Machine Learning |
| `role: product` | `#a2eeef` | Product Management (PM) |

---

## Setup Script

Run this once from the repo root to create all labels (requires `gh` CLI authenticated):

```bash
bash .github/create-labels.sh
```
