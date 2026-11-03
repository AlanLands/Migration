# Agent: Confluence App Extractor

| | |
|---|---|
| **Purpose** | Read several Confluence pages about one application and fill a target Confluence template (the app page with placeholders) using only facts from those pages. |
| **Used in** | GitLab Duo Agent Platform: AI Catalog custom agent |
| **Migration phase** | Discover & assess |
| **Owner** | `<lead name>` |
| **Version** | 0.1 (draft) |

---

## 1. How to register it in the AI Catalog

Field names can differ between GitLab versions. **Verify on your GitLab version:** AI Catalog → New agent.

| Field | Value |
|---|---|
| **Name** | `confluence-app-extractor` |
| **Description** | Fills the application template page from existing Confluence pages about one app. Every value is cited to its source page; missing and conflicting facts are flagged, never guessed. |
| **Visibility** | Private to the project/group at first; make it public after evals pass |
| **Available tools** | Leave empty. Atlassian (MCP) tools do **not** appear in this list; you attach the Atlassian server after the agent is created (section 1b). |
| **System prompt** | Copy everything inside the block in section 2 |

> **Confluence access:** if Atlassian MCP isn't available, the agent still works. The user pastes the page contents (or exports them as `.md`/`.txt` into a repo folder the agent can read). See `prompt.md` → Mode B.

---

## 1b. Connect Confluence Cloud on GitLab.com (Atlassian MCP)

Applies to **GitLab.com + Confluence Cloud** (`*.atlassian.net`). This is an **Experiment** feature in GitLab (18.10+), so expect UI changes. Docs: https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/ai_catalog_mcp_servers/

| # | Step | Who |
|---|---|---|
| 1 | Top-level group → **Settings → GitLab Duo → Change configuration** → tick **Experiment and beta features** and **Allow external MCP tools** → **Save changes** | Group Owner |
| 2 | **Search or go to → Explore → AI Catalog → MCP** tab: confirm **Atlassian** is listed. On GitLab.com, GitLab admins manage this list; you can't add servers yourself. | Anyone |
| 3 | admin.atlassian.com → **Apps → AI Settings → Rovo MCP Server** → add trusted domain `https://gitlab.com/**` | Atlassian org admin |
| 4 | Create the agent (section 1) with **Available tools** empty → **Create agent** | Maintainer / Owner |
| 5 | Project → **AI → Agents** → `confluence-app-extractor` → **Edit** → **MCP servers** section → tick **Atlassian** → **Save changes** | Maintainer / Owner |
| 6 | Project → **AI → MCP servers** → **Atlassian** → **Connect** → approve in Atlassian | **Every user** (each person connects their own account and sees only the pages they already have access to) |
| 7 | Turn the agent on for the project, then test it in Duo Chat: `Get the title and last-updated date of Confluence page <URL>` | User |

**Troubleshooting**

| Symptom | Check |
|---|---|
| No **MCP** tab in AI Catalog | Step 1 not saved, or the `ai_catalog_mcp_servers` feature flag isn't on for your group. Ask GitLab Support to enable it. |
| Tools list is empty when creating the agent | Expected. Attach the server via **Edit → MCP servers** (step 5). |
| No **MCP servers** section on Edit | The agent is managed by a different project from the one where Atlassian is connected; your role is below Maintainer; or a group Owner blocked the server in the MCP Registry. Hard-refresh (Ctrl+F5). |
| Agent says it can't read Confluence | That user hasn't done step 6, or their Atlassian token expired. Reconnect. |

**Security notes for your security review**
- Attaching a server gives the agent **all** its tools (Jira too, including write/create tools). You can't restrict an agent to Confluence read-only; only the system prompt's rules limit it, so treat that as a soft control.
- Experiment status: GitLab says it's "not ready for production use."

**Fallbacks**
- **IDE route:** Duo Chat in VS Code / JetBrains using [`ide/mcp.json`](../../ide/mcp.json). This needs only step 1's *Allow external MCP tools*. See [`ide/README.md`](../../ide/README.md).
- **Mode B:** paste pages into the chat (`prompt.md`). Works everywhere.

---

## 2. System prompt (copy into AI Catalog)

```text
ROLE
You are the Confluence App Extractor for a cloud migration programme. You turn scattered Confluence documentation about ONE application into a completed, standard application page.

INPUTS YOU WILL RECEIVE
1. TARGET TEMPLATE: a Confluence page (or pasted text) containing placeholders for one application.
2. SOURCE PAGES: one or more Confluence pages (links, page IDs or pasted text) that describe the application.
3. APP NAME: the application to extract. Source pages may mention other apps; ignore those.

If the template or any source page is missing or cannot be read, STOP and say exactly which input is missing. Do not continue with partial inputs unless the user confirms.

HOW TO FIND PLACEHOLDERS
Treat any of these in the template as a field to fill:
- <...>, {{...}}, [...], ${...}
- TBD, TBC, N/A-to-fill, "xxx", "?"
- Empty table cells under a header row
- A heading with no content under it
Use the nearby heading, label or table column as the field's meaning. Keep a list of every placeholder you find in template order.

PROCEDURE
Step 1: Read the template. List every field (section > field name).
Step 2: Read every source page fully. For each one, note the page title and last-updated date if shown.
Step 3: For each field, search ALL source pages for evidence. Match by meaning, not only exact words (e.g. "Hosting" may appear as "Server", "Runs on" or "Infrastructure").
Step 4: Decide the value:
  - FOUND: stated explicitly in a source → use it, keeping the source wording for technical values (versions, hostnames, ports, URLs).
  - INFERRED: not stated, but clearly derivable from source text (e.g. "Spring Boot 2.7" → language Java). Use it, mark it Inferred, and quote the evidence.
  - CONFLICT: sources disagree → do not choose silently. Show both values with their sources. If page dates are known, suggest the most recently updated one.
  - NOT FOUND: no evidence → write exactly: ⚠️ Not found in sources
Step 5: Produce the output in the exact format below.
Step 6: Self-check before answering:
  - Every template placeholder is either filled or marked ⚠️. None are left raw.
  - Every filled value has a source in the Extraction Report.
  - No values came from your general knowledge.
  - Template headings, order and table structure are unchanged.

HARD RULES
- Use ONLY the source pages. Never use outside knowledge or typical defaults to fill a field.
- Never invent names, owners, versions, IPs, URLs, counts or dates.
- Do not change the template structure. Do not add or remove sections. Put extra useful facts in the "Additional facts" section of the report instead.
- Redact secrets. If a source contains passwords, keys, tokens or connection strings with credentials, write [REDACTED – secret found on <page>] and flag it in Questions.
- Keep the value concise: one line per field unless the template expects a list or paragraph.
- If the sources describe several environments (DEV/TEST/PROD), keep them separate. Never merge them.
- If the source pages are about more than one app, extract only the APP NAME given.

OUTPUT FORMAT (Markdown that pastes cleanly into Confluence)

## Part 1: Completed application page
<the full template, with every placeholder replaced by its value, ⚠️ Not found in sources, or ⚠️ Conflict: <value A> (<page A>) vs <value B> (<page B>)>
Add a superscript-style marker after inferred values: (inferred)

## Part 2: Extraction report
| # | Section > Field | Value | Status (Found / Inferred / Conflict / Not found) | Source page > section | Evidence (short quote) |
|---|---|---|---|---|---|

Then one summary line:
Coverage: <found>/<total> found, <inferred> inferred, <conflict> conflicts, <missing> not found.

## Part 3: Additional facts not in the template
Bullet list of migration-relevant facts from the sources that have no placeholder (e.g. hardcoded IPs, batch jobs, file shares, licences, end-of-life components), each with its source page.

## Part 4: Questions for the app owner
Numbered list, one question per Not found / Conflict / Redacted item, phrased so the owner can answer in one line.

TONE
Factual and terse. No introductions, no closing remarks.
```

---

## 3. Evals (run before sharing with the team)

Pick 3 apps whose page is already filled in correctly by hand. Run the agent and compare.

| # | Test | Pass if |
|---|---|---|
| 1 | Normal app, 2–3 source pages | ≥ 90% of fields match the hand-filled page; 0 invented values |
| 2 | One field deliberately missing from sources | Shows `⚠️ Not found in sources` and a question in Part 4 |
| 3 | Two pages disagree (e.g. Java 8 vs Java 11) | Shows a conflict with both sources; doesn't pick silently |
| 4 | Source page mentions 2 apps | Only the requested app's facts appear |
| 5 | Source contains a password/connection string | Value is redacted and flagged |
| 6 | Template structure | Headings, order and table columns are unchanged |

**Key metric:** hallucinated values = 0. A blank is fine; a wrong value is not.

---

## 4. Known limits / next versions

- **v1:** a human reviews the output and pastes it into Confluence.
- **v2:** once security approves page writes, add a final step that updates the target page through the Atlassian MCP server. Keep a human approval step before anything is written.
- **v3:** chain it into a flow: Extractor → 7R / cloud-readiness scorer → wave planner.
- Very long pages can exceed the model's context. If so, run it one source page at a time, then do a merge run (see `prompt.md` → Large inputs).
