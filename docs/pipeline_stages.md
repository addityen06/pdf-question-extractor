# Pipeline Stages

Detailed description of every stage in the extraction pipeline.

---

## Stage 1 — PDF Classification

**Module:** `src/questionai/pdf/pdf_classifier.py`

Classifies each page individually as one of three types:

- `NATIVE` — the page contains selectable text characters above the configured threshold
- `SCANNED` — the page is primarily or entirely a rasterised image with no selectable text
- `HYBRID` — the page has some native text but image regions occupy more than half the area

The overall PDF type is determined by majority vote across pages.

**Key parameters:**
- `extraction.native_text_threshold` (default 50): minimum character count for a page to be classified as NATIVE
- `extraction.image_area_threshold` (default 0.5): image-to-page area ratio above which a page is considered scanned

---

## Stage 2 — Text Extraction

**Modules:** `src/questionai/pdf/text_extractor.py`, `src/questionai/ocr/`

### Native text extraction

Uses PyMuPDF (`fitz`) to extract text blocks from each page. Each block is converted to an `ElementBlock` with bounding box coordinates, font name, font size, bold and italic flags, and confidence of 1.0.

### OCR extraction

Uses Apple Vision (`pyobjc-framework-Vision`) on macOS. The page is first rendered to a Pillow image at the configured DPI (default 300). The image is optionally converted to grayscale and deskewed before being passed to the Vision framework's `VNRecognizeTextRequest`. Each recognised word is returned with its bounding box in normalised coordinates and a confidence score. The postprocessor filters out low-confidence words (below `ocr.min_confidence`) and normalises bounding boxes to PDF point coordinates.

### Hybrid merge

For HYBRID pages, native and OCR elements are merged. OCR elements are added only if their bounding box does not have a vertical overlap ratio above 50% with any native element. The merged list is sorted by position.

---

## Stage 3 — Layout Analysis

**Modules:** `src/questionai/layout/layout_analyzer.py`, `src/questionai/layout/reading_order.py`

Groups raw `ElementBlock` objects into `LineBlock` objects by y-coordinate proximity (configurable `line_merge_y_tolerance`), and then groups lines into `ParagraphBlock` objects by vertical gap analysis (gap above `paragraph_gap_multiplier` times the average line height triggers a new paragraph).

Multi-column detection uses a minimum horizontal gap threshold (`column_detection_min_gap`). Elements in distinct columns are assigned different `column` indices and processed in left-to-right, top-to-bottom reading order.

---

## Stage 4 — Administrative Content Removal

**Module:** `src/questionai/layout/header_footer_detector.py`

Scans paragraphs for administrative content using two strategies:

1. **Keyword matching** against a comprehensive list of institutional phrases (institution name, exam metadata labels, instruction phrases, registration fields, etc.)
2. **Pattern matching** for bare page numbers, VIT class numbers, and page separator lines

Paragraphs in the top 25% of the page height (configurable) are checked as potential headers. Paragraphs in the bottom 8% are checked as potential footers. Administrative content is removed from body text. The header scan also extracts the stated maximum marks using regex patterns.

---

## Stage 5 — Question Detection

**Module:** `src/questionai/content/question_detector.py`

This is the most critical stage. See the [README](../README.md#question-detection) for the full signal table.

The detector runs in four phases:

1. **Scoring** — every paragraph is scored against five signals
2. **Validation** — sequential numbering is validated; duplicates are resolved by keeping the higher-scoring candidate
3. **Content boundary assignment** — each candidate owns all paragraphs from its boundary to the next candidate
4. **OR-choice detection** — scans paragraphs between adjacent candidates for standalone "OR" lines and assigns a shared `choice_group` ID

Subquestion candidates (`(a)`, `a)`, `(i)`) are detected independently using a separate pattern set and associated with the nearest preceding main question.

If zero candidates are produced by the multi-signal pass, the detector falls back to regex-only detection.

---

## Stage 6 — Specialised Content Detection

**Modules:** `src/questionai/content/equation_detector.py`, `content/code_detector.py`, `content/table_detector.py`, `content/figure_detector.py`

Runs over the body paragraphs and produces `ContentBlock` objects for detected specialised content:

- **Equations:** presence of math symbols from a comprehensive Unicode set, or math-specific keywords, or inline LaTeX-like notation
- **Code blocks:** keyword matching against C, C++, Java, Python, and SQL keyword lists; monospace font detection by name fragments; syntax character density
- **Tables:** horizontal alignment of elements across multiple paragraphs suggesting tabular structure
- **Figures:** embedded image detection with minimum area threshold; extracted figures are saved to the paper's assets directory

---

## Stage 7 — Question Reconstruction

**Modules:** `src/questionai/reconstruction/question_reconstructor.py`, `reconstruction/text_cleaner.py`

Combines each `QuestionCandidate` with its associated `ContentBlock` objects into a `Question` Pydantic model. Generates a globally unique question ID in the format `<course>_<exam>_<year>_<semester>_Q<n>[_<sub>]`. Flattens content blocks to a plain text `question_text` string, serialising equations as `$...$`, code as fenced blocks, tables as Markdown tables, and figures as `[FIGURE: path (caption)]` references.

Text cleaning applies configurable normalisation: duplicate whitespace removal, page number stripping, Unicode normalisation, with optional preservation of code whitespace and math symbols.

---

## Stage 8 — Validation and Confidence

**Modules:** `src/questionai/validation/validator.py`, `validation/confidence.py`

### Validation

Runs six checks (V1-V6) across the full question set for the paper and produces a `ValidationResult` with per-check `ValidationCheck` objects showing PASS, WARNING, or FAIL status.

### Confidence

Per-question confidence is computed as a weighted sum of six signals. The overall paper confidence is the average of all question confidences. Confidence tiers determine verification status.

---

## Stage 9 — Output Serialization

**Modules:** `src/questionai/output/csv_writer.py`, `output/report_generator.py`, `output/jsonl_writer.py`

Writes all output files for the paper:

- `textPapers/<course>/<stem>.csv` — the primary CSV, questions sorted by number then subquestion label
- `textPapersCSV/<course>/<stem>.csv` — clean mirror with identical content
- `<stem>_raw.json` — full Pydantic model dump of all `Question` objects as JSON
- `<stem>_extraction_report.json` — the `ExtractionReport` model serialised to JSON

Every `question_text` value in the CSV is appended with `\n<<<QUESTION_END>>>` before writing.
