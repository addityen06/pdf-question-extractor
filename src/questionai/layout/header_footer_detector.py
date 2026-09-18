from __future__ import annotations

import logging
import re
from questionai.core.models import ParagraphBlock, BlockType
from questionai.core.constants import ADMIN_KEYWORDS, ADMIN_PATTERNS, MAX_MARKS_PATTERNS, QUESTION_PATTERNS
from questionai.core.config import ExtractionConfig

logger = logging.getLogger(__name__)

# Compile keyword patterns with word boundaries for short keywords
COMPILED_ADMIN_KEYWORDS = []
for kw in ADMIN_KEYWORDS:
    if len(kw) <= 4:
        COMPILED_ADMIN_KEYWORDS.append(re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE))
    else:
        COMPILED_ADMIN_KEYWORDS.append(re.compile(re.escape(kw), re.IGNORECASE))


def detect_and_remove_admin(
    paragraphs: list[ParagraphBlock],
    page_count: int,
    page_height: float,
    config: ExtractionConfig | None = None
) -> tuple[list[ParagraphBlock], list[ParagraphBlock], dict]:
    """
    Detect and classify header/footer/administrative content.
    Extracts paper metadata (e.g. max marks, course code) from headers.
    """
    body_paragraphs: list[ParagraphBlock] = []
    admin_paragraphs: list[ParagraphBlock] = []
    metadata: dict = {}
    
    max_header_ratio = getattr(config, 'max_header_height_ratio', 0.25) if config else 0.25
    max_footer_ratio = getattr(config, 'max_footer_height_ratio', 0.08) if config else 0.08
    
    max_header_height = page_height * max_header_ratio
    min_footer_height = page_height * (1.0 - max_footer_ratio)
    
    for para in paragraphs:
        text = (para.text or "").strip()
        if not text:
            continue
            
        is_admin = False
        
        # Check if this paragraph starts with a question numbering pattern
        is_question_start = False
        for qpat in QUESTION_PATTERNS:
            if qpat.match(text):
                is_question_start = True
                break
                
        # Position checks:
        # Top of Page 1 is almost always university header / metadata block
        if para.page == 1 and para.bbox.y0 < max_header_height:
            # If it's in the top header zone and not an obvious question, or contains admin phrases
            if not is_question_start:
                is_admin = True
            else:
                # Check if it has strong admin keywords like "Assessment Test" or "Vellore Institute"
                for pat in COMPILED_ADMIN_KEYWORDS:
                    if pat.search(text):
                        is_admin = True
                        break
        elif para.bbox.y0 > min_footer_height and not is_question_start:
            # Bottom margin / footer (page numbers, etc.)
            is_admin = True
            
        if not is_admin and not is_question_start:
            # Check pattern matches
            for pat in ADMIN_PATTERNS:
                if pat.search(text):
                    is_admin = True
                    break
                    
        if not is_admin and not is_question_start:
            # Check strong keyword matches
            match_count = 0
            for pat in COMPILED_ADMIN_KEYWORDS:
                if pat.search(text):
                    match_count += 1
            if match_count >= 1 and (para.bbox.y0 < page_height * 0.35 or 'malpractice' in text.lower() or 'mobile phone' in text.lower()):
                is_admin = True
                
        # Extract max marks from text (even in admin sections)
        for pat in MAX_MARKS_PATTERNS:
            match = pat.search(text)
            if match:
                try:
                    metadata['max_marks'] = int(match.group('marks'))
                except (IndexError, ValueError):
                    pass
                
        if 'course code' in text.lower() or 'course name' in text.lower():
            metadata['course_info'] = text
            
        if is_admin:
            para.block_type = BlockType.ADMINISTRATIVE
            admin_paragraphs.append(para)
        else:
            body_paragraphs.append(para)
            
    logger.info(f"Layout separation: {len(body_paragraphs)} body paragraphs, {len(admin_paragraphs)} administrative paragraphs")
    return body_paragraphs, admin_paragraphs, metadata
