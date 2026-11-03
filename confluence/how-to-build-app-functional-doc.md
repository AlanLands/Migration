# How to build an app's Functional Document and Migration Requirements with GitLab Duo

## TL;DR
- Three Duo skills (slash commands) run in sequence: **code spec → functional doc → migration requirements**.
- You get a Word doc and an Excel workbook for the functional doc, and an Excel requirements register.
- Everything is an AI DRAFT. An SME must review it before requirements are extracted.

**Who it's for:** migration engineers and BAs onboarding an application to a wave.

## Before you start
| Need | Where |
|---|---|
| VS Code with GitLab for VS Code **6.71.4+**, Duo enabled | Your PC |
| Python 3.10+ | Your PC |
| The `Migration` AI repo cloned | Your PC |
| Confluence pages for the app | Confluence |

## Steps

1. **Clone the app repo.**
   ```powershell
   git clone <app-repo-url> C:\work\<app>
   ```
2. **Install the AI toolkit into it** (run from the Migration AI repo folder):
   ```powershell
   .\tools\install-to-app-repo.ps1 -AppRepo C:\work\<app> -InstallPython
   ```
3. **Copy the Confluence documents** into `C:\work\<app>\docs\confluence\`:
   - Each page: **⋯ → Export → Word** (or HTML, keeping the `attachments` folder)
   - draw.io diagrams: open the diagram → **Export → XML** → save as `<name>.drawio` (gives exact flows)
   - Other images: just copy them. For the 2–3 most important diagrams, add `<image-name>.image.md` with the flow in words.
   - Remove passwords and customer data first. The tool redacts common secret patterns, but don't rely on it.
4. **Run one command.** Open the app repo in VS Code → GitLab Duo Chat → **new conversation** → check `/skills` lists `functional-doc` → run:
   ```text
   /functional-doc docs/confluence APP NAME: <App name>
   ```
   Approve file writes and the `python` commands when Duo asks. It reports progress per stage (code scan, document prep, build, export).
5. **Get the outputs** in `docs/out/`: `<app>-functional-doc.docx` and `.xlsx`. Also `docs/functional-doc.md` (paste into Confluence).
6. **SME review.** Focus on orange (Low confidence) rows, Open Questions, Conflicts, and anything taken from images. Feed the answers back in the same conversation:
   ```text
   The SME answered: <OQ-001: ..., CF-001: ...>. Update both files, keep IDs stable, re-export.
   ```
7. **Migration requirements** (after review). New conversation:
   ```text
   /migration-requirements-extractor Cloud: <AWS|Azure|GCP|not decided>. Pattern: <rehost|replatform|refactor|not decided>. Compliance: <...>. Downtime window: <...>.
   ```
   Output: `docs/out/<app>-migration-requirements.xlsx`.
8. **Commit** `docs/` on a branch and open an MR.

## When it goes wrong
| Symptom | Fix |
|---|---|
| Answer stops mid-way | Say `continue`. The skill appends to the files. If the JSON is still broken, use the split runs in `agents/<name>/prompt.md` → *Large apps*; `export.py` merges the parts |
| `/skills` doesn't list them | New conversation; check the VS Code extension version; if it's a multi-root workspace, copy `.agents/` into the app repo (README option B) |
| Duo can't run `python` | Run the export command it gives you in a terminal yourself |
| "possible secret value found" | Don't share the files. Ask the agent to redact it, and tell the app owner a secret is stored in docs/code |
| Diagram flow wrong or missing | OCR reads labels, not arrows. Export the diagram as `.drawio`, or add `<image>.image.md` next to the image, then re-run `/functional-doc` |
| `OCR engine: none` in Stage 2 | Run `python -m pip install -r tools/doc-prep/requirements.txt` (needs Windows 10/11 for winocr) |
| "toolkit isn't installed" | Run step 2 again |
| Requirements have invented SLAs | Reject them. Values must be `TBD` plus an open question. Report it to the agent owner so the eval set can be updated |
| `traces_to ... not found` | The functional doc changed after the requirements run. Rerun step 7 |

## Escalate to
- Agent behaviour or prompts: `<AI lead name / channel>`
- App facts: the app owner listed in the functional doc
