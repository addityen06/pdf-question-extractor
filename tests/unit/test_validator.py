"""
Unit tests for the validator.
"""
from __future__ import annotations

import pytest
from questionai.core.models import (
    Question,
    ContentBlock,
    BlockType,
    ExtractionReport,
    VerificationStatus,
)
from questionai.validation.validator import validate_paper


def _make_question(n: int, text: str, marks: int = 10, subq: str | None = None) -> Question:
    return Question(
        question_id=f"TEST101_CAT-1_Q{n}",
        course_code="TEST101",
        paper_file="test.pdf",
        exam_type="CAT-1",
        question_number=n,
        subquestion=subq,
        marks=marks,
        question_text=text,
        blocks=[ContentBlock(type=BlockType.TEXT, content=text)],
    )


def _make_report(stated_max: int | None = None) -> ExtractionReport:
    return ExtractionReport(
        paper_file="test.pdf",
        course_code="TEST101",
        stated_max_marks=stated_max,
    )


class TestValidatePaper:
    def test_sequential_pass(self):
        questions = [_make_question(i, f"Question {i} text here.") for i in range(1, 6)]
        report = _make_report()
        result = validate_paper(questions, report)
        v1 = next(c for c in result.checks if c.check_id == "V1")
        assert v1.status == "PASS"

    def test_sequential_missing_number(self):
        questions = [
            _make_question(1, "Question 1 text here."),
            _make_question(3, "Question 3 text here."),  # 2 is missing
        ]
        report = _make_report()
        result = validate_paper(questions, report)
        v1 = next(c for c in result.checks if c.check_id == "V1")
        assert v1.status == "WARNING"

    def test_marks_match_pass(self):
        questions = [_make_question(i, f"Q{i} text.", marks=10) for i in range(1, 6)]
        report = _make_report(stated_max=50)
        result = validate_paper(questions, report)
        v3 = next(c for c in result.checks if c.check_id == "V3")
        assert v3.status == "PASS"

    def test_marks_mismatch_warning(self):
        questions = [_make_question(1, "Q1 text.", marks=10)]
        report = _make_report(stated_max=100)
        result = validate_paper(questions, report)
        v3 = next(c for c in result.checks if c.check_id == "V3")
        assert v3.status == "WARNING"

    def test_short_question_warning(self):
        questions = [_make_question(1, "Hi")]  # too short
        report = _make_report()
        result = validate_paper(questions, report)
        v4 = next(c for c in result.checks if c.check_id == "V4")
        assert v4.status == "WARNING"

    def test_admin_residual_warning(self):
        questions = [
            _make_question(1, "vellore institute of technology some question text here")
        ]
        report = _make_report()
        result = validate_paper(questions, report)
        v5 = next(c for c in result.checks if c.check_id == "V5")
        assert v5.status == "WARNING"
