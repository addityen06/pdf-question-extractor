"""
Custom Exceptions
================================
Typed exception hierarchy for clean error handling and reporting.
"""

from __future__ import annotations


class PdfExtractError(Exception):
    """Base exception for all extraction errors."""
    pass


# ── Ingestion ────────────────────────────────────────────────────────────────

class FileDiscoveryError(PdfExtractError):
    """Raised when the papers directory cannot be scanned."""
    pass


class FilenameParseError(PdfExtractError):
    """Raised when a PDF filename does not match the expected pattern."""
    def __init__(self, filename: str, reason: str = ""):
        self.filename = filename
        self.reason = reason
        super().__init__(f"Cannot parse filename '{filename}': {reason}")


# ── PDF Processing ───────────────────────────────────────────────────────────

class PDFLoadError(PdfExtractError):
    """Raised when a PDF cannot be opened or read."""
    def __init__(self, file_path: str, reason: str = ""):
        self.file_path = file_path
        super().__init__(f"Cannot load PDF '{file_path}': {reason}")


class PDFClassificationError(PdfExtractError):
    """Raised when PDF type classification fails."""
    pass


class PageRenderError(PdfExtractError):
    """Raised when a PDF page cannot be rendered to an image."""
    def __init__(self, file_path: str, page: int, reason: str = ""):
        self.file_path = file_path
        self.page = page
        super().__init__(f"Cannot render page {page} of '{file_path}': {reason}")


# ── OCR ──────────────────────────────────────────────────────────────────────

class OCRError(PdfExtractError):
    """Raised when OCR processing fails."""
    def __init__(self, file_path: str, page: int, reason: str = ""):
        self.file_path = file_path
        self.page = page
        super().__init__(f"OCR failed on page {page} of '{file_path}': {reason}")


class OCREngineNotAvailable(PdfExtractError):
    """Raised when the configured OCR engine is not installed."""
    def __init__(self, engine: str):
        self.engine = engine
        super().__init__(f"OCR engine '{engine}' is not available on this system")


# ── Layout ───────────────────────────────────────────────────────────────────

class LayoutAnalysisError(PdfExtractError):
    """Raised when layout analysis fails for a page."""
    pass


# ── Extraction ───────────────────────────────────────────────────────────────

class ExtractionError(PdfExtractError):
    """Raised when the overall extraction pipeline fails for a paper."""
    def __init__(self, file_path: str, reason: str = ""):
        self.file_path = file_path
        super().__init__(f"Extraction failed for '{file_path}': {reason}")


class QuestionDetectionError(PdfExtractError):
    """Raised when no questions can be detected in a paper."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"No questions detected in '{file_path}'")


# ── Validation ───────────────────────────────────────────────────────────────

class ValidationError(PdfExtractError):
    """Raised when validation of extracted data fails critically."""
    pass


# ── Output ───────────────────────────────────────────────────────────────────

class OutputWriteError(PdfExtractError):
    """Raised when output files cannot be written."""
    def __init__(self, output_path: str, reason: str = ""):
        self.output_path = output_path
        super().__init__(f"Cannot write output to '{output_path}': {reason}")


# ── Configuration ────────────────────────────────────────────────────────────

class ConfigError(PdfExtractError):
    """Raised when configuration is invalid or cannot be loaded."""
    pass
