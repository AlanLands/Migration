# Prompts: App Functional Doc Builder

In Duo Chat in your IDE, start a **new** conversation and type `/app-functional-doc-builder`, then one of these prompts. The skill writes `docs/functional-doc.md` and `docs/functional-doc.json` and runs the Excel/Word export itself. The sections below are for when you need more control. Replace the `<...>` parts.

**Before you start:** run the **App Functionality Extractor** on the app repo and save its output as `docs/functional-spec.md` in your local clone (IDE route) or keep it ready to paste.

---

## Mode A: IDE with the repo open and Confluence connected (MCP)

```text
APP NAME: <App name>

CODE SPEC: docs/functional-spec.md (in this repo)

SOURCE DOCUMENTS:
1. <Confluence URL or page ID>
2. <Confluence URL or page ID>
3. <Confluence URL or page ID>

Build the Functional Document for this app. Produce Part 1 and Part 2.
If a page has images or diagrams you can't see, list them as open questions.
```

---

## Mode B: No Confluence connection (paste content and describe images)

Export each page (**⋯ → Export → Word/PDF**) or select all and copy. For each diagram or screenshot, type what it shows in an IMAGE block. Short bullet steps are enough.

```text
APP NAME: <App name>

=== CODE SPEC ===
<paste docs/functional-spec.md>
=== END CODE SPEC ===

=== SOURCE 1: <page title> (last updated: <date>) ===
<paste page text>
=== END SOURCE 1 ===

=== SOURCE 2: <page title> (last updated: <date>) ===
<paste page text>
=== END SOURCE 2 ===

=== IMAGE 1: <diagram name> (on page <page title>) ===
- Customer submits claim in Portal
- Portal calls ClaimsAPI (REST)
- ClaimsAPI writes CLAIM table, puts message on MQ CLAIMS.IN
- Nightly batch picks up and sends file to FinanceSys via SFTP
=== END IMAGE 1 ===

Build the Functional Document for this app. Produce Part 1 and Part 2.
```

> If your Duo Chat lets you attach images, try attaching the diagram directly and check that the output cites it as an image source. **Verify on your GitLab version.** If it doesn't, use IMAGE blocks.

---

## Large apps (output too long)

| Run | Prompt |
|---|---|
| 1 | `<inputs as above> Produce Part 1 sections 1–5 only.` |
| 2 | `CONTINUE: produce Part 1 sections 6–10 and the Source Register.` |
| 3 | `Give me Part 2 (the JSON) for sections overview, business_functions, business_rules, data_model.` |
| 4 | `Give me Part 2 (the JSON) for integrations, process_flows, runbook, risks, open_questions, conflicts. Repeat doc_type, schema_version, meta and sources.` |

Save runs 3 and 4 as `functional-doc.part1.json` and `functional-doc.part2.json`. `export.py` merges them (see `tools/office-export/README.md`).

---

## Follow-ups

| Need | Prompt |
|---|---|
| SME answered questions | `The SME answered: <paste answers with OQ IDs>. Update Parts 1 and 2. Close the answered OQs, raise confidence where answers confirm items, and keep IDs stable.` |
| Resolve a conflict | `CF-003: the correct value is <x> (confirmed by <name/role>). Update the affected items and mark CF-003 resolved.` |
| Only the JSON | `Give me only Part 2.` |
| Check before export | `Validate your JSON: every BR has a function_id that exists, every related ID exists, no empty source fields. List problems, then output the corrected JSON.` |
| Next app | `Same format. New APP NAME: <name>. New CODE SPEC and SOURCES: <...>` |

---

## After the chat: make the Excel and Word files

1. Copy the JSON block into `docs/functional-doc.json` in the app repo (or any folder).
2. Run:
   ```powershell
   python tools/office-export/export.py docs/functional-doc.json --out-dir docs/out
   ```
3. You get `<app>-functional-doc.xlsx` (one sheet per section) and `<app>-functional-doc.docx`.
4. Send both to the SME for review. Paste Part 1 into Confluence.
