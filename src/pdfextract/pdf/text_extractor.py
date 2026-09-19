from __future__ import annotations
import logging
import uuid
import pymupdf as fitz

from pdfextract.core.models import ElementBlock, BoundingBox, ExtractionSource, BlockType
from pdfextract.core.exceptions import ExtractionError

logger = logging.getLogger(__name__)


def extract_native_text(page: fitz.Page, page_number: int) -> list[ElementBlock]:
    """Extract text with positional/typographic information from native PDF pages."""
    logger.info(f"Extracting native text from page {page_number}")
    elements = []
    
    try:
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        
        for block in blocks:
            if block.get("type") != 0:
                continue
                
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                        
                    bbox = span.get("bbox")
                    if not bbox or len(bbox) != 4:
                        continue
                        
                    font_name = span.get("font", "Unknown")
                    flags = span.get("flags", 0)
                    
                    is_bold = bool(flags & (2**4)) or 'Bold' in font_name or 'bold' in font_name.lower()
                    is_italic = bool(flags & (2**1)) or 'Italic' in font_name or 'italic' in font_name.lower()
                    
                    color_int = span.get("color", 0)
                    color = color_int if isinstance(color_int, int) else None
                    
                    element = ElementBlock(
                        block_id=str(uuid.uuid4()),
                        page=page_number,
                        bbox=BoundingBox(
                            x0=float(bbox[0]),
                            y0=float(bbox[1]),
                            x1=float(bbox[2]),
                            y1=float(bbox[3])
                        ),
                        block_type=BlockType.TEXT,
                        content=text,
                        font_name=font_name,
                        font_size=float(span.get("size", 10.0)),
                        is_bold=is_bold,
                        is_italic=is_italic,
                        color=color,
                        confidence=1.0,
                        source=ExtractionSource.NATIVE,
                        raw_text=text,
                        metadata={}
                    )
                    elements.append(element)
                    
    except Exception as e:
        logger.error(f"Error extracting native text on page {page_number}: {e}")
        
    return elements
