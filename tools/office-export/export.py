#!/usr/bin/env python3
"""Convert GitLab Duo agent JSON output into Excel (.xlsx) and Word (.docx).

Supported doc types (the "doc_type" key in the JSON):
  functional_doc          -> <app>-functional-doc.xlsx + <app>-functional-doc.docx
  migration_requirements  -> <app>-migration-requirements.xlsx

Usage:
  python export.py docs/functional-doc.json --out-dir docs/out
  python export.py part1.json part2.json --out-dir out          # merges split runs
  python export.py chat-output.md                               # pulls the ```json block out of a saved chat
  python export.py docs/requirements.json --functional-doc docs/functional-doc.json --check

--check  validates only (no files written); exit code 1 if there are errors.
Files are NOT written when validation finds errors (e.g. a possible secret) unless --force is given.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from docx import Document
from docx.shared import Pt

# --------------------------------------------------------------------------- schema

FUNCTIONAL_SECTIONS = [
    # (json key, sheet / heading title, columns)
    ("sources", "Sources", ["id", "type", "title", "ref", "last_updated", "readable"]),
    ("business_functions", "Business Functions",
     ["id", "name", "description", "trigger", "actors", "related_rules", "source", "confidence"]),
    ("business_rules", "Business Rules",
     ["id", "rule", "function_id", "type", "enforced_in", "source", "confidence"]),
    ("data_model", "Data Model",
     ["id", "entity", "description", "key_attributes", "relationships", "datastore",
      "read_by", "written_by", "volume", "pii", "source", "confidence"]),
    ("integrations", "Integrations",
     ["id", "system", "direction", "protocol", "frequency", "data", "purpose",
      "config_location", "source", "confidence"]),
    ("process_flows", "Process Flows", None),  # flattened specially
    ("runbook", "Runbook", ["id", "task", "when", "steps", "owner", "source", "confidence"]),
    ("risks", "Risks & Actions", ["id", "risk", "impact", "likelihood", "action", "owner", "source"]),
    ("open_questions", "Open Questions", ["id", "question", "why_it_matters", "ask", "related_ids"]),
    ("conflicts", "Conflicts",
     ["id", "topic", "value_a", "source_a", "value_b", "source_b", "recommendation"]),
]
OVERVIEW_FIELDS = ["purpose", "business_owner", "users", "criticality", "current_hosting",
                   "tech_stack", "scope", "source"]
FLOW_COLUMNS = ["flow_id", "flow_name", "step", "actor", "action", "system", "refs", "source", "confidence"]

REQ_SECTIONS = [
    ("requirements", "Requirements",
     ["id", "category", "title", "description", "acceptance_criteria", "priority",
      "traces_to", "source", "confidence", "owner", "status"]),
    ("assumptions", "Assumptions", ["id", "assumption", "impact_if_wrong", "related_ids"]),
    ("open_questions", "Open Questions", ["id", "question", "why_it_matters", "ask", "related_ids"]),
    ("coverage_gaps", "Coverage Gaps", ["item_id", "reason"]),
]
REQ_CATEGORIES = ["Functional", "Data", "Integration", "Non-functional", "Security & Compliance",
                  "Operational", "Infrastructure", "Transition"]
PRIORITIES = ["Must", "Should", "Could", "Won't"]

ID_RE = re.compile(r"\b(?:BF|BR|DM|INT|PF|RB|RA|OQ|CF|REQ|AS)-\d{3,}\b")

# --------------------------------------------------------------------------- loading


def extract_json(text, path):
    """Accept raw JSON or a Markdown chat transcript containing ```json blocks."""
    text = text.strip()
    if text.startswith("{"):
        return [json.loads(text)]
    blocks = re.findall(r"```json\s*(.*?)```", text, flags=re.S)
    if not blocks:
        raise ValueError(f"{path}: no JSON object or ```json block found")
    out = []
    for b in blocks:
        obj = json.loads(b)
        if isinstance(obj, dict) and "doc_type" in obj:
            out.append(obj)
    if not out:
        raise ValueError(f"{path}: ```json blocks found but none has a doc_type key")
    return out


def merge(docs):
    """Merge split runs: dicts shallow-merged, lists concatenated and de-duplicated by id."""
    types = {d.get("doc_type") for d in docs}
    if len(types) != 1:
        raise ValueError(f"inputs mix doc types: {sorted(map(str, types))}")
    merged = {}
    for d in docs:
        for k, v in d.items():
            if isinstance(v, list):
                bucket = merged.setdefault(k, [])
                seen = {i.get("id") or i.get("item_id") for i in bucket if isinstance(i, dict)}
                for item in v:
                    key = item.get("id") or item.get("item_id") if isinstance(item, dict) else None
                    if key and key in seen:
                        # later run wins (e.g. a corrected re-run)
                        bucket[:] = [item if (i.get("id") or i.get("item_id")) == key else i for i in bucket]
                    else:
                        bucket.append(item)
                        seen.add(key)
            elif isinstance(v, dict):
                target = merged.setdefault(k, {})
                for kk, vv in v.items():  # don't let an empty value in a later run wipe a filled one
                    if vv not in ("", None) or kk not in target:
                        target[kk] = vv
            else:
                merged[k] = v
    return merged


def s(v):
    """Cell-safe string."""
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(s(i) for i in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)

# --------------------------------------------------------------------------- validation


def validate(doc, functional_ref=None):
    errors, warnings = [], []
    dt = doc.get("doc_type")
    sections = FUNCTIONAL_SECTIONS if dt == "functional_doc" else REQ_SECTIONS
    known_ids = set()
    for key, _, _ in sections:
        items = doc.get(key)
        if items is None:
            errors.append(f"missing section '{key}'")
            continue
        if not isinstance(items, list):
            errors.append(f"section '{key}' must be a list")
            continue
        ids = [i.get("id") for i in items if isinstance(i, dict) and i.get("id")]
        for dup, n in Counter(ids).items():
            if n > 1:
                errors.append(f"{key}: duplicate id {dup}")
        known_ids.update(ids)
        for i in items:
            if not isinstance(i, dict):
                errors.append(f"{key}: item is not an object: {i!r}")
                continue
            if "source" in i and not s(i.get("source")).strip() and key not in ("sources",):
                warnings.append(f"{i.get('id', key)}: empty source")
            if "confidence" in i and s(i["confidence"]) not in ("High", "Medium", "Low"):
                warnings.append(f"{i.get('id', key)}: confidence '{s(i['confidence'])}' not High/Medium/Low")

    if dt == "functional_doc":
        if not doc.get("meta", {}).get("app_name"):
            errors.append("meta.app_name is empty")
        bf = {i["id"] for i in doc.get("business_functions", []) if i.get("id")}
        for r in doc.get("business_rules", []):
            if r.get("function_id") and r["function_id"] not in bf:
                errors.append(f"{r.get('id')}: function_id {r['function_id']} not found in business_functions")
        src_ids = {i.get("id") for i in doc.get("sources", [])}
        unreadable = [i["id"] for i in doc.get("sources", []) if s(i.get("readable")).upper() == "N"]
        oq_text = " ".join(s(q) for q in doc.get("open_questions", []))
        for u in unreadable:
            if u not in oq_text:
                warnings.append(f"source {u} is not readable but no open question mentions it")
        for key, _, _ in FUNCTIONAL_SECTIONS:
            for i in doc.get(key, []) or []:
                for ref in re.findall(r"\bS\d+\b", s(i.get("source"))):
                    if ref not in src_ids:
                        warnings.append(f"{i.get('id')}: cites {ref}, which is not in sources")
        all_ids = known_ids
    else:
        if not doc.get("meta", {}).get("app_name"):
            errors.append("meta.app_name is empty")
        for r in doc.get("requirements", []):
            if r.get("category") not in REQ_CATEGORIES:
                warnings.append(f"{r.get('id')}: category '{r.get('category')}' not in {REQ_CATEGORIES}")
            if r.get("priority") not in PRIORITIES:
                warnings.append(f"{r.get('id')}: priority '{r.get('priority')}' not MoSCoW")
            if not s(r.get("traces_to")).strip():
                errors.append(f"{r.get('id')}: traces_to is empty (every requirement must trace)")
        all_ids = set(known_ids)
        if functional_ref:
            for key, _, _ in FUNCTIONAL_SECTIONS:
                all_ids.update(i.get("id") for i in functional_ref.get(key, []) if isinstance(i, dict))
            covered = set()
            for r in doc.get("requirements", []):
                for ref in ID_RE.findall(s(r.get("traces_to"))):
                    covered.add(ref)
                    if ref not in all_ids:
                        errors.append(f"{r.get('id')}: traces_to {ref} not found in functional doc")
            gaps = {g.get("item_id") for g in doc.get("coverage_gaps", [])}
            for key in ("business_functions", "data_model", "integrations"):
                for i in functional_ref.get(key, []):
                    if i.get("id") not in covered and i.get("id") not in gaps:
                        warnings.append(f"{i.get('id')} has no requirement and is not listed in coverage_gaps")

    # dangling cross-references inside the doc itself
    if dt == "functional_doc":
        for key, _, _ in FUNCTIONAL_SECTIONS:
            for i in doc.get(key, []) or []:
                for f in ("related_rules", "related_ids", "refs"):
                    for ref in ID_RE.findall(s(i.get(f))):
                        if ref not in all_ids:
                            warnings.append(f"{i.get('id')}: {f} references unknown {ref}")
            for flow in doc.get("process_flows", []) or []:
                for st in flow.get("steps", []) or []:
                    for ref in ID_RE.findall(s(st.get("refs"))):
                        if ref not in all_ids:
                            warnings.append(f"{flow.get('id')} step {st.get('step')}: unknown ref {ref}")

    # secret smell test
    blob = json.dumps(doc)
    if re.search(r"(?i)(password|pwd|secret|apikey|api_key)\s*[=:]\s*[^\s\"\[,;]{4,}", blob):
        errors.append("possible secret value found in output: review before sharing")
    return errors, sorted(set(warnings))

# --------------------------------------------------------------------------- excel

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
LOW_FILL = PatternFill("solid", fgColor="FCE4D6")
WRAP = Alignment(wrap_text=True, vertical="top")
WIDE = {"description", "rule", "action", "steps", "question", "why_it_matters", "acceptance_criteria",
        "purpose", "risk", "recommendation", "assumption", "impact_if_wrong", "reason", "value_a", "value_b",
        "data", "relationships", "key_attributes", "title", "ref"}


def title_case(col):
    return col.replace("_", " ").title().replace("Id", "ID").replace("Pii", "PII")


def add_table_sheet(wb, title, columns, rows):
    ws = wb.create_sheet(title[:31])
    ws.append([title_case(c) for c in columns])
    for c in ws[1]:
        c.fill, c.font, c.alignment = HEADER_FILL, HEADER_FONT, WRAP
    for r in rows:
        ws.append([s(r.get(c)) for c in columns])
    conf_col = columns.index("confidence") + 1 if "confidence" in columns else None
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = WRAP
        if conf_col and row[conf_col - 1].value == "Low":
            for c in row:
                c.fill = LOW_FILL
    for idx, col in enumerate(columns, 1):
        ws.column_dimensions[get_column_letter(idx)].width = 50 if col in WIDE else (12 if col == "id" else 22)
    ws.freeze_panes = "B2"
    if rows:
        ws.auto_filter.ref = ws.dimensions
    return ws


def add_kv_sheet(wb, title, pairs):
    ws = wb.create_sheet(title)
    ws.append(["Field", "Value"])
    for c in ws[1]:
        c.fill, c.font = HEADER_FILL, HEADER_FONT
    for k, v in pairs:
        ws.append([title_case(k), s(v)])
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 100
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = WRAP
    return ws


def flatten_flows(flows):
    rows = []
    for f in flows or []:
        steps = f.get("steps") or [{}]
        for st in steps:
            rows.append({"flow_id": f.get("id"), "flow_name": f.get("name"), **st,
                         "source": f.get("source"), "confidence": f.get("confidence")})
    return rows


def functional_xlsx(doc, path):
    wb = Workbook()
    wb.remove(wb.active)
    meta = doc.get("meta", {})
    add_kv_sheet(wb, "Overview",
                 [(k, meta.get(k)) for k in meta] + [(k, doc.get("overview", {}).get(k)) for k in OVERVIEW_FIELDS])
    for key, title, cols in FUNCTIONAL_SECTIONS:
        if key == "process_flows":
            add_table_sheet(wb, title, FLOW_COLUMNS, flatten_flows(doc.get(key)))
            mer = wb.create_sheet("Flow Diagrams (Mermaid)")
            mer.append(["Flow ID", "Name", "Mermaid (paste into Confluence Mermaid macro / mermaid.live)"])
            for c in mer[1]:
                c.fill, c.font = HEADER_FILL, HEADER_FONT
            for f in doc.get(key) or []:
                mer.append([s(f.get("id")), s(f.get("name")), s(f.get("mermaid"))])
            mer.column_dimensions["B"].width = 30
            mer.column_dimensions["C"].width = 100
            for row in mer.iter_rows(min_row=2):
                for c in row:
                    c.alignment = WRAP
        else:
            add_table_sheet(wb, title, cols, doc.get(key) or [])
    wb.save(path)


def requirements_xlsx(doc, path):
    wb = Workbook()
    wb.remove(wb.active)
    reqs = doc.get("requirements") or []
    ws = add_table_sheet(wb, "Requirements", REQ_SECTIONS[0][2], reqs)
    # reviewer dropdowns
    cols = REQ_SECTIONS[0][2]
    last = max(len(reqs) + 1, 2) + 200  # leave room for reviewers to add rows
    for col, values in (("priority", PRIORITIES), ("status", ["Draft", "Reviewed", "Approved", "Rejected"]),
                        ("category", REQ_CATEGORIES), ("confidence", ["High", "Medium", "Low"])):
        letter = get_column_letter(cols.index(col) + 1)
        dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{letter}2:{letter}{last}")

    # live summary (formulas so it updates as reviewers edit)
    sm = wb.create_sheet("Summary", 0)
    meta = doc.get("meta", {})
    sm.append([f"{meta.get('app_name', '')}: Migration Requirements ({meta.get('status', 'AI DRAFT')})"])
    sm["A1"].font = Font(bold=True, size=14)
    sm.append([f"Date: {meta.get('date', '')}   Target context: {meta.get('target_context', '')}"])
    sm.append([])
    sm.append(["Category"] + PRIORITIES + ["Total"])
    for c in sm[4]:
        c.fill, c.font = HEADER_FILL, HEADER_FONT
    cat_col = get_column_letter(cols.index("category") + 1)
    pri_col = get_column_letter(cols.index("priority") + 1)
    for r, cat in enumerate(REQ_CATEGORIES, start=5):
        sm.cell(r, 1, cat)
        for j, p in enumerate(PRIORITIES, start=2):
            sm.cell(r, j, f'=COUNTIFS(Requirements!${cat_col}:${cat_col},$A{r},'
                          f'Requirements!${pri_col}:${pri_col},"{p}")')
        sm.cell(r, len(PRIORITIES) + 2, f"=SUM(B{r}:{get_column_letter(len(PRIORITIES) + 1)}{r})")
    tr = 5 + len(REQ_CATEGORIES)
    sm.cell(tr, 1, "Total").font = Font(bold=True)
    for j in range(2, len(PRIORITIES) + 3):
        L = get_column_letter(j)
        sm.cell(tr, j, f"=SUM({L}5:{L}{tr - 1})").font = Font(bold=True)
    sm.column_dimensions["A"].width = 26
    for key, title, c in REQ_SECTIONS[1:]:
        add_table_sheet(wb, title, c, doc.get(key) or [])
    wb.save(path)

# --------------------------------------------------------------------------- word


def docx_table(d, columns, rows):
    t = d.add_table(rows=1, cols=len(columns))
    t.style = "Light Grid Accent 1"
    for i, c in enumerate(columns):
        t.rows[0].cells[i].text = title_case(c)
    for r in rows:
        cells = t.add_row().cells
        for i, c in enumerate(columns):
            cells[i].text = s(r.get(c))
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8)


def functional_docx(doc, path):
    d = Document()
    meta = doc.get("meta", {})
    d.add_heading(f"{meta.get('app_name', 'Application')}: Functional Document", 0)
    d.add_paragraph(f"Status: {meta.get('status', 'AI DRAFT')} – requires SME review | Date: {meta.get('date', '')} | "
                    f"Repo: {meta.get('repo', '')} {meta.get('commit', '')}")
    d.add_paragraph(f"Coverage: {meta.get('coverage', '')}")

    d.add_heading("1. Overview", 1)
    ov = doc.get("overview", {})
    t = d.add_table(rows=0, cols=2)
    t.style = "Light Grid Accent 1"
    for k in OVERVIEW_FIELDS:
        cells = t.add_row().cells
        cells[0].text, cells[1].text = title_case(k), s(ov.get(k))

    n = 2
    for key, title, cols in FUNCTIONAL_SECTIONS:
        if key == "sources":
            continue
        d.add_heading(f"{n}. {title}", 1)
        n += 1
        items = doc.get(key) or []
        if not items:
            d.add_paragraph("None identified in the sources.")
            continue
        if key == "process_flows":
            for f in items:
                d.add_heading(f"{s(f.get('id'))} {s(f.get('name'))}", 2)
                if f.get("description"):
                    d.add_paragraph(s(f.get("description")))
                for st in f.get("steps") or []:
                    d.add_paragraph(f"{s(st.get('actor'))}: {s(st.get('action'))} [{s(st.get('system'))}]"
                                    + (f" ({s(st.get('refs'))})" if st.get("refs") else ""),
                                    style="List Number")
                d.add_paragraph(f"Source: {s(f.get('source'))} | Confidence: {s(f.get('confidence'))}")
                if f.get("mermaid"):
                    p = d.add_paragraph()
                    run = p.add_run(s(f.get("mermaid")))
                    run.font.name, run.font.size = "Consolas", Pt(8)
        else:
            docx_table(d, cols, items)

    d.add_heading("Source Register", 1)
    docx_table(d, FUNCTIONAL_SECTIONS[0][2], doc.get("sources") or [])
    d.save(path)

# --------------------------------------------------------------------------- main


def slug(name):
    return re.sub(r"[^A-Za-z0-9]+", "-", name or "app").strip("-").lower() or "app"


def load_all(paths):
    docs = []
    for p in paths:
        docs += extract_json(Path(p).read_text(encoding="utf-8-sig"), p)
    return merge(docs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="JSON or Markdown files (split runs are merged)")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--functional-doc", help="functional-doc.json, to check requirement traceability")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--force", action="store_true", help="write files even if there are validation errors")
    a = ap.parse_args()

    try:
        doc = load_all(a.inputs)
        ref = load_all([a.functional_doc]) if a.functional_doc else None
    except (ValueError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    dt = doc.get("doc_type")
    if dt not in ("functional_doc", "migration_requirements"):
        print(f"ERROR: unknown doc_type '{dt}'", file=sys.stderr)
        return 1

    errors, warnings = validate(doc, ref)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"{dt}: {len(errors)} error(s), {len(warnings)} warning(s)")
    if a.check:
        return 1 if errors else 0
    if errors and not a.force:
        print("Nothing written. Fix the errors (ask the agent to correct its JSON) or rerun with --force.")
        return 1

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    app = slug(doc.get("meta", {}).get("app_name"))
    if dt == "functional_doc":
        x, w = out / f"{app}-functional-doc.xlsx", out / f"{app}-functional-doc.docx"
        functional_xlsx(doc, x)
        functional_docx(doc, w)
        print(f"wrote {x}\nwrote {w}")
    else:
        x = out / f"{app}-migration-requirements.xlsx"
        requirements_xlsx(doc, x)
        print(f"wrote {x}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
