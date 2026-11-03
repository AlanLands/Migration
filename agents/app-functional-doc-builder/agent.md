# Agent: App Functional Doc Builder

| | |
|---|---|
| **Purpose** | Merge what the **code** says (App Functionality Extractor output) with what the **Confluence documents** say (text and images) into one Functional Document per application, delivered as Markdown and as JSON that converts to Excel and Word. |
| **Used in** | GitLab Duo Chat in the IDE, as a project-level **Agent Skill**: `/app-functional-doc-builder` |
| **Migration phase** | Discover & assess |
| **Upstream** | `App Functionality Extractor` (code → `docs/functional-spec.md`) and Confluence pages about the app |
| **Downstream** | `migration-requirements-extractor` (reads this agent's JSON) and `tools/office-export` (JSON → .xlsx / .docx) |
| **Owner** | `<lead name>` |
| **Version** | 0.1 (draft) |

---

## 1. Where it fits

```
App repo (local clone)  ──► App Functionality Extractor ──► docs/functional-spec.md ─┐
                                                                                      ├─► App Functional Doc Builder ──► functional-doc.md   (review / Confluence)
Confluence pages (+ images) ──────────────────────────────────────────────────────────┘                                └► functional-doc.json ──► export.py ──► .xlsx + .docx
                                                                                                                                                       │
                                                                                         migration-requirements-extractor ◄──────────────────────────────┘
                                                                                                    └► requirements.json ──► export.py ──► requirements .xlsx
```

**Why a separate agent and not a bigger App Functionality Extractor:** code and docs disagree more often than people expect, because documentation goes stale. Keeping the code scan separate means the code spec stays evidence-only, and this agent's main job is to reconcile the two sources and show where they conflict.

**Why JSON and not Excel directly:** Duo agents return text. They can't create `.xlsx` or `.docx` files. The agent outputs one JSON block that follows a fixed schema (inside the system prompt in section 3), and the `tools/office-export/export.py` script turns it into Excel and Word, either on a developer's PC or as a CI job.

---

## 2. Where the instructions live

The instructions are in [`.agents/skills/app-functional-doc-builder/SKILL.md`](../../.agents/skills/app-functional-doc-builder/SKILL.md). That file is the **single source of truth**, so edit it there. No AI Catalog registration is needed: Duo Chat in VS Code (GitLab for VS Code 6.71.4+, GitLab 18.10+) loads project skills from `.agents/skills/` and offers them as slash commands. See the repo README → *How to use the skills*. Docs: https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills/

---

## 3. Evals (run before sharing)

Use 3 apps that an SME already knows well. Keep the inputs and the SME-approved output in `evals/`.

| # | Test | Pass if |
|---|---|---|
| 1 | Normal app: code spec + 2–3 Confluence pages | ≥ 85% of SME-listed business functions found; 0 invented items |
| 2 | Code and doc disagree (e.g. doc says nightly batch, code cron says hourly) | A CF item is logged with both values; neither is chosen silently |
| 3 | Page with a diagram the agent can't see | Source marked `readable: N` and an OQ asks for a description |
| 4 | Page with an image note typed in by a person | Steps from the note appear in a PF, cited to the image source |
| 5 | Source contains a connection string with a password | Value redacted and a risk raised |
| 6 | JSON validity | `python tools/office-export/export.py <file>` runs with 0 schema errors |
| 7 | Traceability | Every BR has a valid `function_id`; every ID referenced exists |

**Key metric:** invented facts = 0. A gap with an open question is a pass; a confident wrong value is a fail.

---

## 4. Known limits

- **Images:** whether the agent can see Confluence images depends on the model Duo picks and on what the Atlassian MCP returns. In most setups the agent gets the page text and image file names, not the pixels. **Verify on your GitLab version.** Until then, use image notes (see `prompt.md` → Mode B).
- **Output length:** large apps need the split-run approach in `prompt.md`.
- **v2:** once the skills are stable, a CI job (see `tools/office-export/README.md`) checks `docs/functional-doc.json` on every MR.
