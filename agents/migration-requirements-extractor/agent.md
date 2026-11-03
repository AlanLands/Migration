# Agent: Migration Requirements Extractor

| | |
|---|---|
| **Purpose** | Turn an approved Functional Document into a traceable register of on-prem → cloud migration requirements, delivered as JSON that exports to Excel. |
| **Used in** | GitLab Duo Chat in the IDE, as a project-level **Agent Skill**: `/migration-requirements-extractor` |
| **Migration phase** | Discover & assess → Plan waves |
| **Upstream** | `app-functional-doc-builder` → `functional-doc.json` (**after SME review**) |
| **Downstream** | `tools/office-export/export.py` → `<app>-migration-requirements.xlsx`; later the wave planner, Terraform generator and test generator |
| **Owner** | `<lead name>` |
| **Version** | 0.1 (draft) |

---

## 1. Why it's a separate agent

- The functional doc describes what the app does **today**. Requirements describe what the cloud version **must do**. Mixing the two in one prompt makes the model invent target-state requirements as if they were facts.
- Run it **only after an SME has reviewed the functional doc**. Requirements built on an unreviewed draft repeat its errors with more confidence.
- Every requirement traces back to a BF/BR/DM/INT/PF/RB/RA ID, so reviewers can check it and the testers can build test cases from it.

---

## 2. Where the instructions live

The instructions are in [`.agents/skills/migration-requirements-extractor/SKILL.md`](../../.agents/skills/migration-requirements-extractor/SKILL.md). That file is the **single source of truth**, so edit it there. No AI Catalog registration is needed: Duo Chat in VS Code (GitLab for VS Code 6.71.4+, GitLab 18.10+) loads project skills from `.agents/skills/` and offers them as slash commands. See the repo README → *How to use the skills*. Docs: https://docs.gitlab.com/user/duo_agent_platform/customize/agent_skills/

---

## 3. Evals

| # | Test | Pass if |
|---|---|---|
| 1 | Reviewed functional doc for a known app | Every BF, DM, INT covered (coverage_gaps empty or justified) |
| 2 | Functional doc has no SLA values | NFRs use "TBD" + an OQ; no invented numbers |
| 3 | Requirements are testable | A tester can write a test from ≥ 90% of acceptance criteria without asking |
| 4 | Traceability | Every `traces_to` ID exists in the functional doc, or is BASELINE with an assumption |
| 5 | No target context given | No cloud product names appear in requirements |
| 6 | JSON validity | `export.py` runs with 0 errors |

---

## 4. Next versions

- **v2:** a CI job checks that each requirement's `traces_to` exists (`export.py --check`) and fails the MR if not.
- **v3:** feed `Must` requirements into the smoke/regression test generator, and the Infrastructure ones into the Terraform module generator.
