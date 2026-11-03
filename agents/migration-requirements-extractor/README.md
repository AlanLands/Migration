# Migration Requirements Extractor

A GitLab Duo AI Catalog agent that turns a **reviewed** Functional Document (`functional-doc.json`) into an on-prem → cloud **migration requirements register** in Excel. Every requirement is testable, has a MoSCoW priority and traces to a BF/BR/DM/INT/PF/RB/RA ID. Unknown SLAs stay `TBD` with an open question; they're never invented.

Categories: Functional · Data · Integration · Non-functional · Security & Compliance · Operational · Infrastructure · Transition

| File | What it is |
|---|---|
| [`agent.md`](agent.md) | AI Catalog fields, system prompt, evals |
| [`prompt.md`](prompt.md) | Duo Chat prompts and the export command |

Export: `python tools/office-export/export.py docs/requirements.json --functional-doc docs/functional-doc.json --out-dir docs/out`
