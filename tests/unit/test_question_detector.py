"""
Unit tests for the question detection module.
"""
from __future__ import annotations

import pytest
from questionai.content.question_detector import (
    detect_questions,
    _extract_question_number,
    _extract_marks,
    _is_subquestion_start,
)
from questionai.core.models import ParagraphBlock, LineBlock, BoundingBox, BlockType


def _make_paragraph(text: str, x0: float = 72.0, y0: float = 100.0, page: int = 1) -> ParagraphBlock:
    """Helper to create a minimal ParagraphBlock with a single line."""
    bbox = BoundingBox(x0=x0, y0=y0, x1=x0 + 400.0, y1=y0 + 12.0)
    line = LineBlock(
        line_id="l1",
        page=page,
        bbox=bbox,
        text=text,
        avg_font_size=10.0,
        is_bold=False,
        line_spacing_above=0.0,
    )
    return ParagraphBlock(
        paragraph_id="p1",
        page=page,
        bbox=bbox,
        lines=[line],
        text=text,
        block_type=BlockType.TEXT,
    )


class TestExtractQuestionNumber:
    def test_dotted_format(self):
        assert _extract_question_number("1. Define recursion.") == 1

    def test_paren_format(self):
        assert _extract_question_number("2) What is polymorphism?") == 2

    def test_q_prefix(self):
        assert _extract_question_number("Q.3 Explain stacks.") == 3

    def test_question_word(self):
        assert _extract_question_number("Question 4: Describe the OSI model.") == 4

    def test_no_match(self):
        assert _extract_question_number("This is not a question start.") is None

    def test_two_digit(self):
        assert _extract_question_number("10. Final question.") == 10


class TestExtractMarks:
    def test_bracket_format(self):
        assert _extract_marks("Explain the process [10]") == 10

    def test_marks_word(self):
        assert _extract_marks("State the theorem (5 marks)") == 5

    def test_M_format(self):
        assert _extract_marks("Solve (3M)") == 3

    def test_no_marks(self):
        assert _extract_marks("No marks indicated here") is None


class TestIsSubquestion:
    def test_paren_a(self):
        is_sub, label, parent = _is_subquestion_start("(a) Define abstraction.")
        assert is_sub is True
        assert label == "a"

    def test_standalone_b_paren(self):
        is_sub, label, parent = _is_subquestion_start("b) List the advantages.")
        assert is_sub is True
        assert label == "b"

    def test_roman_numeral(self):
        is_sub, label, parent = _is_subquestion_start("(i) First part.")
        assert is_sub is True
        assert label == "i"

    def test_not_subquestion(self):
        is_sub, label, parent = _is_subquestion_start("1. Main question here.")
        assert is_sub is False


class TestDetectQuestions:
    def test_basic_detection(self):
        paragraphs = [
            _make_paragraph("1. What is a linked list? [10]", y0=100.0),
            _make_paragraph("It is a linear data structure.", y0=115.0),
            _make_paragraph("2. Explain binary trees. [10]", y0=200.0),
        ]
        # Give the second question enough gap to score on vertical gap signal
        paragraphs[2].lines[0].line_spacing_above = 30.0
        candidates = detect_questions(paragraphs)
        main_qs = [c for c in candidates if not c.is_subquestion]
        assert len(main_qs) == 2
        assert main_qs[0].question_number == 1
        assert main_qs[1].question_number == 2

    def test_empty_paragraphs(self):
        assert detect_questions([]) == []

    def test_marks_extracted(self):
        paragraphs = [
            _make_paragraph("1. Describe recursion. [15]", y0=100.0),
        ]
        candidates = detect_questions(paragraphs)
        main_qs = [c for c in candidates if not c.is_subquestion]
        if main_qs:
            assert main_qs[0].marks == 15
