from __future__ import annotations

import logging
import re
from questionai.core.models import ParagraphBlock, ElementBlock, ContentBlock, BlockType

logger = logging.getLogger(__name__)


def detect_tables(
    paragraphs: list[ParagraphBlock],
    elements: list[ElementBlock]
) -> list[tuple[list[int], ContentBlock]]:
    """
    Detect tabular content in paragraphs and represent as structured Markdown and row arrays.
    """
    detected: list[tuple[list[int], ContentBlock]] = []
    i = 0
    
    while i < len(paragraphs):
        para = paragraphs[i]
        text = (para.text or "").strip()
        
        # Check if text looks like a table row (contains multiple pipes, tabs, or aligned column headers)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        is_table = False
        parsed_rows: list[list[str]] = []
        
        # 1. Pipe-separated tables
        if any(l.count('|') >= 2 for l in lines):
            is_table = True
            for l in lines:
                cells = [c.strip() for c in l.split('|') if c.strip()]
                if cells:
                    parsed_rows.append(cells)
                    
        # 2. Multi-column key headers (e.g. S.No. Question Marks CO BL)
        elif len(lines) >= 2 and any('s.no' in l.lower() or 'list -1' in l.lower() for l in lines):
            is_table = True
            for l in lines:
                parts = re.split(r'\s{2,}|\t', l)
                parsed_rows.append([p.strip() for p in parts if p.strip()])
                
        if is_table and parsed_rows:
            table_paras = [i]
            
            # Format markdown table
            max_cols = max(len(r) for r in parsed_rows)
            # Pad rows
            for r in parsed_rows:
                while len(r) < max_cols:
                    r.append("")
                    
            md_lines = []
            for ri, r in enumerate(parsed_rows):
                md_lines.append("| " + " | ".join(r) + " |")
                if ri == 0:
                    md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
                    
            md_table = "\n".join(md_lines)
            
            block = ContentBlock(
                type=BlockType.TABLE,
                content=md_table,
                rows=parsed_rows,
                confidence=0.85,
                source_page=para.page,
                source_bbox=para.bbox
            )
            detected.append((table_paras, block))
            i += 1
        else:
            i += 1
            
    return detected
