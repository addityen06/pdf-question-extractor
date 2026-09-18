from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from questionai.core.models import ParagraphBlock, Question
from questionai.core.constants import SUBQUESTION_PATTERNS, OR_PATTERN
from questionai.content.question_detector import QuestionCandidate

logger = logging.getLogger(__name__)

@dataclass
class SubquestionCandidate:
    subquestion_label: str
    parent_question: Any
    marks: int | None
    content_paragraphs: list[ParagraphBlock]
    choice_group: str | None

def detect_subquestions(candidate: QuestionCandidate, config: Any) -> list[SubquestionCandidate]:
    """
    Detect subquestions within question boundaries.
    """
    subquestions = []
    current_label = None
    current_paragraphs = []
    current_choice_group = None
    
    for para in candidate.content_paragraphs:
        is_subquestion = False
        text = para.text or ""
        
        # Check for OR choice
        if re.search(OR_PATTERN, text, re.IGNORECASE):
            if not current_choice_group:
                current_choice_group = "group_1"
            continue
            
        for pattern in SUBQUESTION_PATTERNS:
            match = re.match(pattern, text.strip())
            if match:
                if current_label and current_paragraphs:
                    subquestions.append(SubquestionCandidate(
                        subquestion_label=current_label,
                        parent_question=candidate,
                        marks=None,
                        content_paragraphs=current_paragraphs,
                        choice_group=current_choice_group
                    ))
                current_label = match.group(1) if match.groups() else text.strip()[0]
                current_paragraphs = [para]
                is_subquestion = True
                break
                
        if not is_subquestion and current_label:
            current_paragraphs.append(para)
            
    if current_label and current_paragraphs:
        subquestions.append(SubquestionCandidate(
            subquestion_label=current_label,
            parent_question=candidate,
            marks=None,
            content_paragraphs=current_paragraphs,
            choice_group=current_choice_group
        ))
        
    return subquestions
