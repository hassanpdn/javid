# Deed data extraction assistant: architecture and the reasons behind it

The whole application is described in [../ARCHITECTURE.md](../ARCHITECTURE.md). How to run it, the samples and the
known limitations are in [README.md](README.md). This file explains the design.

## In one minute

For the Registration Organization: old booklet deeds (سند دفترچه‌ای) must become single-page deeds (سند تک‌برگ). A
reviewer types every field from a scan, which is slow and error-prone. The assistant reads the scan, proposes every
field with the line it came from and how sure the reading was, runs the checks a reviewer would, and leaves the final
word to the reviewer, who confirms and downloads JSON.

## The pipeline

```
 upload (image, PDF or text) ─► ocr.py: page images, turn upright, Tesseract Persian, confidence per line
                                  │   (unreadable pages are left out with a message; results cached by page hash)
                                  ▼
                               extract.py: per page, rules or the model → fields.PageData (a fixed schema)
                                  │
                                  ▼
                               every value looked for in the page's own text: not there → null; there → its line
                               and a confidence from the OCR of that line
                                  │
                                  ▼
                               fields.py checks: digits and letters, real Jalali dates, national ID check digit,
                               shares add up to 6 dang, pages that disagree keep both values
                                  │
                                  ▼
                               review screen (scan beside the form) → confirm → JSON
```

| File | What it does |
|---|---|
| `ocr.py` | Everything about reading the scan, on the server only, with Tesseract and poppler. |
| `extract.py` | From text to fields: the rules, the model path, and the check of every value against the page. |
| `fields.py` | The schema and the checks; no model here. |
| `store.py` | `deed.db` and the files: documents, pages, OCR cache. |
| `api.py` | Upload, progress, review, confirm, export. |
| `make_samples.py` | Draws the three made-up sample deeds (committed, not drawn on the server). |

## Why it is built this way

- **OCR on the server, nothing sent out.** Deeds are sensitive. With the AI switch off (the live default), nothing
  leaves the machine.
- **A fixed schema** (`PageData`) for rules and model alike, so the review screen and the checks never care who read
  the page.
- **The model may not guess.** Its answer is validated against the schema (asked once more, then reported), and any
  value not found in the page's text is dropped. A label with an unreadable value is flagged, not filled.
- **Confidence comes from the OCR**, not from the model's opinion of itself.
- **Pages that disagree keep both values**, because choosing one is the reviewer's decision.
- **A reviewer confirms everything.** The output is a proposal until a person confirms it.

## Questions you will be asked

- *"What about handwriting?"* Tesseract reads typed Persian well and handwriting badly; those fields come back empty
  or unsure, never invented (README, Known limitations).
- *"Is 'high confidence' a guarantee?"* It means the value is clearly on the page; it says nothing about whether the
  deed itself is right.

## How to change common things

| Change | Where | Test |
|---|---|---|
| A new deed wording | the rules in `extract.py` | `test_rules_read_a_clean_deed` |
| A new field or check | `fields.py` | `test_shares_must_add_up_to_six_dang`, `test_national_id_check_digit` |
| OCR quality limits | `ocr.py` | `test_unreadable_page_is_left_out_with_a_message` |

## Tests

`tests/test_deed.py` (18), from digit cleaning to the model being refused when it invents an owner, a broken JSON
answer asked again, the model down falling back to rules, wrong or big files refused, review, confirm and export.
