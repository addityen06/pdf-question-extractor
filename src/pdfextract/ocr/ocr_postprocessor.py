from __future__ import annotations

import logging
from pdfextract.core.models import ElementBlock, BoundingBox, ExtractionSource, BlockType
from pdfextract.core.config import OCRConfig

logger = logging.getLogger(__name__)


def postprocess_ocr_results(
    elements: list[ElementBlock],
    page_width: float,
    page_height: float,
    config: OCRConfig | None = None
) -> list[ElementBlock]:
    """
    Post-process OCR output to merge fragments on the same line and clean results.
    """
    if not elements:
        return []

    # Sort elements top-to-bottom, left-to-right
    elements.sort(key=lambda e: (e.bbox.y0, e.bbox.x0))
    
    merged: list[ElementBlock] = []
    current_line: list[ElementBlock] = []
    
    for el in elements:
        if el.confidence is not None and el.confidence < 0.5:
            el.metadata['low_confidence'] = True
            
        if not current_line:
            current_line.append(el)
            continue
            
        last = current_line[-1]
        
        # Check vertical overlap
        y_overlap = last.bbox.vertical_overlap_ratio(el.bbox)
        
        # Check horizontal distance
        h_dist = el.bbox.x0 - last.bbox.x1
        
        # Merge if on the same horizontal line and closely positioned
        if y_overlap > 0.4 and -10.0 <= h_dist < 40.0:
            current_line.append(el)
        else:
            merged.append(_merge_elements(current_line))
            current_line = [el]
            
    if current_line:
        merged.append(_merge_elements(current_line))
        
    return merged


def _merge_elements(elements: list[ElementBlock]) -> ElementBlock:
    if len(elements) == 1:
        return elements[0]
        
    base = elements[0]
    texts = [e.content for e in elements if e.content]
    
    x0 = min(e.bbox.x0 for e in elements)
    y0 = min(e.bbox.y0 for e in elements)
    x1 = max(e.bbox.x1 for e in elements)
    y1 = max(e.bbox.y1 for e in elements)
    
    confidences = [e.confidence for e in elements if e.confidence is not None]
    avg_conf = sum(confidences) / len(confidences) if confidences else 1.0
    new_bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
    
    return ElementBlock(
        block_id=base.block_id,
        page=base.page,
        bbox=new_bbox,
        block_type=base.block_type,
        content=" ".join(texts),
        font_name=base.font_name,
        font_size=base.font_size,
        is_bold=base.is_bold,
        is_italic=base.is_italic,
        color=None,
        confidence=avg_conf,
        source=ExtractionSource.OCR,
        raw_text=" ".join(e.raw_text for e in elements if e.raw_text),
        metadata=base.metadata
    )
