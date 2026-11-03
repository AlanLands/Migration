# App Functional Doc Builder

A GitLab Duo AI Catalog agent that builds the **Functional Document** for one application by combining its code spec (from the App Functionality Extractor) with its Confluence pages, including diagrams and images. Every item is cited and has a confidence level; code-vs-document conflicts are logged, not hidden.

**Sections:** Overview · Business Functions · Business Rules · Data Model · Integrations · Process Flows (steps + Mermaid) · Runbook · Risks & Actions · Open Questions · Conflicts · Source Register

**Outputs:** Markdown (for Confluence) + JSON → `tools/office-export/export.py` → **Excel + Word**

## Files

| File | What it is |
|---|---|
| [`agent.md`](agent.md) | AI Catalog fields, system prompt, evals, limits |
| [`prompt.md`](prompt.md) | Duo Chat prompts: with/without Confluence, image notes, large apps, follow-ups |
| [`../../tools/office-export/`](../../tools/office-export/) | JSON → .xlsx / .docx converter and validator |
| [`../migration-requirements-extractor/`](../migration-requirements-extractor/) | Next step: migration requirements in Excel |

## End-to-end (per app)

| # | Step | Tool | Output |
|---|---|---|---|
| 1 | Scan the cloned repo | App Functionality Extractor agent | `docs/functional-spec.md` |
| 2 | Merge code + Confluence + images | **this agent** | Part 1 Markdown + Part 2 JSON |
| 3 | Save the JSON, export | `export.py` | `functional-doc.xlsx/.docx` |
| 4 | SME review; answer OQs and CFs | Follow-up prompts | reviewed `functional-doc.json` |
| 5 | Extract migration requirements | `migration-requirements-extractor` | `requirements.json` → `.xlsx` |
