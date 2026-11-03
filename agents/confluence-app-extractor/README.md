# Confluence App Extractor

A GitLab Duo AI Catalog agent that reads several Confluence pages about one application and fills a standard application template page. Every value is cited to its source page; missing or conflicting facts are flagged, never guessed.

Built for cloud migration discovery across many applications.

## Files

| File | What it is |
|---|---|
| [`agent.md`](agent.md) | AI Catalog registration fields, the system prompt to copy, evals and limits |
| [`prompt.md`](prompt.md) | Ready-to-use Duo Chat prompts (with and without a Confluence connection, large inputs, follow-ups) |
| [`../../ide/mcp.json`](../../ide/mcp.json) | Shared IDE config to connect GitLab Duo to Confluence Cloud (see [`../../ide/README.md`](../../ide/README.md)) |

## Quick start

1. In GitLab, open **AI Catalog → New agent**.
2. Fill the fields from `agent.md` section 1 and paste the system prompt from section 2.
3. In Duo Chat, select the agent and use a prompt from `prompt.md`.
4. Run the evals in `agent.md` section 3 before sharing it with the team.

> GitLab Duo field names and tool options vary by version. Check them on your instance.
