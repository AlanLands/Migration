---
name: functional-doc
description: One-command pipeline that creates the Functional Document (Word + Excel + Markdown) for the application in this repository from its source code plus a folder of Confluence documents (Word, PDF, HTML, Excel, images, draw.io). Use when the user says "create the functional doc", "document this app", or gives this repo and a relative path to Confluence documents.
metadata:
  slash-command: enabled
---

# Functional Doc (one command)

Usage in GitLab Duo Chat (IDE), new conversation, app repo open:

```
/functional-doc docs/confluence
/functional-doc docs/confluence APP NAME: Claims Portal
/functional-doc docs/confluence RESCAN
```

It runs four stages and stops only if something is missing:
code scan → prepare documents (text + OCR on images) → build functional doc → export Word/Excel.
Migration requirements are a separate step after SME review: `/migration-requirements-extractor`.

## Instructions

You are the orchestrator for documenting ONE application for an on-premises-to-cloud migration. Follow the stages in order. After each stage, write ONE status line to the user (e.g. "Stage 1/4 done: code spec written, 14 endpoints, 9 entities") and continue without waiting, unless a stage says STOP.

### Stage 0: Inputs
- DOCS PATH: the first path-like argument (relative to the app repo root). If none is given, ask for it once.
  If it doesn't exist, STOP and say so.
- APP NAME: from "APP NAME:" in the message; otherwise the repository/project name. Say which you used.
- RESCAN: present → force a fresh code scan.
- Check that these exist in the repo: `.agents/skills/app-functionality-extractor/SKILL.md`, `.agents/skills/app-functional-doc-builder/SKILL.md`, `tools/doc-prep/prepare_sources.py`, `tools/office-export/export.py`.
  If any is missing, STOP: "The AI toolkit isn't installed in this repo. Run tools/install-to-app-repo.ps1 from the Migration AI repo (see its README)."

### Stage 1/4: Code spec
- If `docs/functional-spec.md` exists and RESCAN is not set: reuse it. Say "reused existing code spec (date)".
- Otherwise: read `.agents/skills/app-functionality-extractor/SKILL.md` and follow its instructions to analyse THIS repository and write `docs/functional-spec.md`. Don't analyse the DOCS PATH folder as code.
- From here on, use the FILE `docs/functional-spec.md` as the code evidence. Don't rely on your memory of the scan.

### Stage 2/4: Prepare the documents
Run in the terminal from the repo root:
```
python tools/doc-prep/prepare_sources.py <DOCS PATH>
```
- It writes `<DOCS PATH>/_extracted/` with one text file per document, one `*.image.md` per image (OCR text), `*.drawio.md` for draw.io diagrams, and `index.md`.
- If the command fails because a Python package is missing, run `python -m pip install -r tools/doc-prep/requirements.txt -r tools/office-export/requirements.txt` once and retry. If you can't run commands, STOP and give the user both commands.
- Read `<DOCS PATH>/_extracted/index.md`. Report: number of documents, images read, OCR engine, secrets redacted, items needing attention.
- If OCR engine is "none", continue, but every image becomes an open question.

### Stage 3/4: Build the functional document
Read `.agents/skills/app-functional-doc-builder/SKILL.md` and follow its instructions with these inputs:
- APP NAME: from Stage 0.
- CODE SPEC: `docs/functional-spec.md`.
- SOURCE DOCUMENTS: every file listed in `<DOCS PATH>/_extracted/index.md` (read them all; do NOT read the original .docx/.pdf/.html files).
- Image rules (in addition to the builder's rules):
  - `*.drawio.md`: connections are exact and can be High confidence for process flows and integrations.
  - `*.image.md` with a "Human description" section: use that description (Medium confidence).
  - `*.image.md` with OCR text only: names of systems/steps found are evidence (Medium); any flow, order or connection you infer from the row layout is Low confidence AND needs an open question "Confirm the flow shown in <image>".
  - Items listed as "unsupported", "error" or "not available locally" in index.md → source register with readable N + an open question.
- Output files: `docs/functional-doc.md` (Part 1) and `docs/functional-doc.json` (Part 2 JSON only, no code fences).

### Stage 4/4: Export and report
Run:
```
python tools/office-export/export.py docs/functional-doc.json --out-dir docs/out
```
- If it reports ERRORS: fix `docs/functional-doc.json` (never by deleting content to silence a check; fix the IDs or references) and re-run, max 2 times. If "possible secret" is reported, find and redact it.
- Final reply to the user, nothing else:
  1. Files created: `docs/functional-spec.md`, `docs/functional-doc.md`, `docs/functional-doc.json`, `docs/out/<app>-functional-doc.xlsx`, `docs/out/<app>-functional-doc.docx`
  2. Counts: business functions, rules, data entities, integrations, process flows, runbook items, risks, open questions, conflicts
  3. The Open Questions and Conflicts tables
  4. "Next: SME reviews the Word/Excel (orange rows = low confidence). Give me their answers to update the doc. Then run /migration-requirements-extractor."

### Rules for the whole run
- Write only inside `docs/` (and `<DOCS PATH>/_extracted/` via the script). Never modify source code, build files or the original documents.
- Never invent facts. Gaps become open questions.
- Never print secret values. The prepare step redacts common patterns; if you still see one, write [REDACTED] and raise a risk.
- If the context gets too large: finish the current stage, make sure its output file is complete, then tell the user to start a new conversation with `/functional-doc <DOCS PATH>`. Stages whose output files exist are reused (Stage 1 reuses the code spec; for Stage 3, if `docs/functional-doc.json` exists, ask whether to rebuild or only re-export).
