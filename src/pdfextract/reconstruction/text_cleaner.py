from __future__ import annotations

import logging
import re
from typing import Any

from pdfextract.core.models import Question, BlockType

logger = logging.getLogger(__name__)

class CleaningConfig:
    pass

def clean_text(text: str, config: Any) -> str:
    """
    Clean text conservatively.
    """
    if not text:
        return text
    
    # Duplicate whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Normalize quotes/dashes
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('—', '--')
    
    # OCR errors (very conservative)
    text = re.sub(r'\b(l)\b', '1', text) # naive example, would need regex context
    text = re.sub(r'\b(O)\b', '0', text)
    
    # Trim lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    
    return "\n".join(lines)

def clean_element_text(text: str, block_type: BlockType, config: Any) -> str:
    if block_type in (BlockType.CODE, BlockType.EQUATION):
        return text
    return clean_text(text, config)

def clean_question(question: Question, config: Any) -> Question:
    try:
        new_blocks = []
        for b in question.blocks:
            b.content = clean_element_text(b.content, b.type, config)
            new_blocks.append(b)
        question.blocks = new_blocks
        question.question_text = clean_text(question.question_text, config)
    except Exception as e:
        logger.warning(f"Error cleaning question {question.question_id}: {e}")
    return question
