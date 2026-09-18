from __future__ import annotations

import logging
from questionai.core.models import ParagraphBlock

logger = logging.getLogger(__name__)


def detect_columns(paragraphs: list[ParagraphBlock], page_width: float) -> int:
    """Detect number of columns based on horizontal x-coordinate distribution."""
    if not paragraphs or len(paragraphs) < 4:
        return 1
        
    x0_vals = [p.bbox.x0 for p in paragraphs if p.bbox and p.bbox.x0 is not None]
    if not x0_vals:
        return 1
        
    mid_x = page_width * 0.45
    left_count = sum(1 for x in x0_vals if x < mid_x)
    right_count = sum(1 for x in x0_vals if x >= mid_x)
    
    # If there are substantially many paragraphs in both left and right halves
    if left_count >= 3 and right_count >= 3 and min(left_count, right_count) / len(paragraphs) > 0.25:
        return 2
    return 1


def order_paragraphs(paragraphs: list[ParagraphBlock], page_width: float) -> list[ParagraphBlock]:
    """
    Reconstruct correct semantic reading order from paragraphs on a page.
    """
    if not paragraphs:
        return []
        
    num_cols = detect_columns(paragraphs, page_width)
    
    if num_cols == 1:
        # Standard top-to-bottom reading order
        return sorted(paragraphs, key=lambda p: (p.bbox.y0, p.bbox.x0))
        
    # Multi-column logic:
    # Band-based sorting: full width blocks partition the page vertically.
    mid_x = page_width * 0.45
    
    # Sort all paragraphs vertically first
    sorted_all = sorted(paragraphs, key=lambda p: p.bbox.y0)
    
    ordered: list[ParagraphBlock] = []
    current_band: list[ParagraphBlock] = []
    
    for p in sorted_all:
        is_full_width = p.bbox.width > page_width * 0.65
        if is_full_width:
            if current_band:
                # Flush column band: left column first, then right column
                lefts = sorted([bp for bp in current_band if bp.bbox.x0 < mid_x], key=lambda bp: bp.bbox.y0)
                rights = sorted([bp for bp in current_band if bp.bbox.x0 >= mid_x], key=lambda bp: bp.bbox.y0)
                ordered.extend(lefts)
                ordered.extend(rights)
                current_band = []
            ordered.append(p)
        else:
            current_band.append(p)
            
    if current_band:
        lefts = sorted([bp for bp in current_band if bp.bbox.x0 < mid_x], key=lambda bp: bp.bbox.y0)
        rights = sorted([bp for bp in current_band if bp.bbox.x0 >= mid_x], key=lambda bp: bp.bbox.y0)
        ordered.extend(lefts)
        ordered.extend(rights)
        
    return ordered
