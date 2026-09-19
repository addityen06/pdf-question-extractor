from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field

from pdfextract.core.models import DEFAULT_QUESTION_SEPARATOR


class PathsConfig(BaseModel):
    papers_dir: str = "Papers"
    output_dir: str = "textPapers"
    csv_output_dir: str = "textPapersCSV"
    reports_dir: str = "reports"
    logs_dir: str = "logs"


class ExtractionConfig(BaseModel):
    native_text_threshold: int = 50
    image_area_threshold: float = 0.5
    max_header_height_ratio: float = 0.25
    max_footer_height_ratio: float = 0.08
    min_question_text_length: int = 15
    line_merge_y_tolerance: float = 3.0
    paragraph_gap_multiplier: float = 1.5
    column_detection_min_gap: float = 30.0
    question_separator: str = DEFAULT_QUESTION_SEPARATOR


class OCRConfig(BaseModel):
    engine: str = "apple_vision"
    dpi: int = 300
    language: str = "en"
    recognition_level: str = "accurate"
    min_confidence: float = 0.3
    grayscale: bool = True
    adaptive_threshold: bool = False
    deskew: bool = True


class QuestionDetectionConfig(BaseModel):
    question_signal_threshold: int = 3
    marks_search_radius: float = 200.0
    subquestion_indent_threshold: float = 15.0
    or_choice_detection: bool = True
    expected_numbering_start: int = 1


class ContentDetectionConfig(BaseModel):
    code_keyword_threshold: int = 2
    math_symbol_threshold: int = 2
    table_min_columns: int = 2
    table_min_rows: int = 2
    figure_min_area: float = 3000.0


class ConfidenceConfig(BaseModel):
    weights: dict[str, float] = Field(default_factory=lambda: {
        "ocr_confidence": 0.25,
        "question_number": 0.20,
        "marks_detection": 0.10,
        "boundary_confidence": 0.20,
        "content_completeness": 0.15,
        "validation_checks": 0.10,
    })
    tier_high: float = 0.85
    tier_medium: float = 0.70
    tier_low: float = 0.50


class ValidationConfig(BaseModel):
    check_sequential_numbers: bool = True
    check_marks_sum: bool = True
    check_admin_content: bool = True
    check_truncation: bool = True
    check_brackets_balanced: bool = True
    marks_tolerance_percent: float = 10.0
    min_question_length: int = 15


class CleaningConfig(BaseModel):
    remove_duplicate_whitespace: bool = True
    remove_page_numbers: bool = True
    normalize_unicode: bool = True
    preserve_code_whitespace: bool = True
    preserve_math_symbols: bool = True


class BatchConfig(BaseModel):
    max_workers: int = 1
    resume_on_restart: bool = True
    skip_answer_keys: bool = False
    skip_model_papers: bool = False


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_to_file: bool = True
    log_format: str = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    rich_console: bool = True


class PipelineConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    question_detection: QuestionDetectionConfig = Field(default_factory=QuestionDetectionConfig)
    content_detection: ContentDetectionConfig = Field(default_factory=ContentDetectionConfig)
    confidence: ConfidenceConfig = Field(default_factory=ConfidenceConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    batch: BatchConfig = Field(default_factory=BatchConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    extractor_version: str = "1.0.0"


def load_config(config_path: str | Path | None = None) -> PipelineConfig:
    if config_path is None:
        return PipelineConfig()
    path = Path(config_path)
    if not path.exists():
        return PipelineConfig()
    with open(path, "r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}
    return PipelineConfig(**raw)
