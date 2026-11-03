# doc-prep: Confluence exports → text the AI can read (including images)

GitLab Duo reads text files well but can't read `.docx`/`.pdf` reliably or see images. `prepare_sources.py` converts a folder of Confluence exports into plain Markdown, and reads the text inside images with OCR. The `/functional-doc` skill runs it automatically (Stage 2).

```powershell
python tools/doc-prep/prepare_sources.py docs/confluence            # writes docs/confluence/_extracted/
python tools/doc-prep/prepare_sources.py docs/confluence --ocr none # skip OCR
```

## What it handles

| Input | Result | Reliability |
|---|---|---|
| `.docx` (Confluence → Export → Word) | Headings, paragraphs, tables; embedded images → OCR notes | High |
| `.pdf` | Text per page; embedded images → OCR notes | Medium (layout can scramble) |
| `.html` (Confluence → Export → HTML, keep the `attachments/` folder) | Headings, tables; local images → OCR notes | High |
| `.xlsx` | Each sheet as a table (first 500 rows) | High |
| `.png .jpg .gif .bmp .tif` | OCR text, grouped into visual rows | Text: Medium. Arrows/flow: **not detected** |
| `.drawio` (draw.io diagram file) | Exact shapes, connections and labels | **Exact**, the best option for diagrams |
| `<image-name>.image.md` | A person's description of `<image-name>.png`, which takes priority over OCR | As good as the description |
| `.md .txt` | Copied | High |

**Secrets** (`password=`, `token:`, `user:pass@host` …) are replaced with `[REDACTED]` before Duo ever sees them. The count is in `index.md`.

## Images: how to get the best result

1. **draw.io / Gliffy diagrams:** in Confluence, open the diagram → **Export → XML** (draw.io) and save it as `<name>.drawio`. This gives exact connections, much better than OCR.
2. **Screenshots and pictures of architecture:** OCR reads the labels but **not the arrows**. For the 2–3 diagrams that matter most, add a short `<image-name>.image.md` next to the image:
   ```text
   Broker Portal -> Claims API (REST)
   Claims API -> Oracle CLAIMS DB
   Nightly 02:00: batch -> FinanceSys (SFTP file)
   ```
3. Everything inferred from OCR alone is marked **Low confidence** and gets an open question, so the SME confirms it.

## OCR engines

| Engine | Install | Notes |
|---|---|---|
| `winocr` (default on Windows) | `pip install winocr` | Uses the OCR engine built into Windows 10/11. **No admin rights.** English by default. |
| `rapidocr` | `pip install rapidocr-onnxruntime` | Linux/macOS/CI. On Windows it needs the Visual C++ runtime (admin to install). |
| `tesseract` | `pip install pytesseract` + the Tesseract program | Only if already installed |

The script picks the first one that works. With none, it still runs and lists every image as needing a human description.

Why not plain OpenCV? OpenCV handles image processing (resize, threshold) but doesn't read text. The OCR engines above do the reading (RapidOCR uses OpenCV internally).

## Output (`_extracted/`)
- `NN-<doc>.md`: document text, with `[IMAGE k: see …]` markers where images were
- `NN-<doc>.img-k.image.md`: OCR text of each image + a caution for the agent
- `NN-<diagram>.drawio.md`: shapes and connections
- `index.md` / `manifest.json`: what was processed, the OCR engine, redactions, and items needing attention

`_extracted/` is regenerated on every run, so don't edit it. Put corrections in `.image.md` files next to the originals.
