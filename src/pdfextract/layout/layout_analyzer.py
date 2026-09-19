from __future__ import annotations

import logging
import uuid
from pdfextract.core.models import ElementBlock, LineBlock, ParagraphBlock, BoundingBox, BlockType

logger = logging.getLogger(__name__)


def analyze_layout(
    elements: list[ElementBlock],
    page_number: int,
    page_width: float,
    page_height: float,
    config: any = None
) -> list[ParagraphBlock]:
    """
    Analyze page layout — assemble elements into lines, then lines into paragraphs.
    """
    if not elements:
        return []
        
    lines = _assemble_lines(elements, page_number)
    paragraphs = _assemble_paragraphs(lines, page_number)
    _classify_paragraphs(paragraphs)
    
    return paragraphs


def _assemble_lines(elements: list[ElementBlock], page: int) -> list[LineBlock]:
    elements_sorted = sorted(elements, key=lambda e: (e.bbox.y0, e.bbox.x0))
    lines: list[LineBlock] = []
    current_group: list[ElementBlock] = []
    
    for el in elements_sorted:
        if not current_group:
            current_group.append(el)
            continue
            
        last = current_group[-1]
        y_overlap = last.bbox.vertical_overlap_ratio(el.bbox)
        
        if y_overlap > 0.4:
            current_group.append(el)
        else:
            lines.append(_create_line(current_group, page))
            current_group = [el]
            
    if current_group:
        lines.append(_create_line(current_group, page))
        
    # Calculate vertical spacing above each line
    for i in range(1, len(lines)):
        lines[i].line_spacing_above = max(0.0, lines[i].bbox.y0 - lines[i-1].bbox.y1)
        
    return lines


def _create_line(group: list[ElementBlock], page: int) -> LineBlock:
    group_sorted = sorted(group, key=lambda e: e.bbox.x0)
    texts = [e.content for e in group_sorted if e.content]
    
    x0 = min(e.bbox.x0 for e in group_sorted)
    y0 = min(e.bbox.y0 for e in group_sorted)
    x1 = max(e.bbox.x1 for e in group_sorted)
    y1 = max(e.bbox.y1 for e in group_sorted)
    bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
    
    font_sizes = [e.font_size for e in group_sorted if e.font_size]
    avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else 10.0
    
    fonts = [e.font_name for e in group_sorted if e.font_name]
    dom_font = max(set(fonts), key=fonts.count) if fonts else None
    
    is_bold = any(e.is_bold for e in group_sorted)
    is_italic = any(e.is_italic for e in group_sorted)
    
    return LineBlock(
        line_id=str(uuid.uuid4()),
        page=page,
        bbox=bbox,
        elements=group_sorted,
        text=" ".join(texts),
        avg_font_size=avg_font,
        dominant_font=dom_font,
        is_bold=is_bold,
        is_italic=is_italic,
        indent_level=x0,
        line_spacing_above=0.0
    )


def _assemble_paragraphs(lines: list[LineBlock], page: int) -> list[ParagraphBlock]:
    lines_sorted = sorted(lines, key=lambda l: l.bbox.y0)
    paragraphs: list[ParagraphBlock] = []
    current_para: list[LineBlock] = []
    
    for line in lines_sorted:
        if not current_para:
            current_para.append(line)
            continue
            
        last = current_para[-1]
        gap = line.bbox.y0 - last.bbox.y1
        avg_height = (last.bbox.height + line.bbox.height) / 2.0
        
        # Check gap and left margin alignment
        if gap < 1.8 * avg_height and abs(line.bbox.x0 - last.bbox.x0) < 35.0:
            current_para.append(line)
        else:
            paragraphs.append(_create_paragraph(current_para, page))
            current_para = [line]
            
    if current_para:
        paragraphs.append(_create_paragraph(current_para, page))
        
    return paragraphs


def _create_paragraph(lines: list[LineBlock], page: int) -> ParagraphBlock:
    x0 = min(l.bbox.x0 for l in lines)
    y0 = min(l.bbox.y0 for l in lines)
    x1 = max(l.bbox.x1 for l in lines)
    y1 = max(l.bbox.y1 for l in lines)
    bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
    text = "\n".join([l.text for l in lines])
    
    return ParagraphBlock(
        paragraph_id=str(uuid.uuid4()),
        page=page,
        bbox=bbox,
        lines=lines,
        text=text,
        block_type=BlockType.TEXT,
        column=0
    )


def _classify_paragraphs(paragraphs: list[ParagraphBlock]):
    for para in paragraphs:
        if "table" in para.text.lower() and "|" in para.text:
            para.block_type = BlockType.TABLE
        else:
            para.block_type = BlockType.TEXT
