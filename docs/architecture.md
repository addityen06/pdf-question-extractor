# Architecture

## Overview

The pipeline is composed of nine isolated stages that execute in a strict linear order. Each stage produces a well-typed output consumed by the next stage. Failures within a stage (except total PDF load failure) are caught, logged, and reported without aborting the entire paper.

## Stage Map

```
PDF File
  |
  v
[1] PDF Classification         pdf/pdf_classifier.py
      Classifies each page as NATIVE, SCANNED, or HYBRID.
      Uses character count threshold and image area ratio.
  |
  v
[2] Text Extraction            pdf/text_extractor.py
                               ocr/ocr_engine.py
      NATIVE  -> PyMuPDF text blocks with bounding boxes and font metadata
      SCANNED -> Apple Vision OCR (macOS) with word-level confidence scores
      HYBRID  -> Both, merged by bounding box overlap analysis
  |
  v
[3] Layout Analysis            layout/layout_analyzer.py
                               layout/reading_order.py
      Groups element blocks into lines and lines into paragraphs.
      Detects multi-column layouts.
      Assigns reading order within each page.
  |
  v
[4] Administrative Removal     layout/header_footer_detector.py
      Strips headers, footers, institution names, slot info,
      registration number fields, exam duration blocks, and
      instruction paragraphs from each page.
      Extracts stated maximum marks from header metadata.
  |
  v
[5] Question Detection         content/question_detector.py
      Five-signal scoring per paragraph:
        S1 text pattern (regex, weight 3)
        S2 font emphasis (bold/size, weight 2)
        S3 marks nearby (weight 2)
        S4 vertical gap (weight 1)
        S5 indent left-shift (weight 1)
      Detects subquestion boundaries independently.
      Detects OR choice groups between adjacent questions.
      Assigns content paragraphs to each candidate.
  |
  v
[6] Specialised Content        content/equation_detector.py
    Detection                  content/code_detector.py
                               content/table_detector.py
                               content/figure_detector.py
      Scans body paragraphs for typed content blocks.
      Equations: math symbols, LaTeX-like patterns, specific keywords.
      Code: language keyword matching, monospace font detection.
      Tables: column/row alignment heuristics.
      Figures: bounding box area threshold on embedded images.
  |
  v
[7] Question Reconstruction    reconstruction/question_reconstructor.py
                               reconstruction/text_cleaner.py
      Assembles Question objects from candidates and detected content.
      Generates globally unique question IDs.
      Flattens content blocks to plain text (with equation/code/table markers).
      Applies conservative text cleaning.
  |
  v
[8] Validation and Confidence  validation/validator.py
                               validation/confidence.py
      Runs six validation checks (V1-V6).
      Computes per-question confidence from six weighted signals.
      Assigns verification tier (auto_extracted, review_recommended, review_required).
  |
  v
[9] Output Serialization       output/csv_writer.py
                               output/report_generator.py
                               output/jsonl_writer.py
      Writes textPapers/<course>/<stem>.csv (with question separator)
      Writes textPapersCSV/<course>/<stem>.csv (clean mirror)
      Writes <stem>_raw.json (raw extraction record)
      Writes <stem>_extraction_report.json (per-paper report)
```

## Data Flow Types

```
ElementBlock    - Single text span or OCR word with bbox, font, confidence
LineBlock       - Ordered list of ElementBlocks on the same line
ParagraphBlock  - Ordered list of LineBlocks forming a logical paragraph
QuestionCandidate - A scored paragraph boundary with assigned content paragraphs
ContentBlock    - A typed content unit (text, equation, code, table, figure)
Question        - The final canonical output unit with all metadata
ExtractionReport - Per-paper processing summary and validation result
```

## Hybrid Merge Strategy

When a page is classified as HYBRID, native text blocks and OCR text blocks are merged. For each OCR element, the merger checks whether any native element's bounding box overlaps with a vertical overlap ratio greater than 50%. If covered, the OCR element is discarded; otherwise it is appended as an OCR-sourced element. The merged list is then sorted by page, y0, x0.

## Resumability

Before processing any paper, the pipeline checks whether the target CSV and report JSON already exist and the report's `processing_status` is `success`. If so, the paper is skipped. Pass `--force` on the CLI to bypass this check.

## Paper Isolation

Each paper is processed completely independently. There is no shared state between papers. Output paths are derived from the paper's course code and filename stem, so concurrent processing (if added) would be safe without additional locking.
