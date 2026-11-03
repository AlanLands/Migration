# Prompts: Migration Requirements Extractor

In Duo Chat in your IDE, start a **new** conversation and type `/migration-requirements-extractor`, then one of these prompts. The skill writes `docs/requirements.md` / `.json` and runs the Excel export itself.

**Before you start:** an SME has reviewed the app's `functional-doc.json`, and its open questions and conflicts are answered (or explicitly accepted).

---

## Standard run (IDE, repo open)

```text
FUNCTIONAL DOC: docs/functional-doc.json

TARGET CONTEXT:
- Cloud: <AWS | Azure | GCP | not decided>
- Target pattern: <rehost | replatform (containers) | refactor | not decided>
- Compliance: <PCI | HIPAA | SOX | GDPR | none known>
- Downtime window: <e.g. 4h Sunday night | unknown>

Build the migration requirements register. Produce Part 1 and Part 2.
```

## Paste run (no repo access)

```text
=== FUNCTIONAL DOC ===
<paste functional-doc.json>
=== END FUNCTIONAL DOC ===

TARGET CONTEXT: <as above, or "not decided">

Build the migration requirements register. Produce Part 1 and Part 2.
```

## Large apps

| Run | Prompt |
|---|---|
| 1 | `<inputs> Output Part 2 for categories Functional and Data only.` |
| 2 | `Continue with Integration, Non-functional and Security & Compliance. Continue numbering from the last REQ ID.` |
| 3 | `Continue with Operational, Infrastructure and Transition, then assumptions, open_questions and coverage_gaps.` |

Save each run as `requirements.partN.json`. `export.py` merges them.

## Follow-ups

| Need | Prompt |
|---|---|
| Target context decided later | `Target is now <cloud / pattern>. Update Infrastructure and Integration requirements; keep REQ IDs stable; list what changed.` |
| Review feedback | `Reviewer comments: <REQ-ID: comment ...>. Apply them, keep IDs stable, output the full JSON.` |
| Coverage check | `List every BF, DM and INT ID in the functional doc and the REQ IDs that cover it. Mark any without coverage.` |

## Make the Excel file

```powershell
python tools/office-export/export.py docs/requirements.json --out-dir docs/out
```

Output: `<app>-migration-requirements.xlsx` with the sheets Requirements, Summary, Assumptions, Open Questions and Coverage Gaps.
