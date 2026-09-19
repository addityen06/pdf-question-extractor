from __future__ import annotations

import logging
import re
from pdfextract.core.models import ParagraphBlock, ContentBlock, BlockType
from pdfextract.core.constants import CODE_KEYWORDS, ALL_CODE_KEYWORDS, MONOSPACE_FONTS, CODE_SYNTAX_CHARS

logger = logging.getLogger(__name__)


def detect_code_blocks(paragraphs: list[ParagraphBlock]) -> list[tuple[list[int], ContentBlock]]:
    """
    Detect programming code blocks and preserve them accurately.
    """
    detected: list[tuple[list[int], ContentBlock]] = []
    i = 0
    
    while i < len(paragraphs):
        para = paragraphs[i]
        text = para.text or ""
        
        # Check if monospace font
        is_mono = False
        if hasattr(para, 'lines'):
            for line in para.lines:
                if line.dominant_font:
                    font_lower = line.dominant_font.lower()
                    if any(mf in font_lower for mf in MONOSPACE_FONTS):
                        is_mono = True
                        break
                        
        # Check programming keywords
        detected_lang = None
        keyword_matches = 0
        
        for lang, kws in CODE_KEYWORDS.items():
            lang_matches = sum(1 for kw in kws if kw in text or re.search(r'\b' + re.escape(kw) + r'\b', text))
            if lang_matches > keyword_matches:
                keyword_matches = lang_matches
                detected_lang = lang
                
        # Count code syntax characters
        syntax_count = sum(text.count(char) for char in "{}[];->==!=&&||#")
        
        score = 0
        if is_mono:
            score += 3
        if keyword_matches >= 2:
            score += 3
        elif keyword_matches == 1:
            score += 1
        if syntax_count >= 3:
            score += 2
        elif syntax_count >= 1:
            score += 1
            
        if score >= 3:
            code_paras = [i]
            code_lines = [text]
            
            # Look ahead for continuing code lines
            j = i + 1
            while j < len(paragraphs):
                next_text = paragraphs[j].text or ""
                next_score = 0
                
                # Check next paragraph for syntax or indentation
                if sum(next_text.count(c) for c in "{}[];->==!=&&||#") >= 1:
                    next_score += 1
                if any(kw in next_text for kw in (CODE_KEYWORDS.get(detected_lang, []) if detected_lang else ALL_CODE_KEYWORDS)):
                    next_score += 2
                if next_text.startswith("    ") or next_text.startswith("\t") or next_text.strip().endswith(";"):
                    next_score += 1
                    
                if next_score >= 1 and len(next_text.splitlines()) <= 5:
                    code_paras.append(j)
                    code_lines.append(next_text)
                    j += 1
                else:
                    break
                    
            content = "\n".join(code_lines)
            block = ContentBlock(
                type=BlockType.CODE,
                content=content,
                language=detected_lang or "c",
                confidence=0.85,
                source_page=para.page,
                source_bbox=para.bbox
            )
            detected.append((code_paras, block))
            i = j
        else:
            i += 1
            
    return detected
