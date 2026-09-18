from __future__ import annotations

import logging
import re
from typing import List, Any

from questionai.core.models import Question, ExtractionReport, ValidationResult, ValidationCheck
from questionai.core.constants import ADMIN_KEYWORDS
from questionai.core.config import ValidationConfig

logger = logging.getLogger(__name__)


def validate_paper(
    questions: List[Question],
    report: ExtractionReport,
    config: ValidationConfig | Any | None = None
) -> ValidationResult:
    """
    Run comprehensive validation checks on extracted questions for a paper.
    """
    logger.info(f"Validating paper {report.paper_file} ({len(questions)} questions)")
    
    checks: list[ValidationCheck] = []
    
    # ── V1: Sequential Question Numbering ─────────────────────────────────
    main_qs = [q for q in questions if not q.subquestion]
    if main_qs:
        q_nums = [q.question_number for q in main_qs]
        sorted_nums = sorted(q_nums)
        expected_range = list(range(sorted_nums[0], sorted_nums[-1] + 1))
        missing_nums = set(expected_range) - set(sorted_nums)
        
        if not missing_nums:
            checks.append(ValidationCheck(
                check_id="V1",
                check_name="Sequential Question Numbering",
                status="PASS",
                detail=f"Question sequence {sorted_nums[0]} to {sorted_nums[-1]} is complete.",
                severity="INFO"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="V1",
                check_name="Sequential Question Numbering",
                status="WARNING",
                detail=f"Missing question numbers in sequence: {sorted(missing_nums)}",
                severity="WARNING"
            ))
    else:
        checks.append(ValidationCheck(
            check_id="V1",
            check_name="Sequential Question Numbering",
            status="WARNING",
            detail="No main questions detected to validate sequence.",
            severity="WARNING"
        ))
        
    # ── V2: Valid Subquestions ────────────────────────────────────────────
    sub_qs = [q for q in questions if q.subquestion]
    invalid_subs = [q.subquestion for q in sub_qs if q.subquestion and len(q.subquestion) > 3]
    if not invalid_subs:
        checks.append(ValidationCheck(
            check_id="V2",
            check_name="Valid Subquestion Labels",
            status="PASS",
            detail=f"All {len(sub_qs)} subquestion labels are valid.",
            severity="INFO"
        ))
    else:
        checks.append(ValidationCheck(
            check_id="V2",
            check_name="Valid Subquestion Labels",
            status="WARNING",
            detail=f"Unusual subquestion labels found: {invalid_subs}",
            severity="WARNING"
        ))
        
    # ── V3: Marks Sum Match ───────────────────────────────────────────────
    total_extracted_marks = sum(q.marks or 0 for q in questions if not q.subquestion)
    stated_max = report.stated_max_marks
    if stated_max and total_extracted_marks > 0:
        tolerance = getattr(config, 'marks_tolerance_percent', 10.0) if config else 10.0
        allowed_diff = stated_max * (tolerance / 100.0)
        diff = abs(total_extracted_marks - stated_max)
        
        if diff <= allowed_diff:
            checks.append(ValidationCheck(
                check_id="V3",
                check_name="Marks Summation Match",
                status="PASS",
                detail=f"Extracted total marks ({total_extracted_marks}) matches stated max ({stated_max}).",
                severity="INFO"
            ))
        else:
            checks.append(ValidationCheck(
                check_id="V3",
                check_name="Marks Summation Match",
                status="WARNING",
                detail=f"Extracted total marks ({total_extracted_marks}) differs from stated max ({stated_max}).",
                severity="WARNING"
            ))
    else:
        checks.append(ValidationCheck(
            check_id="V3",
            check_name="Marks Summation Match",
            status="SKIP",
            detail="Stated max marks not found in header or no question marks detected.",
            severity="INFO"
        ))
        
    # ── V4: Short Questions ───────────────────────────────────────────────
    min_len = getattr(config, 'min_question_length', 10) if config else 10
    short_qs = [q.question_id for q in questions if len(q.question_text.strip()) < min_len]
    if not short_qs:
        checks.append(ValidationCheck(
            check_id="V4",
            check_name="Question Content Length",
            status="PASS",
            detail="All questions have sufficient text length.",
            severity="INFO"
        ))
    else:
        checks.append(ValidationCheck(
            check_id="V4",
            check_name="Question Content Length",
            status="WARNING",
            detail=f"Found {len(short_qs)} suspiciously short questions: {short_qs}",
            severity="WARNING"
        ))
        
    # ── V5: Administrative Content Residuals ──────────────────────────────
    admin_residual_qs = []
    for q in questions:
        q_text_lower = q.question_text.lower()
        if "vellore institute of technology" in q_text_lower or "keeping mobile phone" in q_text_lower or "exam malpractice" in q_text_lower:
            admin_residual_qs.append(q.question_id)
            
    if not admin_residual_qs:
        checks.append(ValidationCheck(
            check_id="V5",
            check_name="Admin Residual Removal",
            status="PASS",
            detail="No administrative boilerplates found in question text.",
            severity="INFO"
        ))
    else:
        checks.append(ValidationCheck(
            check_id="V5",
            check_name="Admin Residual Removal",
            status="WARNING",
            detail=f"Administrative text detected inside questions: {admin_residual_qs}",
            severity="WARNING"
        ))
        
    # ── V6: Bracket Balance in Equations/Code ──────────────────────────────
    unbalanced_qs = []
    for q in questions:
        txt = q.question_text
        if txt.count('(') != txt.count(')') or txt.count('{') != txt.count('}'):
            # Only flag if there are multiple brackets
            if txt.count('(') + txt.count('{') >= 2:
                unbalanced_qs.append(q.question_id)
                
    if not unbalanced_qs:
        checks.append(ValidationCheck(
            check_id="V6",
            check_name="Bracket Balance",
            status="PASS",
            detail="Brackets and braces are well balanced.",
            severity="INFO"
        ))
    else:
        checks.append(ValidationCheck(
            check_id="V6",
            check_name="Bracket Balance",
            status="INFO",
            detail=f"{len(unbalanced_qs)} questions have potential bracket asymmetry.",
            severity="INFO"
        ))
        
    # Aggregate results
    error_count = sum(1 for c in checks if c.status == "FAIL")
    warning_count = sum(1 for c in checks if c.status == "WARNING")
    
    overall_status = "PASS"
    if error_count > 0:
        overall_status = "FAILED"
    elif warning_count > 0:
        overall_status = "WARNING"
        
    return ValidationResult(
        paper_file=report.paper_file,
        course_code=report.course_code,
        validation_passed=(error_count == 0),
        checks=checks,
        warning_count=warning_count,
        error_count=error_count,
        overall_status=overall_status
    )
