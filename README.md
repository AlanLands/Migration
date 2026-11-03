# Cloud Migration AI Repo

GitLab Duo agents, flows, prompts and rules for a multi-application cloud migration. One folder per asset; every asset is built to run in **GitLab Duo** (AI Catalog / Duo Chat).

## Catalog

| Asset | Type | Migration phase | Status | What it does |
|---|---|---|---|---|
| [App Functionality Extractor](gitlab-duo-app-functionality-agent.md) | Agent | Discover & assess | Draft | Scans an app repo and produces the code-based functional spec (input to app-functional-doc-builder) |
| [confluence-app-extractor](agents/confluence-app-extractor/) | Agent | Discover & assess | Draft v0.1 | Fills the application template page from existing Confluence pages, with citations |
| [app-functional-doc-builder](agents/app-functional-doc-builder/) | Agent | Discover & assess | Draft v0.1 | Code spec + Confluence (incl. images) → Functional Document (functions, rules, data, integrations, flows, runbook, risks, questions) as Markdown + JSON |
| [migration-requirements-extractor](agents/migration-requirements-extractor/) | Agent | Discover & assess → Plan waves | Draft v0.1 | Reviewed functional doc → traceable on-prem → cloud requirements register |
| [office-export](tools/office-export/) | Tool / CI job | All | Tested on samples | Validates agent JSON and exports Excel + Word |
| [how-to-build-app-functional-doc](confluence/how-to-build-app-functional-doc.md) | Confluence playbook | Discover & assess | Draft | Step-by-step guide for the three-agent chain |

## Layout

```
.
├── agents/<agent-name>/     # agent.md (AI Catalog fields + system prompt + evals), prompt.md, README.md
├── flows/<flow-name>/       # multi-step flows (YAML) + README
├── prompts/<category>/      # copy-paste Duo Chat prompts
├── rules/                   # AGENTS.md / Duo rule templates to copy into app repos
├── confluence/              # Confluence page drafts (playbooks, guides)
└── ide/                     # shared IDE config (mcp.json for Confluence Cloud)
```

## Adding a new asset

1. Create `agents/<kebab-case-name>/` (or `flows/...`, `prompts/...`).
2. Include `README.md`, `agent.md` (purpose, AI Catalog fields, system prompt, guardrails, evals) and `prompt.md`.
3. Add a row to the **Catalog** table above.
4. Run the evals before sharing with the team.
