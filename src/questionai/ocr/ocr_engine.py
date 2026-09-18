from __future__ import annotations

import logging
import io
import uuid
from PIL import Image

try:
    import Vision
    import Quartz
    from Foundation import NSData
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

from questionai.core.models import ElementBlock, BoundingBox, BlockType, ExtractionSource
from questionai.core.config import OCRConfig
from questionai.core.exceptions import OCREngineNotAvailable

logger = logging.getLogger(__name__)


def check_engine_available() -> bool:
    return VISION_AVAILABLE


def pil_to_cgimage(image: Image.Image):
    """Convert PIL image to CGImage using NSData."""
    img_byte_arr = io.BytesIO()
    # Save as PNG
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    data_bytes = img_byte_arr.getvalue()
    ns_data = NSData.dataWithBytes_length_(data_bytes, len(data_bytes))
    
    options = {
        Quartz.kCGImageSourceShouldCache: True
    }
    source = Quartz.CGImageSourceCreateWithData(ns_data, options)
    if not source:
        return None
    cg_image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
    return cg_image


def ocr_page(
    image: Image.Image,
    page_number: int,
    page_width: float,
    page_height: float,
    config: OCRConfig | None = None
) -> list[ElementBlock]:
    """
    Perform OCR using Apple Vision framework (macOS native).
    Transforms normalized bottom-left origin coordinates to PDF top-left points.
    """
    if not check_engine_available():
        raise OCREngineNotAvailable("apple_vision")
        
    logger.info(f"Running Apple Vision OCR on page {page_number}")
    cg_image = pil_to_cgimage(image)
    if not cg_image:
        logger.error(f"Failed to create CGImage from page {page_number}")
        return []
    
    request = Vision.VNRecognizeTextRequest.alloc().init()
    
    rec_level = getattr(config, 'recognition_level', 'accurate') if config else 'accurate'
    if rec_level == 'fast':
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)
    else:
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        
    lang = getattr(config, 'language', 'en') if config else 'en'
    request.setRecognitionLanguages_([lang])
    request.setUsesLanguageCorrection_(True)
    
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
    success, error = handler.performRequests_error_([request], None)
    if not success or error:
        logger.error(f"OCR request failed on page {page_number}: {error}")
        return []
        
    results = request.results()
    if not results:
        return []
        
    min_confidence = getattr(config, 'min_confidence', 0.3) if config else 0.3
    elements: list[ElementBlock] = []
    
    for obs in results:
        top_candidates = obs.topCandidates_(1)
        if not top_candidates:
            continue
            
        candidate = top_candidates[0]
        text = str(candidate.string()).strip()
        confidence = float(candidate.confidence())
        
        if not text or confidence < min_confidence:
            continue
        
        # Vision coords: origin is at BOTTOM-LEFT, normalized [0, 1]
        bbox = obs.boundingBox()
        x = float(bbox.origin.x)
        y = float(bbox.origin.y)
        w = float(bbox.size.width)
        h = float(bbox.size.height)
        
        # Convert to PDF coordinates (origin at TOP-LEFT, in points)
        x_pdf = x * page_width
        y_pdf = (1.0 - y - h) * page_height
        x1_pdf = (x + w) * page_width
        y1_pdf = (1.0 - y) * page_height
        
        box = BoundingBox(
            x0=max(0.0, x_pdf),
            y0=max(0.0, y_pdf),
            x1=min(page_width, x1_pdf),
            y1=min(page_height, y1_pdf)
        )
        
        # Approximate font size from bounding box height
        approx_font_size = max(6.0, box.height * 0.8)
        
        el = ElementBlock(
            block_id=str(uuid.uuid4()),
            page=page_number,
            bbox=box,
            block_type=BlockType.TEXT,
            content=text,
            font_name="OCR_Recognized",
            font_size=approx_font_size,
            is_bold=False,
            is_italic=False,
            color=None,
            confidence=confidence,
            source=ExtractionSource.OCR,
            raw_text=text,
            metadata={"apple_vision_conf": confidence}
        )
        elements.append(el)
        
    # Sort top-to-bottom, left-to-right
    elements.sort(key=lambda e: (e.bbox.y0, e.bbox.x0))
    logger.info(f"Recognized {len(elements)} text observations on page {page_number}")
    return elements
