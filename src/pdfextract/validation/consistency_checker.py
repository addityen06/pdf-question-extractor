from __future__ import annotations

import logging
from typing import Dict, List

from pdfextract.core.models import Question

logger = logging.getLogger(__name__)

def check_course_consistency(papers: Dict[str, List[Question]]) -> List[str]:
    warnings = []
    logger.info(f"Checking consistency for {len(papers)} papers")
    
    # Stub logic for Q counts
    q_counts = {p: len(qs) for p, qs in papers.items()}
    if q_counts:
        avg_q = sum(q_counts.values()) / len(q_counts)
        for p, c in q_counts.items():
            if abs(c - avg_q) > 5:
                warnings.append(f"Paper {p} has {c} questions, average is {avg_q:.1f}")
                
    return warnings
