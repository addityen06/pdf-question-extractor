from __future__ import annotations
import logging
from pathlib import Path
import fitz

from pdfextract.core.exceptions import PDFLoadError

logger = logging.getLogger(__name__)

class PDFDocument:
    """Load and manage PDF documents safely with context management."""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._doc = None

    def __enter__(self):
        try:
            self._doc = fitz.open(str(self.file_path))
            if self._doc.is_encrypted:
                logger.warning(f"PDF {self.file_path} is encrypted, attempting to unlock...")
                self._doc.authenticate("")
        except Exception as e:
            raise PDFLoadError(f"Failed to load PDF {self.file_path}: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._doc:
            self._doc.close()
            self._doc = None

    @property
    def page_count(self) -> int:
        if not self._doc:
            raise PDFLoadError("Document not loaded. Use within a context manager.")
        return len(self._doc)

    @property
    def metadata(self) -> dict:
        if not self._doc:
            raise PDFLoadError("Document not loaded.")
        return self._doc.metadata

    def get_page(self, n: int) -> fitz.Page:
        if not self._doc:
            raise PDFLoadError("Document not loaded.")
        try:
            return self._doc[n]
        except IndexError:
            raise PDFLoadError(f"Page {n} out of range (0 to {self.page_count - 1}).")

    def get_page_dimensions(self, n: int) -> tuple[float, float]:
        page = self.get_page(n)
        return page.rect.width, page.rect.height


def load_pdf(file_path: Path) -> PDFDocument:
    """Helper function to create a PDFDocument instance."""
    return PDFDocument(file_path)
