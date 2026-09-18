from __future__ import annotations
import logging
from pathlib import Path
import fitz
from PIL import Image

from questionai.core.exceptions import PageRenderError

logger = logging.getLogger(__name__)

def render_page(page: fitz.Page, dpi: int = 300) -> Image.Image:
    """Render a PDF page to a PIL Image at the specified DPI."""
    logger.debug(f"Rendering page to Image at {dpi} DPI")
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    
    try:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        mode = "RGB" if pix.n == 3 else "RGBA" if pix.n == 4 else "L"
        img = Image.frombytes(mode, (pix.w, pix.h), pix.samples)
        return img
    except Exception as e:
        logger.error(f"Failed to render page: {e}")
        # Return a blank white image as fallback to prevent pipeline crash
        width = int(page.rect.width * zoom)
        height = int(page.rect.height * zoom)
        return Image.new("RGB", (width, height), (255, 255, 255))

def render_page_to_file(page: fitz.Page, dpi: int, output_path: Path) -> Path:
    """Render a PDF page and save it to the specified file path."""
    logger.info(f"Rendering page to file: {output_path} at {dpi} DPI")
    img = render_page(page, dpi)
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))
    except Exception as e:
        logger.error(f"Failed to save rendered page to {output_path}: {e}")
        
    return output_path
