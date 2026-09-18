"""
Unit tests for the CSV writer.
"""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest
from questionai.core.models import Question, ContentBlock, BlockType, VerificationStatus
from questionai.output.csv_writer import write_paper_csv


def _make_question(n: int, text: str, marks: int = 10) -> Question:
    return Question(
        question_id=f"TEST101_CAT-1_Q{n}",
        course_code="TEST101",
        paper_file="test.pdf",
        exam_type="CAT-1",
        academic_year="2024-2025",
        semester="Fall_Semester",
        question_number=n,
        marks=marks,
        question_text=text,
        blocks=[ContentBlock(type=BlockType.TEXT, content=text)],
        extraction_confidence=0.92,
        verification_status=VerificationStatus.AUTO_EXTRACTED,
    )


class TestWritePaperCsv:
    def test_creates_file(self):
        questions = [_make_question(1, "What is a stack?")]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "COURSE" / "paper.csv"
            write_paper_csv(
                questions=questions,
                target_csv_path=target,
                course_code="TEST101",
                paper_file="test.pdf",
            )
            assert target.exists()

    def test_row_count(self):
        questions = [
            _make_question(1, "Question one text."),
            _make_question(2, "Question two text."),
            _make_question(3, "Question three text."),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "COURSE" / "paper.csv"
            write_paper_csv(
                questions=questions,
                target_csv_path=target,
                course_code="TEST101",
                paper_file="test.pdf",
            )
            with open(target, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            # 1 header + 3 data rows
            assert len(rows) == 4

    def test_separator_appended(self):
        questions = [_make_question(1, "Explain recursion.")]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "COURSE" / "paper.csv"
            write_paper_csv(
                questions=questions,
                target_csv_path=target,
                course_code="TEST101",
                paper_file="test.pdf",
            )
            with open(target, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            question_text_col = rows[0].index("question_text")
            text_value = rows[1][question_text_col]
            assert "<<<QUESTION_END>>>" in text_value

    def test_sort_order(self):
        questions = [
            _make_question(3, "Third question."),
            _make_question(1, "First question."),
            _make_question(2, "Second question."),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "COURSE" / "paper.csv"
            write_paper_csv(
                questions=questions,
                target_csv_path=target,
                course_code="TEST101",
                paper_file="test.pdf",
            )
            with open(target, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            nums = [int(rows[i][0]) for i in range(1, len(rows))]
            assert nums == sorted(nums)
