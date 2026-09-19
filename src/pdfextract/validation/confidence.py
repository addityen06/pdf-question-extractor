from __future__ import annotations

import logging
from typing import List, Any

from pdfextract.core.models import Question, ValidationResult, ConfidenceTier, VerificationStatus
from pdfextract.core.config import ConfidenceConfig

logger = logging.getLogger(__name__)


def compute_question_confidence(
    question: Question,
    detection_score: float,
    validation_result: ValidationResult,
    config: ConfidenceConfig | None = None
) -> float:
    """
    Compute composite confidence score (0.0 to 1.0) for a question.
    """
    weights = getattr(config, 'weights', {
        "ocr_confidence": 0.30,
        "question_number": 0.15,
        "marks_detection": 0.10,
        "boundary_confidence": 0.20,
        "content_completeness": 0.15,
        "validation_checks": 0.10,
    }) if config else {
        "ocr_confidence": 0.30,
        "question_number": 0.15,
        "marks_detection": 0.10,
        "boundary_confidence": 0.20,
        "content_completeness": 0.15,
        "validation_checks": 0.10,
    }
    
    # 1. OCR / Native confidence
    ocr_conf = 1.0
    if question.blocks:
        conf_list = [b.confidence for b in question.blocks if b.confidence is not None]
        if conf_list:
            ocr_conf = sum(conf_list) / len(conf_list)
            
    # 2. Question number confidence
    qnum_conf = min(1.0, max(0.4, detection_score / 3.0))
    
    # 3. Marks detection confidence
    marks_conf = 1.0 if question.marks is not None else 0.5
    
    # 4. Boundary clarity
    boundary_conf = 0.9 if question.question_text and len(question.question_text) > 20 else 0.5
    
    # 5. Content completeness
    completeness_conf = 1.0 if not question.question_text.endswith(("-", "...")) else 0.6
    
    # 6. Validation check pass rate
    val_conf = 1.0 if validation_result.error_count == 0 else 0.5
    
    score = (
        weights.get("ocr_confidence", 0.3) * ocr_conf +
        weights.get("question_number", 0.15) * qnum_conf +
        weights.get("marks_detection", 0.10) * marks_conf +
        weights.get("boundary_confidence", 0.20) * boundary_conf +
        weights.get("content_completeness", 0.15) * completeness_conf +
        weights.get("validation_checks", 0.10) * val_conf
    )
    
    return float(min(1.0, max(0.0, score)))


def compute_paper_confidence(questions: List[Question]) -> float:
    if not questions:
        return 0.0
    return float(sum(q.extraction_confidence or 0.0 for q in questions) / len(questions))


def assign_confidence_tier(score: float, config: ConfidenceConfig | None = None) -> ConfidenceTier:
    high_th = getattr(config, 'tier_high', 0.90) if config else 0.90
    med_th = getattr(config, 'tier_medium', 0.70) if config else 0.70
    low_th = getattr(config, 'tier_low', 0.50) if config else 0.50
    
    if score >= high_th:
        return ConfidenceTier.HIGH
    elif score >= med_th:
        return ConfidenceTier.MEDIUM
    elif score >= low_th:
        return ConfidenceTier.LOW
    return ConfidenceTier.VERY_LOW


def assign_verification_status(tier: ConfidenceTier) -> VerificationStatus:
    if tier == ConfidenceTier.HIGH:
        return VerificationStatus.AUTO_EXTRACTED
    elif tier == ConfidenceTier.MEDIUM:
        return VerificationStatus.REVIEW_RECOMMENDED
    elif tier == ConfidenceTier.LOW:
        return VerificationStatus.REVIEW_REQUIRED
    return VerificationStatus.REVIEW_REQUIRED
