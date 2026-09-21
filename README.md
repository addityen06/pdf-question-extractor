# pdf-question-extractor

A deterministic, local-first PDF parsing and question extraction pipeline for structured examination papers. Converts institutional exam PDFs into clean, machine-readable CSV datasets — one CSV per paper, one question per row.

This is Stage A of a larger AI-powered learning tool. It handles all heavy lifting of raw document ingestion: native text extraction, OCR for scanned pages, layout analysis, question boundary detection, content classification, and quality validation — entirely offline.

---

## What It Does

Given a directory of course-organised examination PDFs, the pipeline:

1. Classifies each page as native text, scanned image, or hybrid
2. Extracts text using PyMuPDF for native pages and Apple Vision OCR for scanned pages
3. Analyses layout to determine reading order, columns, and paragraph boundaries
4. Strips administrative boilerplate (headers, footers, instructions, institution metadata)
5. Detects question boundaries using a five-signal scoring system — not just regex
6. Detects specialised content: equations, code blocks, tables, and embedded figures
7. Reconstructs full question objects with marks, subquestion labels, and choice groups
8. Validates the extraction with six automated checks and assigns a confidence tier
9. Writes one CSV per paper to a structured output directory, plus a raw JSON record and a per-paper extraction report

---

## Architecture

```
src/pdfextract/
    core/           Models, config schema, constants, exceptions
    ingestion/      Directory scanner, filename parser, paper registry
    pdf/            PDF loader, page classifier, native text extractor, page renderer
    ocr/            Image preprocessor, Apple Vision OCR engine, OCR postprocessor
    layout/         Layout analyser, reading order sorter, header/footer detector
    content/        Question detector, subquestion detector, equation/code/table/figure detectors
    reconstruction/ Question reconstructor, text cleaner
    validation/     Validator, confidence scorer, consistency checker
    output/         CSV writer, JSONL writer, report generator
```

The top-level `pipeline.py` orchestrates all stages in strict order. Each stage is isolated — failures in one stage (e.g. figure extraction) are caught and logged without aborting the paper.

---

## Question Detection

Question detection is the core challenge. The detector in `content/question_detector.py` uses a multi-signal scoring approach:

| Signal | Weight | Description |
|---|---|---|
| S1 Text pattern | 3 | Regex match on question number formats (`Q1`, `1.`, `Question 1`) |
| S2 Font emphasis | 2 | Bold text or font size above the page median |
| S3 Marks nearby | 2 | Marks indicator in the same paragraph (`[10]`, `(5 marks)`) |
| S4 Vertical gap | 1 | Whitespace above paragraph exceeds 1.5x average line gap |
| S5 Indent shift | 1 | Left-edge x-coordinate shifts left vs. previous paragraph |

A paragraph must reach a configurable threshold (default: 3) to be treated as a question boundary. If no candidates reach the threshold, the detector falls back to regex-only detection. Subquestion labels (`(a)`, `(i)`, `a)`) are detected independently and associated with their parent question. `OR` choice groups are detected between adjacent questions.

---

## Output Format

Each paper produces a CSV at `textPapers/<course_code>/<paper_stem>.csv` with these columns:

| Column | Description |
|---|---|
| `question_number` | Integer question number |
| `subquestion` | Subquestion label (`a`, `b`, `i`, `ii`) or empty |
| `marks` | Marks allocated, or empty if not detected |
| `question_type` | `theory`, `numerical`, `programming` |
| `question_text` | Full question text, terminated by `<<<QUESTION_END>>>` |
| `separator` | The question separator constant |
| `confidence` | Extraction confidence score (0.0 to 1.0) |
| `verification_status` | `auto_extracted`, `review_recommended`, `review_required` |
| `course_code` | Course identifier |
| `paper_file` | Source PDF filename |
| `exam_type` | `CAT-1`, `CAT-2`, `FAT` |
| `academic_year` | e.g. `2024-2025` |
| `semester` | `Fall_Semester`, `Winter_Semester`, `Summer_Semester` |
| `has_equation` | Boolean |
| `has_code` | Boolean |
| `has_table` | Boolean |
| `has_figure` | Boolean |
| `choice_group` | OR-choice group ID or empty |

A clean CSV-only mirror is written to `textPapersCSV/<course_code>/<paper_stem>.csv`. A raw JSON extraction record and a structured JSON report are written alongside the CSV.

---

## Directory Convention

The pipeline expects PDFs organised as:

```
<papers_root>/
    <COURSE_CODE>/
        CAT-1_2024-2025_Fall_Semester_D1_Vellore_85f84318.pdf
        FAT_2024-2025_Winter_Semester_A1_Vellore_AnsKey_a03f5dc7.pdf
    <COURSE_CODE>/
        ...
```

Course directories with descriptive names containing a bracket-wrapped code are also supported:

```
Electric_Vehicle_Instrumentation_and_Data_Analytics_[BAMEE344]/
```

---

## Installation

Requires Python 3.11 or later.

```bash
git clone https://github.com/<your-username>/pdf-question-extractor.git
cd pdf-question-extractor
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For scanned PDF support (Apple Vision OCR, macOS only):

```bash
pip install -e ".[ocr]"
```

For running tests:

```bash
pip install -e ".[test]"
```

---

## Usage

Run extraction on all papers:

```bash
python scripts/run_extraction.py
```

Run on specific courses only:

```bash
python scripts/run_extraction.py --courses BACSE104 BMAT101L
```

Limit to a small batch for testing:

```bash
python scripts/run_extraction.py --limit 10
```

Force re-extraction of already processed papers:

```bash
python scripts/run_extraction.py --force
```

Skip faculty answer key PDFs:

```bash
python scripts/run_extraction.py --skip-answer-keys
```

Use a custom config file:

```bash
python scripts/run_extraction.py --config path/to/my_config.yaml
```

Point to a custom papers directory:

```bash
python scripts/run_extraction.py --papers-dir /path/to/papers
```

---

## Configuration

All tunable parameters live in `config/default.yaml`. The file is fully commented. Key sections:

- `paths` — input and output directory names
- `ocr` — DPI, recognition level, preprocessing toggles
- `extraction` — thresholds for native text detection, column detection, paragraph merging
- `question_detection` — signal threshold, marks search radius, OR-choice detection
- `content_detection` — thresholds for code, equation, table, and figure detection
- `confidence` — weight distribution across confidence signals and tier cutoffs
- `validation` — which checks to run and marks tolerance
- `cleaning` — text normalisation toggles
- `batch` — resume behaviour and answer key filtering

---

## Verification Tiers

Every extracted question receives a verification status derived from its confidence score:

| Tier | Score Range | Status |
|---|---|---|
| High | >= 0.90 | `auto_extracted` |
| Medium | 0.70 - 0.89 | `review_recommended` |
| Low | 0.50 - 0.69 | `review_required` |
| Very low | < 0.50 | `review_required` |

Confidence is computed from six weighted signals: OCR quality, question number detectability, marks detection, boundary detection quality, content completeness, and validation check results.

---

## Validation Checks

The validator (`validation/validator.py`) runs six checks per paper:

| Check | Description |
|---|---|
| V1 Sequential numbering | Verifies question numbers are contiguous |
| V2 Subquestion labels | Validates subquestion label format |
| V3 Marks summation | Compares detected total marks to stated maximum |
| V4 Question text length | Flags suspiciously short questions |
| V5 Admin residual removal | Checks for institution boilerplate inside question text |
| V6 Bracket balance | Detects unmatched parentheses or braces in equations |

---

## Resumability

The pipeline is resumable. If a paper's CSV and report already exist and the report shows `success`, that paper is skipped on subsequent runs. Use `--force` to override.

---

## Requirements

- Python >= 3.11
- PyMuPDF >= 1.24.0
- pypdf >= 4.0.0
- pydantic >= 2.0.0
- PyYAML >= 6.0
- pandas >= 2.0.0
- Pillow >= 10.0.0
- numpy >= 1.24.0
- rich >= 13.0.0
- typer >= 0.9.0
- tqdm >= 4.65.0

Optional (OCR, macOS only):

- pyobjc-framework-Vision >= 10.0
- pyobjc-framework-Quartz >= 10.0

---

## Project Structure

```
pdf-question-extractor/
    src/
        pdfextract/
            __init__.py
            pipeline.py
            core/
                config.py
                constants.py
                exceptions.py
                models.py
            ingestion/
                directory_scanner.py
                filename_parser.py
                paper_registry.py
            pdf/
                page_renderer.py
                pdf_classifier.py
                pdf_loader.py
                text_extractor.py
            ocr/
                image_preprocessor.py
                ocr_engine.py
                ocr_postprocessor.py
            layout/
                header_footer_detector.py
                layout_analyzer.py
                reading_order.py
            content/
                code_detector.py
                equation_detector.py
                figure_detector.py
                marks_detector.py
                question_detector.py
                subquestion_detector.py
                table_detector.py
            reconstruction/
                question_reconstructor.py
                text_cleaner.py
            validation/
                confidence.py
                consistency_checker.py
                validator.py
            output/
                csv_writer.py
                jsonl_writer.py
                report_generator.py
    scripts/
        run_extraction.py
        export_csvs.py
    config/
        default.yaml
    tests/
        unit/
        integration/
        fixtures/
    docs/
        architecture.md
        pipeline_stages.md
        output_schema.md
    pyproject.toml
    .gitignore
    LICENSE
```

---
