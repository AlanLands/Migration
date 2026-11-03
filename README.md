# Cloud Migration AI Repo

GitLab Duo skills, prompts, rules and tools for a multi-application cloud migration. Everything runs in **GitLab Duo Chat in the IDE** from files in this repo. No AI Catalog is needed.

## Catalog

| Asset | Type | Migration phase | Status | What it does |
|---|---|---|---|---|
| [`/functional-doc`](.agents/skills/functional-doc/SKILL.md) | **Skill: one command** | Discover & assess | Draft v0.1 | `/functional-doc docs/confluence` → code scan → prepare docs (incl. OCR) → functional doc → Word + Excel |
| [`/app-functionality-extractor`](.agents/skills/app-functionality-extractor/SKILL.md) | Skill (step 1) | Discover & assess | Draft v0.1 | Scans the app repo → `docs/functional-spec.md` (design notes: [gitlab-duo-app-functionality-agent.md](gitlab-duo-app-functionality-agent.md)) |
| [`/app-functional-doc-builder`](.agents/skills/app-functional-doc-builder/SKILL.md) | Skill (step 2) | Discover & assess | Draft v0.1 | Code spec + Confluence (incl. diagram notes) → Functional Document → `docs/functional-doc.md/.json` + Excel + Word ([docs](agents/app-functional-doc-builder/)) |
| [`/migration-requirements-extractor`](.agents/skills/migration-requirements-extractor/SKILL.md) | Skill (step 3) | Discover & assess → Plan waves | Draft v0.1 | Reviewed functional doc → traceable on-prem → cloud requirements → Excel ([docs](agents/migration-requirements-extractor/)) |
| [confluence-app-extractor](agents/confluence-app-extractor/) | Agent prompt (copy-paste) | Discover & assess | Draft v0.1 | Fills the application template page from existing Confluence pages, with citations |
| [doc-prep](tools/doc-prep/) | Tool | Discover & assess | Tested on samples | Confluence exports (Word/PDF/HTML/Excel/images/draw.io) → text; OCR on images; redacts secrets |
| [install-to-app-repo.ps1](tools/install-to-app-repo.ps1) | Tool | All | Tested | Copies the skills + tools into a cloned app repo |
| [office-export](tools/office-export/) | Tool / CI job | All | Tested on samples | Validates the skills' JSON and exports Excel + Word |
| [how-to-build-app-functional-doc](confluence/how-to-build-app-functional-doc.md) | Confluence playbook | Discover & assess | Draft | Step-by-step guide for the three skills |

## How to use it (per app)

Full end-to-end workflow with diagram: **[WORKFLOW.md](WORKFLOW.md)**.

**Requirements (verify on your GitLab version):** GitLab 18.10+, Premium/Ultimate with Duo Agent Platform, GitLab for VS Code **6.71.4+**, Python 3.10+, Windows 10/11 (for the built-in OCR). Docs: https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills/

| # | Step | How |
|---|---|---|
| 1 | Clone the app repo | `git clone <app-repo-url> C:\work\<app>` |
| 2 | Add the AI toolkit to it | From this repo: `.\tools\install-to-app-repo.ps1 -AppRepo C:\work\<app> -InstallPython` (copies `.agents/skills`, `tools/doc-prep`, `tools/office-export`) |
| 3 | Add the Confluence documents | Export each page (**⋯ → Export → Word**, or HTML with attachments) into `docs/confluence/`. Add draw.io diagrams as `.drawio`, plus images. Optional: `<image>.image.md` describing key diagrams. |
| 4 | Run one command | VS Code → GitLab Duo Chat → **new conversation** → `/functional-doc docs/confluence` |
| 5 | Review | SME reviews `docs/out/<app>-functional-doc.docx/.xlsx`; give the answers back in the chat to update |
| 6 | Requirements | New conversation → `/migration-requirements-extractor Cloud: <..>. Pattern: <..>.` → `docs/out/<app>-migration-requirements.xlsx` |
| 7 | Commit | Commit `docs/` on a branch and open an MR |

What `/functional-doc` does: **Stage 1** scans the code → `docs/functional-spec.md` (reused next time, add `RESCAN` to redo) · **Stage 2** runs `tools/doc-prep/prepare_sources.py` → text + OCR of images → `docs/confluence/_extracted/` · **Stage 3** builds the functional doc from both → `docs/functional-doc.md/.json` · **Stage 4** exports Word + Excel to `docs/out/`.

The individual skills (`/app-functionality-extractor`, `/app-functional-doc-builder`) still work on their own when you need to re-run one stage. After you edit a `SKILL.md`, re-run the install script and start a new Duo conversation.

**Confluence via MCP** (optional, instead of exports): see [`ide/`](ide/README.md). Exports are recommended because they include images and work offline.

## Layout

```
.
├── .agents/skills/<skill>/SKILL.md   # what Duo runs (source of truth for instructions)
├── agents/<name>/                    # design notes, evals, extra prompts for each skill/agent
├── tools/doc-prep/                   # Confluence exports → text + OCR of images
├── tools/office-export/              # JSON → Excel/Word + validation (+ CI job snippet)
├── tools/install-to-app-repo.ps1     # copies skills + tools into an app repo
├── confluence/                       # Confluence page drafts (playbooks, guides)
├── ide/                              # IDE config (mcp.json for Confluence Cloud)
└── gitlab-duo-app-functionality-agent.md
```

## Adding a new skill

1. Create `.agents/skills/<kebab-case-name>/SKILL.md` with frontmatter `name` (same as the folder), `description` (what it does and when to use it, because Duo picks skills by this) and `metadata: slash-command: enabled`.
2. Put design notes and evals in `agents/<name>/`.
3. Add a row to the **Catalog**.
4. Run the evals on 2–3 real apps before telling the team.
