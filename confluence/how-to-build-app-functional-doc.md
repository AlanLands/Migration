# How to build an app's Functional Document and Migration Requirements with GitLab Duo

## TL;DR
- Three Duo agents run in sequence: **code spec → functional doc → migration requirements**.
- You get a Word doc and an Excel workbook for the functional doc, and an Excel requirements register.
- Everything is an AI DRAFT. An SME must review it before requirements are extracted.

**Who it's for:** migration engineers and BAs onboarding an application to a wave.

## Before you start
| Need | Where |
|---|---|
| App repo cloned locally, opened in VS Code / JetBrains with GitLab Duo | Your IDE |
| Agents enabled for your project: `App Functionality Extractor`, `app-functional-doc-builder`, `migration-requirements-extractor` | Project → AI → Agents |
| Confluence page links for the app (or exported copies) | Confluence |
| Python 3.10+ with `pip install -r tools/office-export/requirements.txt` | Your PC (or use the CI job) |

## Steps

1. **Scan the code.** In Duo Chat, select **App Functionality Extractor**:
   ```text
   Analyze this repository and produce the full functional specification using your standard format.
   ```
   Save the answer as `docs/functional-spec.md`.

2. **Build the functional doc.** Select **app-functional-doc-builder**:
   ```text
   APP NAME: <App name>
   CODE SPEC: docs/functional-spec.md (in this repo)
   SOURCE DOCUMENTS:
   1. <Confluence URL>
   2. <Confluence URL>
   Build the Functional Document for this app. Produce Part 1 and Part 2.
   ```
   No Confluence connection? Paste the pages and describe each diagram in an `=== IMAGE n ===` block (see the agent's `prompt.md`, Mode B).

3. **Export.** Copy the JSON block into `docs/functional-doc.json`, then run:
   ```powershell
   python tools/office-export/export.py docs/functional-doc.json --out-dir docs/out
   ```
   If it reports errors, paste them back into Duo Chat: `Fix these errors in your JSON: <errors>`.

4. **SME review.** Send the `.docx` / `.xlsx` to the app owner. Focus on orange (Low confidence) rows, Open Questions and Conflicts. Feed answers back:
   ```text
   The SME answered: <OQ-001: ..., CF-001: ...>. Update Parts 1 and 2, keep IDs stable.
   ```
   Paste the final Part 1 into the app's Confluence page.

5. **Extract migration requirements.** Select **migration-requirements-extractor**:
   ```text
   FUNCTIONAL DOC: docs/functional-doc.json
   TARGET CONTEXT: Cloud <...>, pattern <...>, compliance <...>, downtime <...>
   Build the migration requirements register. Produce Part 1 and Part 2.
   ```
   Save the JSON as `docs/requirements.json`, then run:
   ```powershell
   python tools/office-export/export.py docs/requirements.json --functional-doc docs/functional-doc.json --out-dir docs/out
   ```

## When it goes wrong
| Symptom | Fix |
|---|---|
| Answer stops mid-way | Use the split runs in the agent's `prompt.md` → *Large apps*; `export.py` merges the parts |
| "possible secret value found" | Don't share the files. Ask the agent to redact it, and tell the app owner a secret is stored in docs/code |
| Diagram content missing | Expected if Duo can't see images. Add an `=== IMAGE ===` description and rerun |
| Requirements have invented SLAs | Reject them. Values must be `TBD` plus an open question. Report it to the agent owner so the eval set can be updated |
| `traces_to ... not found` | The functional doc changed after the requirements run. Rerun step 5 |

## Escalate to
- Agent behaviour or prompts: `<AI lead name / channel>`
- App facts: the app owner listed in the functional doc
