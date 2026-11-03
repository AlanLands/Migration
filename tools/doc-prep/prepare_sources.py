#!/usr/bin/env python3
"""Turn a folder of Confluence exports into plain text an LLM can read, including what's inside images.

    python tools/doc-prep/prepare_sources.py docs/confluence
    python tools/doc-prep/prepare_sources.py docs/confluence --out docs/confluence/_extracted --ocr none

Reads (recursively, skipping _extracted/):
  .md .txt            copied as-is
  .html .htm          Confluence HTML export -> Markdown-ish text; local <img> files are OCR'd
  .docx               Confluence "Export to Word" -> text + tables; embedded images are OCR'd
  .pdf                text per page; embedded images are OCR'd
  .png .jpg .jpeg .gif .bmp .tif .tiff   OCR'd
  .xlsx               each sheet as a table (first 500 rows)
  .drawio (or .xml with mxGraphModel)    parsed exactly: nodes, edges, edge labels
  <name>.image.md     a person's description of an image: copied and linked to that image

Writes to --out (default <input>/_extracted):
  NN-<name>.md                  one text file per document
  NN-<name>.img-K.image.md      one note per image (OCR text laid out by rows + caution)
  NN-<name>.drawio.md           exact diagram structure
  index.md / manifest.json      what was processed, status, OCR engine, warnings

Secrets: values after password=, pwd=, secret=, token=, apikey= etc. are replaced with [REDACTED].
OCR engines tried in order: winocr (Windows 10/11 built-in, no admin) -> rapidocr -> pytesseract.
OCR reads TEXT only. It does not see arrows or connections, so every image note says so.
"""
import argparse
import base64
import io
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from datetime import datetime
from pathlib import Path

IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
MIN_IMG_PX = 80          # skip icons/bullets
MAX_IMG_BYTES = 20_000_000
SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|client_secret|token|api[_-]?key|access[_-]?key)\b(\s*[:=]\s*)([^\s,;\"'<>]{3,})")
CONN_RE = re.compile(r"(?i)(\b\w+://[^:\s/]+:)([^@\s]+)(@)")  # scheme://user:pass@host

# --------------------------------------------------------------------------- helpers


def redact(text, stats):
    def r1(m):
        stats["redactions"] += 1
        return f"{m.group(1)}{m.group(2)}[REDACTED]"

    def r2(m):
        stats["redactions"] += 1
        return f"{m.group(1)}[REDACTED]{m.group(3)}"
    return CONN_RE.sub(r2, SECRET_RE.sub(r1, text))


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:60] or "doc"


def md_table(rows):
    rows = [[c.replace("\n", " ").replace("|", "/").strip() for c in r] for r in rows if any(c.strip() for c in r)]
    if not rows:
        return ""
    w = max(len(r) for r in rows)
    rows = [r + [""] * (w - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)

# --------------------------------------------------------------------------- OCR


class OCR:
    def __init__(self, choice):
        self.name, self._fn = "none", None
        if choice == "none":
            return
        order = [choice] if choice != "auto" else ["winocr", "rapidocr", "tesseract"]
        for eng in order:
            try:
                getattr(self, f"_init_{eng}")()
                self.name = eng
                return
            except Exception:  # engine not installed / not loadable on this machine
                continue

    def _init_winocr(self):
        import winocr
        from PIL import Image
        winocr.recognize_pil_sync(Image.new("RGB", (40, 20), "white"), "en")  # load test

        def run(img):
            r = winocr.recognize_pil_sync(img, "en")
            out = []
            for ln in r.get("lines", []):
                ws = ln.get("words") or []
                x = min((w["bounding_rect"]["x"] for w in ws), default=0)
                y = min((w["bounding_rect"]["y"] for w in ws), default=0)
                h = max((w["bounding_rect"]["height"] for w in ws), default=10)
                out.append((x, y, h, ln.get("text", "")))
            return out
        self._fn = run

    def _init_rapidocr(self):
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np
        eng = RapidOCR()

        def run(img):
            res, _ = eng(np.array(img))
            return [(min(p[0] for p in box), min(p[1] for p in box),
                     max(p[1] for p in box) - min(p[1] for p in box), txt) for box, txt, _ in (res or [])]
        self._fn = run

    def _init_tesseract(self):
        import pytesseract
        pytesseract.get_tesseract_version()

        def run(img):
            d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            lines = {}
            for i, t in enumerate(d["text"]):
                if t.strip():
                    k = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
                    x, y, h = d["left"][i], d["top"][i], d["height"][i]
                    if k in lines:
                        lx, ly, lh, lt = lines[k]
                        lines[k] = (min(lx, x), min(ly, y), max(lh, h), lt + " " + t)
                    else:
                        lines[k] = (x, y, h, t)
            return list(lines.values())
        self._fn = run

    def read(self, data):
        """bytes -> (rows_text, size) or raises. rows_text is None if image is too small."""
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
        img = img.convert("RGB")
        size = img.size
        if min(size) < MIN_IMG_PX:
            return None, size
        if not self._fn:
            return "", size
        scale = 2 if size[0] < 1200 else 1
        if scale > 1:
            img = img.resize((size[0] * scale, size[1] * scale))
        lines = self._fn(img)
        if not lines:
            return "", size
        # group into visual rows so layout (left -> right, top -> bottom) survives
        lines.sort(key=lambda l: (l[1], l[0]))
        rows, cur, cur_y, cur_h = [], [], None, 0
        for x, y, h, t in lines:
            if cur and abs(y - cur_y) > max(cur_h, h) * 0.6:
                rows.append(cur)
                cur = []
            if not cur:
                cur_y, cur_h = y, h
            cur.append((x, t))
        if cur:
            rows.append(cur)
        text = "\n".join(f"row {i}: " + "  |  ".join(t for _, t in sorted(r)) for i, r in enumerate(rows, 1))
        return text, size

# --------------------------------------------------------------------------- extractors


class Ctx:
    def __init__(self, out, ocr, stats):
        self.out, self.ocr, self.stats = out, ocr, stats
        self.manifest = []

    def image_note(self, prefix, k, data, origin, human_note=None):
        """OCR one image, write NN-name.img-K.image.md, return the marker to put in the text."""
        fname = f"{prefix}.img-{k}.image.md"
        if len(data) > MAX_IMG_BYTES:
            self.manifest.append({"file": fname, "origin": origin, "status": "skipped: too large"})
            return f"[IMAGE {k}: skipped, too large]"
        try:
            text, size = self.ocr.read(data)
        except Exception as e:
            self.manifest.append({"file": fname, "origin": origin, "status": f"error: {e}"})
            return f"[IMAGE {k}: could not be read ({e.__class__.__name__}) - needs a human description]"
        if text is None:
            return ""  # icon
        status = "ocr" if text else ("ocr-empty" if self.ocr.name != "none" else "no-ocr")
        body = [f"# IMAGE NOTE: {origin}",
                f"SOURCE TYPE: image | SIZE: {size[0]}x{size[1]} | OCR ENGINE: {self.ocr.name} | STATUS: {status}",
                "",
                "CAUTION FOR THE AGENT: the text below was read by OCR. OCR reads words only. It does NOT see arrows,",
                "lines, colours or which box connects to which. Use the row layout only as a hint (left -> right,",
                "top -> bottom). Treat any flow or connection you infer from it as confidence Low and raise an open",
                "question asking a person to confirm the flow shown in this image.",
                ""]
        if human_note:
            body += ["## Human description (takes priority over OCR)", human_note.strip(), ""]
        body += ["## OCR text by visual row", text or "(no text found - the image may be a photo, screenshot of a "
                 "chart or too low resolution; needs a human description)"]
        (self.out / fname).write_text(redact("\n".join(body), self.stats) + "\n", encoding="utf-8")
        self.manifest.append({"file": fname, "origin": origin, "status": status})
        self.stats["images"] += 1
        return f"[IMAGE {k}: see {fname}]"


def read_html(path, ctx, prefix):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    title = soup.title.get_text(strip=True) if soup.title else path.stem
    k = 0
    for img in soup.find_all("img"):
        src = urllib.parse.unquote(img.get("src", ""))
        f = (path.parent / src) if src and not re.match(r"^[a-z]+:", src) else None
        if f and f.is_file() and f.suffix.lower() in IMG_EXT:
            k += 1
            note = human_note_for(f)
            img.replace_with(f"\n{ctx.image_note(prefix, k, f.read_bytes(), f'{path.name} > {src}', note)}\n")
        else:
            img.replace_with(f"[IMAGE: {img.get('alt') or src or 'unknown'} - not available locally]")
    for tbl in soup.find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in tbl.find_all("tr")]
        tbl.replace_with("\n" + md_table(rows) + "\n")
    for lvl in range(1, 7):
        for h in soup.find_all(f"h{lvl}"):
            h.replace_with(f"\n{'#' * lvl} {h.get_text(' ', strip=True)}\n")
    for li in soup.find_all("li"):
        li.insert(0, "- ")
    text = soup.get_text("\n")
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return title, text


def read_docx(path, ctx, prefix):
    import docx
    from docx.oxml.ns import qn
    d = docx.Document(str(path))
    rels = d.part.rels
    out, k = [], 0
    body = d.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            p = docx.text.paragraph.Paragraph(child, d)
            style = (p.style.name or "").lower() if p.style is not None else ""
            line = p.text.strip()
            if style.startswith("heading") and line:
                lvl = re.sub(r"\D", "", style) or "2"
                line = "#" * min(int(lvl), 6) + " " + line
            elif "list" in style and line:
                line = "- " + line
            for blip in child.iter(qn("a:blip")):
                rid = blip.get(qn("r:embed"))
                if rid in rels and "image" in rels[rid].reltype:
                    k += 1
                    part = rels[rid].target_part
                    marker = ctx.image_note(prefix, k, part.blob, f"{path.name} > {Path(part.partname).name}")
                    line = (line + "\n" + marker).strip()
            if line:
                out.append(line)
        elif child.tag == qn("w:tbl"):
            t = docx.table.Table(child, d)
            rows = []
            for r in t.rows:
                try:
                    rows.append([c.text for c in r.cells])
                except Exception:
                    continue
            out.append(md_table(rows))
    title = d.core_properties.title or path.stem
    return title, "\n\n".join(out)


def read_pdf(path, ctx, prefix):
    from pypdf import PdfReader
    r = PdfReader(str(path))
    out, k = [], 0
    for n, page in enumerate(r.pages, 1):
        out.append(f"\n## Page {n}\n")
        out.append(page.extract_text() or "")
        try:
            imgs = list(page.images)
        except Exception:
            imgs = []
        for im in imgs:
            k += 1
            m = ctx.image_note(prefix, k, im.data, f"{path.name} > page {n} > {im.name}")
            if m:
                out.append(m)
            else:
                k -= 1
    title = (r.metadata.title if r.metadata and r.metadata.title else path.stem)
    return title, "\n".join(out)


def read_xlsx(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        rows = []
        for i, r in enumerate(ws.iter_rows(values_only=True)):
            if i >= 500:
                rows.append(["(truncated at 500 rows)"])
                break
            rows.append(["" if v is None else str(v) for v in r])
        out.append(f"## Sheet: {ws.title}\n\n" + (md_table(rows) or "(empty)"))
    return "\n\n".join(out)


def strip_html(s):
    s = re.sub(r"<br\s*/?>", " ", s or "", flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def drawio_models(path):
    root = ET.parse(path).getroot()
    if root.tag == "mxGraphModel":
        yield path.stem, root
        return
    for i, dg in enumerate(root.iter("diagram"), 1):
        name = dg.get("name") or f"page {i}"
        model = dg.find("mxGraphModel")
        if model is None and (dg.text or "").strip():
            raw = zlib.decompress(base64.b64decode(dg.text.strip()), -15)
            model = ET.fromstring(urllib.parse.unquote(raw.decode("utf-8")))
        if model is not None:
            yield name, model


def read_drawio(path):
    out = []
    for name, model in drawio_models(path):
        cells = {c.get("id"): c for c in model.iter("mxCell")}
        label = {i: strip_html(c.get("value")) or f"(unlabelled {i})" for i, c in cells.items()}
        for obj in model.iter("object"):          # labels can sit on a wrapping <object>
            cid = obj.get("id")
            if cid:
                label[cid] = strip_html(obj.get("label")) or label.get(cid, cid)
        nodes = [label[i] for i, c in cells.items() if c.get("vertex") == "1" and strip_html(c.get("value"))]
        edges = []
        for i, c in cells.items():
            if c.get("edge") == "1":
                elabel = strip_html(c.get("value"))
                for j, cc in cells.items():          # edge labels are often child cells
                    if cc.get("parent") == i and strip_html(cc.get("value")):
                        elabel = (elabel + " " + strip_html(cc.get("value"))).strip()
                edges.append((label.get(c.get("source"), "?"), label.get(c.get("target"), "?"), elabel))
        out.append(f"## Diagram: {name}\n\n### Shapes\n" + "\n".join(f"- {n}" for n in nodes))
        out.append("### Connections (exact, from the diagram file)\n" + md_table(
            [["From", "To", "Label"]] + [list(e) for e in edges]) if edges else "### Connections\n(none)")
    return "\n\n".join(out)


def human_note_for(img_path):
    p = img_path.with_name(img_path.stem + ".image.md")
    return p.read_text(encoding="utf-8") if p.exists() else None

# --------------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="folder (or single file) with Confluence exports")
    ap.add_argument("--out", help="output folder (default <input>/_extracted)")
    ap.add_argument("--ocr", default="auto", choices=["auto", "winocr", "rapidocr", "tesseract", "none"])
    a = ap.parse_args()

    src = Path(a.input).resolve()
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 1
    base = src if src.is_dir() else src.parent
    out = Path(a.out).resolve() if a.out else base / "_extracted"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*"):
        if old.is_file():
            old.unlink()

    stats = {"redactions": 0, "images": 0}
    ocr = OCR(a.ocr)
    ctx = Ctx(out, ocr, stats)
    files = [src] if src.is_file() else sorted(
        p for p in src.rglob("*") if p.is_file() and "_extracted" not in p.relative_to(src).parts)
    # images that belong to an HTML export are handled with their page
    html_dirs = {p.parent for p in files if p.suffix.lower() in (".html", ".htm")}

    n = 0
    for f in files:
        ext, rel = f.suffix.lower(), f.relative_to(base).as_posix()
        if f.name.endswith(".image.md"):
            continue  # attached to its image below
        if ext in IMG_EXT and any(d in f.parents for d in html_dirs):
            continue
        n += 1
        prefix = f"{n:02d}-{slug(f.stem)}"
        modified = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
        entry = {"file": f"{prefix}.md", "origin": rel, "status": "ok"}
        try:
            if ext in (".md", ".txt"):
                title, text = f.stem, f.read_text(encoding="utf-8", errors="replace")
            elif ext in (".html", ".htm"):
                title, text = read_html(f, ctx, prefix)
            elif ext == ".docx":
                title, text = read_docx(f, ctx, prefix)
            elif ext == ".pdf":
                title, text = read_pdf(f, ctx, prefix)
            elif ext == ".xlsx":
                title, text = f.stem, read_xlsx(f)
            elif ext in IMG_EXT:
                if not ctx.image_note(prefix, 1, f.read_bytes(), rel, human_note_for(f)):  # "" = icon
                    ctx.manifest.append({"file": "", "origin": rel, "status": "icon/too small - skipped"})
                continue
            elif ext == ".drawio" or (ext == ".xml" and re.search(rb"<mxfile|<mxGraphModel", f.read_bytes()[:4000])):
                title, text = f.stem, read_drawio(f)
                entry["file"] = f"{prefix}.drawio.md"
                text = ("SOURCE TYPE: diagram (draw.io) - structure parsed exactly from the file, "
                        "so connections are reliable.\n\n" + text)
            else:
                entry["status"], entry["file"] = "unsupported type - not read", ""
                ctx.manifest.append(entry)
                continue
            header = f"# SOURCE: {title}\nORIGINAL FILE: {rel} | FILE MODIFIED: {modified}\n\n"
            (out / entry["file"]).write_text(redact(header + text.strip(), stats) + "\n", encoding="utf-8")
        except Exception as e:
            entry["status"], entry["file"] = f"error: {e.__class__.__name__}: {e}", ""
        ctx.manifest.append(entry)

    # orphan human notes (no matching image file)
    for note in (p for p in files if p.name.endswith(".image.md")):
        if not any(note.with_name(note.name[:-9] + e).exists() for e in IMG_EXT):
            n += 1
            fn = f"{n:02d}-{slug(note.name[:-9])}.image.md"
            (out / fn).write_text(redact("# IMAGE NOTE (human description)\n\n" + note.read_text(encoding="utf-8"),
                                         stats), encoding="utf-8")
            ctx.manifest.append({"file": fn, "origin": note.relative_to(base).as_posix(), "status": "human note"})

    problems = [m for m in ctx.manifest if m["status"] not in ("ok", "ocr", "human note")]
    lines = ["# Extracted sources", "",
             f"Input: {src} | OCR engine: {ocr.name} | Images read: {stats['images']} | "
             f"Secrets redacted: {stats['redactions']}", "",
             md_table([["Extracted file", "Original", "Status"]] +
                      [[m["file"] or "-", m["origin"], m["status"]] for m in ctx.manifest])]
    if ocr.name == "none":
        lines += ["", "WARNING: no OCR engine available - image text was not read. Images need human "
                  "descriptions (<image-name>.image.md next to the image). See tools/doc-prep/README.md."]
    if problems:
        lines += ["", "Items needing attention: " + ", ".join(m["origin"] for m in problems)]
    (out / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"ocr_engine": ocr.name, **stats, "items": ctx.manifest},
                                                  indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
