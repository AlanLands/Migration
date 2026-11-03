# office-export: agent JSON → Excel / Word

GitLab Duo agents return text, not files. This script turns the JSON block from

| Agent | `doc_type` | Output |
|---|---|---|
| `app-functional-doc-builder` | `functional_doc` | `<app>-functional-doc.xlsx` (one sheet per section) + `<app>-functional-doc.docx` |
| `migration-requirements-extractor` | `migration_requirements` | `<app>-migration-requirements.xlsx` (Requirements with dropdowns, live Summary, Assumptions, Open Questions, Coverage Gaps) |

It also **validates** the JSON: missing sections, duplicate IDs, broken cross-references (a BR pointing to a BF that doesn't exist, a REQ tracing to a missing ID), uncovered BF/DM/INT items, unreadable images without an open question, and anything that looks like a secret. **If it finds errors, it writes nothing** (use `--force` to override).

## Setup (once)

```powershell
python -m pip install -r tools/office-export/requirements.txt
```

## Use

```powershell
# Functional doc → Excel + Word
python tools/office-export/export.py docs/functional-doc.json --out-dir docs/out

# Split runs (large apps) are merged; later files win on the same ID
python tools/office-export/export.py functional-doc.part1.json functional-doc.part2.json --out-dir docs/out

# A saved Duo Chat answer (.md) works too; the ```json block is extracted
python tools/office-export/export.py chat-answer.md --out-dir docs/out

# Requirements → Excel, with traceability checked against the functional doc
python tools/office-export/export.py docs/requirements.json --functional-doc docs/functional-doc.json --out-dir docs/out

# Validate only (for CI)
python tools/office-export/export.py docs/requirements.json --functional-doc docs/functional-doc.json --check
```

Try it with `samples/` first.

## What you get

| Feature | Detail |
|---|---|
| Low-confidence rows | Highlighted orange so reviewers look at them first |
| Process flows | Steps sheet + a Mermaid sheet (paste into a Confluence Mermaid macro or mermaid.live). Word shows numbered steps plus the Mermaid text; diagrams are not rendered. |
| Requirements sheet | Dropdowns for Category, Priority, Status, Confidence. Summary counts use `COUNTIFS`, so they update as reviewers edit. |

## CI job (optional)

Fails the MR if the agent's JSON is broken, and publishes the Excel/Word files as artifacts. **Verify the image and paths for your runners.**

```yaml
functional-docs:
  stage: test
  image: python:3.12-slim
  rules:
    - changes: [docs/functional-doc.json, docs/requirements.json]
  script:
    - pip install -q -r tools/office-export/requirements.txt
    - python tools/office-export/export.py docs/functional-doc.json --out-dir docs/out
    - if [ -f docs/requirements.json ]; then python tools/office-export/export.py docs/requirements.json --functional-doc docs/functional-doc.json --out-dir docs/out; fi
  artifacts:
    paths: [docs/out/]
    expire_in: 30 days
```

In app repos the tool usually isn't present. Either copy `tools/office-export/` in, or add a `git clone` / CI include of the AI repo before `script`.
