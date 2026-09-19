"""
Unit tests for filename parsing and course code extraction.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from pdfextract.ingestion.directory_scanner import (
    extract_course_code,
    parse_paper_filename,
)


class TestExtractCourseCode:
    def test_plain_code(self):
        assert extract_course_code("BACSE104") == "BACSE104"

    def test_bracketed_code(self):
        result = extract_course_code(
            "Electric_Vehicle_Instrumentation_and_Data_Analytics_[BAMEE344]"
        )
        assert result == "BAMEE344"

    def test_whitespace_in_bracket(self):
        assert extract_course_code("Some_Subject_[ CODE123 ]") == "CODE123"

    def test_no_bracket(self):
        assert extract_course_code("BMAT101L") == "BMAT101L"


class TestParsePaperFilename:
    def _path(self, name: str) -> Path:
        return Path(f"/papers/BACSE104/{name}")

    def test_standard_cat1(self):
        meta = parse_paper_filename(
            self._path("CAT-1_2024-2025_Fall_Semester_D1_Vellore_85f84318.pdf"),
            "BACSE104",
        )
        assert meta.exam_type == "CAT-1"
        assert meta.academic_year == "2024-2025"
        assert meta.semester == "Fall_Semester"
        assert meta.slot == "D1"
        assert meta.campus == "Vellore"
        assert meta.is_answer_key is False
        assert meta.course_code == "BACSE104"

    def test_answer_key_detection(self):
        meta = parse_paper_filename(
            self._path("FAT_2024-2025_Winter_Semester_A1_Vellore_AnsKey_a03f5dc7.pdf"),
            "BACSE104",
        )
        assert meta.is_answer_key is True
        assert meta.exam_type == "FAT"

    def test_non_standard_filename(self):
        meta = parse_paper_filename(
            self._path("unknown_paper.pdf"),
            "BACSE104",
        )
        assert meta.course_code == "BACSE104"
        assert len(meta.parse_warnings) > 0
