# IDE route: connect GitLab Duo to Confluence Cloud

Use this when the AI Catalog **MCP servers** option isn't available yet. It works in GitLab Duo Chat inside VS Code or JetBrains, but AI Catalog agents aren't available on this route.

## Prerequisites
- A top-level group Owner has ticked **Settings → GitLab Duo → Change configuration → Allow external MCP tools**.
- GitLab for VS Code 6.35.6 or later, or the JetBrains GitLab Duo plugin 3.14.0 or later.
- Confluence Cloud (`*.atlassian.net`). Your Atlassian admin may need to allow this client under **Apps → AI Settings → Rovo MCP Server**.

## Setup
1. Copy the content of [`mcp.json`](mcp.json) into one of these:
   - **VS Code:** Command Palette → `GitLab MCP: Open User Settings (JSON)`
   - **JetBrains (Windows):** `%APPDATA%\GitLab\duo\mcp.json`
   - **JetBrains (macOS/Linux):** `~/.gitlab/duo/mcp.json`
   - **One repo only:** `.gitlab/duo/mcp.json` in that repo
2. Restart the IDE.
3. In Duo Chat, ask a Confluence question. Sign in to Atlassian when the browser opens.
4. Paste the system prompt from the agent's `agent.md` (e.g. [confluence-app-extractor](../agents/confluence-app-extractor/agent.md)) at the start of the chat, then use Mode A from that agent's `prompt.md`.

## Troubleshooting
- **VS Code:** Command Palette → `GitLab: Show MCP Dashboard` shows the connection status and tools.
- **Stale login:** delete the `~/.mcp-auth/` folder and try again.

Docs: https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_clients/
