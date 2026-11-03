# Prompts: Confluence App Extractor

Copy these into Duo Chat after selecting the **confluence-app-extractor** agent. Replace the `<...>` parts.

---

## Mode A: Duo can read Confluence (MCP connected)

```text
APP NAME: <App name, e.g. SMA>

TARGET TEMPLATE PAGE:
<Confluence URL or page ID of the page with placeholders>

SOURCE PAGES:
1. <URL or page ID>
2. <URL or page ID>
3. <URL or page ID>

Fill the target template for this app using only the source pages. Follow your output format (Parts 1–4).
```

---

## Mode B: No Confluence connection (paste the content)

In Confluence, open each page → **⋯ → Export → Word/PDF**, or simply select all and copy. Paste below.

```text
APP NAME: <App name>

=== TARGET TEMPLATE ===
<paste the template page here>
=== END TEMPLATE ===

=== SOURCE PAGE 1: <page title> (last updated: <date>) ===
<paste>
=== END SOURCE PAGE 1 ===

=== SOURCE PAGE 2: <page title> (last updated: <date>) ===
<paste>
=== END SOURCE PAGE 2 ===

Fill the target template for this app using only the source pages. Follow your output format (Parts 1–4).
```

The `===` markers help the agent cite the right page, so keep them.

---

## Large inputs (pages too long for one message)

**Run 1 to N:** one source page per run:
```text
APP NAME: <App name>
=== TARGET TEMPLATE === <paste> === END TEMPLATE ===
=== SOURCE PAGE <n>: <title> === <paste> === END ===
Produce only Part 2 (Extraction report) for this one page.
```

**Final run:** merge the results:
```text
APP NAME: <App name>
=== TARGET TEMPLATE === <paste> === END TEMPLATE ===
Below are extraction reports from <N> separate source pages. Merge them: resolve duplicates, flag conflicts, then produce Parts 1–4.
<paste each Part 2 table>
```

---

## Follow-up prompts

| Need | Prompt |
|---|---|
| Owner answered questions | `The app owner answered: <paste answers>. Update Part 1 and Part 2, and remove the answered questions from Part 4.` |
| Page only, ready to paste | `Give me only Part 1, with no markers or commentary.` |
| Check an existing filled page | `Here is a filled app page and its source pages. Check every value against the sources and list any that are unsupported or wrong.` |
| Same template, next app | `Same template. New APP NAME: <name>. New SOURCE PAGES: <...>` |
