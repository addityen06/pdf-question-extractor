from __future__ import annotations

import logging
from pathlib import Path
import pymupdf as fitz

from pdfextract.core.models import PDFClassification, PageClassification, PDFPageType
from pdfextract.core.config import ExtractionConfig

logger = logging.getLogger(__name__)


def classify_pdf(file_path: Path, config: ExtractionConfig | None = None) -> PDFClassification:
    """
    Classify a PDF document as native, scanned, or hybrid by inspecting each page.
    """
    file_path = Path(file_path)
    logger.debug(f"Classifying PDF: {file_path.name}")
    
    text_char_threshold = getattr(config, 'native_text_threshold', 50) if config else 50
    image_area_threshold = getattr(config, 'image_area_threshold', 0.5) if config else 0.5
    
    pages: list[PageClassification] = []
    overall_type = PDFPageType.HYBRID
    page_count = 0
    file_size_bytes = 0
    
    try:
        if file_path.exists():
            file_size_bytes = file_path.stat().st_size
            
        doc = fitz.open(str(file_path))
        page_count = len(doc)
        
        all_scanned = True
        all_native = True
        
        for i, page in enumerate(doc):
            text = page.get_text() or ""
            text_char_count = len(text.strip())
            
            image_list = page.get_images()
            image_count = len(image_list)
            
            image_area = 0.0
            page_area = float(page.rect.width * page.rect.height)
            
            for img in image_list:
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    image_area += float(pix.width * pix.height)
                    pix = None
                except Exception:
                    pass
                
            image_area_ratio = min(1.0, image_area / page_area) if page_area > 0 else 0.0
            
            # Classification rules:
            if text_char_count < text_char_threshold and (image_area_ratio > image_area_threshold or image_count > 0):
                page_type = PDFPageType.SCANNED
                all_native = False
            elif text_char_count >= text_char_threshold and image_area_ratio < 0.8:
                page_type = PDFPageType.NATIVE
                all_scanned = False
            else:
                page_type = PDFPageType.HYBRID
                all_native = False
                all_scanned = False
                
            pages.append(PageClassification(
                page_number=i + 1,
                page_type=page_type,
                text_char_count=text_char_count,
                image_count=image_count,
                image_area_ratio=image_area_ratio,
                has_selectable_text=(text_char_count > 0),
                confidence=1.0
            ))
            
        if page_count > 0:
            if all_native:
                overall_type = PDFPageType.NATIVE
            elif all_scanned:
                overall_type = PDFPageType.SCANNED
            else:
                overall_type = PDFPageType.HYBRID
            
        doc.close()
            
    except Exception as e:
        logger.error(f"Error classifying PDF {file_path}: {e}")
        overall_type = PDFPageType.SCANNED
        
    return PDFClassification(
        file_path=str(file_path),
        overall_type=overall_type,
        page_count=page_count,
        pages=pages,
        file_size_bytes=file_size_bytes
    )
