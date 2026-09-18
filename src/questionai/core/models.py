from __future__ import annotations

import enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field

DEFAULT_QUESTION_SEPARATOR = "<<<QUESTION_END>>>"


class ExamType(str, enum.Enum):
    CAT1 = "CAT-1"
    CAT2 = "CAT-2"
    FAT = "FAT"
    UNKNOWN = "Unknown"


class Semester(str, enum.Enum):
    FALL = "Fall_Semester"
    WINTER = "Winter_Semester"
    SUMMER = "Summer_Semester"
    UNKNOWN = "Unknown"


class BlockType(str, enum.Enum):
    TEXT = "text"
    EQUATION = "equation"
    MATRIX = "matrix"
    TABLE = "table"
    CODE = "code"
    FIGURE = "figure"
    HEADER = "header"
    FOOTER = "footer"
    MARKS = "marks"
    ADMINISTRATIVE = "administrative"
    UNKNOWN = "unknown"


class ExtractionSource(str, enum.Enum):
    NATIVE = "native"
    OCR = "ocr"
    HYBRID = "hybrid"


class PDFPageType(str, enum.Enum):
    NATIVE = "native"
    SCANNED = "scanned"
    HYBRID = "hybrid"


class VerificationStatus(str, enum.Enum):
    AUTO_EXTRACTED = "auto_extracted"
    REVIEW_RECOMMENDED = "review_recommended"
    REVIEW_REQUIRED = "review_required"
    MANUAL_VERIFIED = "manual_verified"


class ProcessingStatus(str, enum.Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConfidenceTier(str, enum.Enum):
    HIGH = "high"          # >= 0.85 -> AUTO_EXTRACTED
    MEDIUM = "medium"      # 0.70 - 0.84 -> REVIEW_RECOMMENDED
    LOW = "low"            # 0.50 - 0.69 -> REVIEW_REQUIRED
    VERY_LOW = "very_low"  # < 0.50 -> REVIEW_REQUIRED


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2.0

    def overlaps(self, other: BoundingBox) -> bool:
        return not (
            self.x1 < other.x0 or
            self.x0 > other.x1 or
            self.y1 < other.y0 or
            self.y0 > other.y1
        )

    def merge(self, other: BoundingBox) -> BoundingBox:
        return BoundingBox(
            x0=min(self.x0, other.x0),
            y0=min(self.y0, other.y0),
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
        )

    def vertical_overlap_ratio(self, other: BoundingBox) -> float:
        overlap = max(0.0, min(self.y1, other.y1) - max(self.y0, other.y0))
        min_h = min(self.height, other.height)
        if min_h == 0.0:
            return 0.0
        return overlap / min_h


class ElementBlock(BaseModel):
    block_id: str
    page: int
    bbox: BoundingBox
    block_type: BlockType = BlockType.TEXT
    content: str
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    is_bold: bool = False
    is_italic: bool = False
    color: Optional[int] = None
    confidence: float = 1.0
    source: ExtractionSource = ExtractionSource.NATIVE
    raw_text: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineBlock(BaseModel):
    line_id: str
    page: int
    bbox: BoundingBox
    elements: list[ElementBlock] = Field(default_factory=list)
    text: str = ""
    avg_font_size: float = 10.0
    dominant_font: Optional[str] = None
    is_bold: bool = False
    is_italic: bool = False
    indent_level: float = 0.0
    line_spacing_above: float = 0.0


class ParagraphBlock(BaseModel):
    paragraph_id: str
    page: int
    bbox: BoundingBox
    lines: list[LineBlock] = Field(default_factory=list)
    text: str = ""
    block_type: BlockType = BlockType.TEXT
    column: int = 0


class PaperMetadata(BaseModel):
    file_path: str
    file_name: str
    course_code: str
    exam_type: str = "Unknown"
    academic_year: str = "Unknown"
    semester: str = "Unknown"
    slot: str = "Unknown"
    campus: str = "Unknown"
    is_answer_key: bool = False
    file_hash: str = "Unknown"
    parse_warnings: list[str] = Field(default_factory=list)


class PageClassification(BaseModel):
    page_number: int
    page_type: PDFPageType
    text_char_count: int = 0
    image_count: int = 0
    image_area_ratio: float = 0.0
    has_selectable_text: bool = False
    confidence: float = 1.0


class PDFClassification(BaseModel):
    file_path: str
    overall_type: PDFPageType
    page_count: int
    pages: list[PageClassification] = Field(default_factory=list)
    file_size_bytes: int = 0


class ContentBlock(BaseModel):
    type: BlockType = BlockType.TEXT
    content: str = ""
    language: Optional[str] = None
    rows: Optional[list[list[str]]] = None
    image_path: Optional[str] = None
    caption: Optional[str] = None
    latex: Optional[str] = None
    confidence: float = 1.0
    source_page: int = 1
    source_bbox: Optional[BoundingBox] = None


class Question(BaseModel):
    question_id: str
    course_code: str
    paper_file: str
    paper_id: str = ""
    exam_type: str = ""
    academic_year: str = ""
    semester: str = ""
    slot: str = ""
    campus: str = ""
    is_answer_key: bool = False
    question_number: int
    subquestion: Optional[str] = None
    parent_question: Optional[int] = None
    marks: Optional[int] = None
    choice_group: Optional[str] = None
    question_type: str = "theory"
    blocks: list[ContentBlock] = Field(default_factory=list)
    question_text: str = ""
    separator: str = DEFAULT_QUESTION_SEPARATOR
    extraction_confidence: float = 1.0
    verification_status: VerificationStatus = VerificationStatus.AUTO_EXTRACTED
    warnings: list[str] = Field(default_factory=list)
    source_pages: list[int] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    check_id: str
    check_name: str
    status: str = "PASS"
    detail: str = ""
    severity: str = "INFO"


class ValidationResult(BaseModel):
    paper_file: str
    course_code: str
    validation_passed: bool = True
    checks: list[ValidationCheck] = Field(default_factory=list)
    warning_count: int = 0
    error_count: int = 0
    overall_status: str = "VALID"


class ExtractionReport(BaseModel):
    paper_file: str
    course_code: str
    exam_type: str = ""
    academic_year: str = ""
    semester: str = ""
    is_answer_key: bool = False
    pages: int = 0
    pdf_type: str = "unknown"
    questions_detected: int = 0
    subquestions_detected: int = 0
    marks_detected: Optional[int] = None
    stated_max_marks: Optional[int] = None
    marks_match: Optional[bool] = None
    ocr_used: bool = False
    ocr_engine: Optional[str] = None
    avg_ocr_confidence: Optional[float] = None
    equations_detected: int = 0
    matrices_detected: int = 0
    tables_detected: int = 0
    code_blocks_detected: int = 0
    figures_detected: int = 0
    figures_saved: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    overall_confidence: float = 1.0
    processing_time_seconds: float = 0.0
    extractor_version: str = "1.0.0"
    processing_date: str = ""
    validation: Optional[ValidationResult] = None
    processing_status: ProcessingStatus = ProcessingStatus.SUCCESS
