# Deed data extraction assistant (دستیار استخراج داده‌ی سند)

A demo for the Registration Organization: a reviewer sends a scanned booklet deed (سند دفترچه‌ای), gets its data as
a form to correct and confirm, and downloads it as JSON for the single-page deed (سند تک‌برگ). It is the third card on
the assistants page, next to the school and the fabric wholesaler.

## Run the demo

Once per machine, the OCR tools (Ubuntu/Debian; on a Mac: `brew install tesseract tesseract-lang poppler`):

```
sudo apt install tesseract-ocr tesseract-ocr-fas poppler-utils
```

Then, as for the rest of the project:

```
HUB=1 uvicorn app:app --reload     # HUB=1 shows the assistants page locally; open the «دستیار استخراج داده‌ی سند» card
```

On the card: send a JPG/PNG/PDF scan, paste a deed's text, or open one of the three samples:

| Sample | File | What it shows |
|---|---|---|
| سند تمیز، یک مالک | `deed/samples/clean.png` | one page, every field read with high confidence |
| چند مالک با سهم | `deed/samples/shared.pdf` | two pages, three owners (3 + 1.5 + 1.5 dang), two transfers, an area that differs between the pages (180 / 186) |
| اسکن نامرغوب | `deed/samples/unclear.png` | turned 90°, blurred; the deed number is smudged (flagged as unreadable), no issue date or book/page (left empty) |

All names, numbers and plates are made up (the national IDs only pass the checksum). `python -m deed.make_samples`
draws them again (it needs Pillow with libraqm, so the files are committed instead of drawn on the server).

Settings: `DEED_DB_PATH` (default `deed.db`), `DEED_DIR` (default `deed_files/`, the uploads and page images).
Tests: `pytest tests/test_deed.py` (the OCR tests skip without Tesseract).

On the live server, once: the `apt install` above, and in the nginx site `client_max_body_size 15m;` (a 10 MB scan
is sent as base64, about 13.4 MB; nginx refuses more than 1 MB by default).

## How it works

1. **Upload.** JPG, PNG or PDF (checked by the file's first bytes, not its name), at most 10 MB and 10 pages; or
   pasted text. Anything else is refused with a message.
2. **OCR, page by page, on the server** (`deed/ocr.py`): Tesseract's orientation check turns the page upright, the
   Persian model reads it with a confidence per word. A page with too little Persian text or a mean confidence under
   55 is "not readable" and gets a message instead of being extracted. Results are cached by the page image's hash, so
   extracting again never reads a page twice. One page at a time, one thread each (in parallel they slowed 30-fold).
3. **Extraction, page by page** (`deed/extract.py`), into a fixed schema (`deed/fields.py`, `PageData`):
   - **rules**: code that knows a deed's fixed wording. Used when the card's AI switch is off, which is the live
     site's default, so nothing leaves the server.
   - **model**: through the project's `llm.py`, with a 90-second timeout. The answer is validated against the
     schema, asked once more if it does not fit, then reported as an error. If the model does not answer at all, the
     deed is read by rules and the review says so.
4. **Every value is looked for in the page's own text.** A value that is not there is dropped (null): the model may
   not guess. One that is there gets that line as its source, and a confidence from the OCR's confidence on that line
   (high from 85, medium from 65). A label present with an unreadable value («شماره سند: .») is flagged, not filled.
5. **Checks by code**: digits and letters normalized (۰-۹ and ٠-٩ to 0-9, ي to ی, ك to ک), Jalali dates real and not
   in the future (leap years included), national ID check digit, shares added up to 6 dang, values that differ
   between pages kept side by side.
6. **Review** (`frontend/src/deed/`): the scan on one side, the form on the other; unsure fields coloured, each with
   its source line and its problems; the other page's value one click away. Save, confirm, then download the JSON.

## Known limitations

- **Handwriting.** Tesseract reads printed and typed Persian well, handwriting badly. Many old booklet deeds are
  partly handwritten; those fields will mostly come back empty or unsure. The samples are typed.
- **The rules know one wording.** They follow the common phrases of a deed («پلاک ... فرعی از ... اصلی», «به مساحت»,
  «شمالاً ...», «فرزند ... به شماره ملی ...»). A deed worded differently loses those fields (they stay empty, never
  wrong). The model reads free wording better, but on the live server it is AvalAI, an outside service; only with a
  local model (Ollama) does the model path stay on the machine.
- **Confidence is about reading, not truth.** "High" means the value is clearly on the page and OCR was sure of that
  line; it does not mean the deed itself is right.
- **Matching a value to its line is by words.** A value split over two lines in an odd way, or with OCR errors, may
  get no source and be dropped as "not in the text"; the reviewer then types it.
- **Tables and stamps.** Values inside tables, stamps or margins are not read reliably; deeds with a table of owners
  may need typing in.
- **Speed.** About 1-2 seconds a page for OCR on a small server, pages in turn, one deed after another in order.
- **No history of edits.** The last saved form is kept; who changed what is not recorded (out of scope: no new auth).
- **The live site forgets every deed on each new visit**, like the other assistants (`RESET_ON_LOAD`).
