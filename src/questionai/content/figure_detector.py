from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import pymupdf as fitz

from questionai.core.models import ElementBlock, ContentBlock, BlockType
from questionai.core.config import ContentDetectionConfig

logger = logging.getLogger(__name__)


def detect_figures(
    page: Any,
    page_image: Any,
    page_number: int,
    elements: list[ElementBlock],
    output_dir: Path,
    paper_prefix: str,
    config: ContentDetectionConfig | None = None
) -> list[ContentBlock]:
    """
    Detect figures/diagrams in PDF pages and save image assets to assets/.
    """
    detected: list[ContentBlock] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Native embedded image extraction via PyMuPDF
    if hasattr(page, "get_images") and hasattr(page, "parent"):
        doc = page.parent
        try:
            images = page.get_images(full=True)
            for i, img_info in enumerate(images):
                xref = img_info[0]
                pix = fitz.Pixmap(doc, xref)
                
                # Filter out tiny icons / logos (width/height < 40 or area < 2000)
                if pix.width < 40 or pix.height < 40 or (pix.width * pix.height < 2000):
                    pix = None
                    continue
                    
                # Convert CMYK if needed
                if pix.n >= 5:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                img_name = f"{paper_prefix}_p{page_number}_fig{i+1}.png"
                img_path = output_dir / img_name
                pix.save(str(img_path))
                pix = None
                
                rel_path = f"assets/{img_name}"
                block = ContentBlock(
                    type=BlockType.FIGURE,
                    content="",
                    image_path=rel_path,
                    caption=f"Figure {i+1} on page {page_number}",
                    confidence=0.95,
                    source_page=page_number,
                    source_bbox=None
                )
                detected.append(block)
                logger.info(f"Saved extracted figure to {img_path}")
        except Exception as e:
            logger.warning(f"Error extracting images from page {page_number}: {e}")
            
    return detected
