from __future__ import annotations

import logging
import re
from questionai.core.models import ElementBlock, BoundingBox
from questionai.core.constants import MARKS_PATTERNS, MAX_MARKS_PATTERNS

logger = logging.getLogger(__name__)


def detect_question_marks(text: str, nearby_text: str = '') -> int | None:
    """
    Detect marks allocation for questions and subquestions.
    """
    combined_text = f"{text} {nearby_text}"
    
    # Check for split marks e.g. 5+5 or [5]+[5]
    split_match = re.search(r'\[?(\d+)\]?\s*\+\s*\[?(\d+)\]?', combined_text)
    if split_match:
        try:
            return int(split_match.group(1)) + int(split_match.group(2))
        except (ValueError, IndexError):
            pass

    for pattern in MARKS_PATTERNS:
        match = pattern.search(combined_text)
        if match:
            try:
                gd = match.groupdict()
                if "marks" in gd:
                    return int(gd["marks"])
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
    return None


def detect_max_marks(header_text: str) -> int | None:
    """
    Detect maximum marks declared in the header/metadata.
    """
    for pattern in MAX_MARKS_PATTERNS:
        match = pattern.search(header_text)
        if match:
            try:
                gd = match.groupdict()
                if "marks" in gd:
                    return int(gd["marks"])
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
    return None


def detect_marks_from_elements(
    elements: list[ElementBlock],
    question_bbox: BoundingBox,
    search_radius: float = 200.0
) -> int | None:
    """
    Detect marks from nearby element blocks in spatial proximity.
    """
    nearby_text = []
    for el in elements:
        if el.bbox and question_bbox:
            dist_x = abs(el.bbox.x0 - question_bbox.x1)
            dist_y = abs(el.bbox.center_y - question_bbox.center_y)
            if dist_x <= search_radius and dist_y <= search_radius:
                content = el.content or el.raw_text or ""
                if content:
                    nearby_text.append(content)
                    
    if nearby_text:
        return detect_question_marks(" ".join(nearby_text))
    return None
