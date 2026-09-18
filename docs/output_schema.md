# Output Schema

## CSV Schema

Each extracted paper produces a CSV file with the following columns.

| Column | Type | Description |
|---|---|---|
| `question_number` | int | Sequential question number starting from 1 |
| `subquestion` | str | Subquestion label (`a`, `b`, `i`, `ii`) or empty string |
| `marks` | int or empty | Marks allocated to this question or subquestion |
| `question_type` | str | `theory`, `numerical`, or `programming` |
| `question_text` | str | Full extracted question text terminated with `<<<QUESTION_END>>>` |
| `separator` | str | The question separator constant (`<<<QUESTION_END>>>`) |
| `confidence` | float | Extraction confidence, two decimal places, range 0.00 to 1.00 |
| `verification_status` | str | `auto_extracted`, `review_recommended`, or `review_required` |
| `course_code` | str | Course identifier, e.g. `BACSE104` |
| `paper_file` | str | Source PDF filename |
| `exam_type` | str | `CAT-1`, `CAT-2`, `FAT`, or `Unknown` |
| `academic_year` | str | Academic year string, e.g. `2024-2025` |
| `semester` | str | `Fall_Semester`, `Winter_Semester`, `Summer_Semester`, or `Unknown` |
| `has_equation` | bool | Whether the question contains a detected equation block |
| `has_code` | bool | Whether the question contains a detected code block |
| `has_table` | bool | Whether the question contains a detected table block |
| `has_figure` | bool | Whether the question contains an embedded figure reference |
| `choice_group` | str | OR-choice group identifier (e.g. `OR_1`) or empty string |

## Question Separator

Every `question_text` value is terminated with the string `<<<QUESTION_END>>>` on a new line. This acts as a programmatic boundary marker for downstream consumers that need to split multi-question text safely without relying on newlines alone.

Example:

```
Explain the working of a binary search tree and derive the time complexity for insertion.
<<<QUESTION_END>>>
```

## Output Directories

```
textPapers/
    <course_code>/
        <paper_stem>.csv                     Question CSV
        <paper_stem>_raw.json                Raw Question objects (full Pydantic dump)
        <paper_stem>_extraction_report.json  Per-paper extraction report
        <paper_stem>_assets/                 Extracted figures (PNG)

textPapersCSV/
    <course_code>/
        <paper_stem>.csv                     Clean CSV-only mirror of textPapers
```

## Extraction Report Schema

The JSON extraction report for each paper contains:

```json
{
  "paper_file": "CAT-1_2024-2025_Fall_Semester_D1_Vellore_85f84318.pdf",
  "course_code": "BACSE104",
  "exam_type": "CAT-1",
  "academic_year": "2024-2025",
  "semester": "Fall_Semester",
  "is_answer_key": false,
  "pages": 4,
  "pdf_type": "native",
  "questions_detected": 8,
  "subquestions_detected": 12,
  "marks_detected": 100,
  "stated_max_marks": 100,
  "marks_match": true,
  "ocr_used": false,
  "ocr_engine": null,
  "avg_ocr_confidence": null,
  "equations_detected": 3,
  "tables_detected": 1,
  "code_blocks_detected": 0,
  "figures_detected": 0,
  "figures_saved": [],
  "warnings": [],
  "errors": [],
  "overall_confidence": 0.91,
  "processing_time_seconds": 2.34,
  "extractor_version": "1.0.0",
  "processing_date": "2026-09-18T09:21:00+00:00",
  "processing_status": "success",
  "validation": {
    "paper_file": "CAT-1_2024-2025_Fall_Semester_D1_Vellore_85f84318.pdf",
    "course_code": "BACSE104",
    "validation_passed": true,
    "checks": [...],
    "warning_count": 0,
    "error_count": 0,
    "overall_status": "PASS"
  }
}
```

## Confidence Score Composition

The confidence score for each question is a weighted sum across six signals:

| Signal | Default Weight |
|---|---|
| OCR confidence (avg word-level score) | 0.30 |
| Question number detectability | 0.15 |
| Marks detection | 0.10 |
| Boundary detection quality | 0.20 |
| Content completeness | 0.15 |
| Validation check results | 0.10 |

Weights are configurable in `config/default.yaml` under the `confidence.weights` section.
