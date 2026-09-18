"""
Unit tests for core data models.
"""
from __future__ import annotations

import pytest
from questionai.core.models import (
    BoundingBox,
    ElementBlock,
    ParagraphBlock,
    LineBlock,
    Question,
    ExtractionReport,
    BlockType,
    ExtractionSource,
    ProcessingStatus,
    VerificationStatus,
)


class TestBoundingBox:
    def test_dimensions(self):
        bbox = BoundingBox(x0=10.0, y0=20.0, x1=110.0, y1=70.0)
        assert bbox.width == 100.0
        assert bbox.height == 50.0
        assert bbox.area == 5000.0

    def test_center(self):
        bbox = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=50.0)
        assert bbox.center_x == 50.0
        assert bbox.center_y == 25.0

    def test_overlaps_true(self):
        a = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=50.0)
        b = BoundingBox(x0=50.0, y0=25.0, x1=150.0, y1=75.0)
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_overlaps_false(self):
        a = BoundingBox(x0=0.0, y0=0.0, x1=50.0, y1=50.0)
        b = BoundingBox(x0=100.0, y0=0.0, x1=200.0, y1=50.0)
        assert not a.overlaps(b)

    def test_merge(self):
        a = BoundingBox(x0=0.0, y0=0.0, x1=50.0, y1=50.0)
        b = BoundingBox(x0=25.0, y0=25.0, x1=100.0, y1=100.0)
        merged = a.merge(b)
        assert merged.x0 == 0.0
        assert merged.y0 == 0.0
        assert merged.x1 == 100.0
        assert merged.y1 == 100.0

    def test_vertical_overlap_ratio(self):
        a = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=20.0)
        b = BoundingBox(x0=0.0, y0=10.0, x1=100.0, y1=30.0)
        ratio = a.vertical_overlap_ratio(b)
        # overlap is 10, min height is 20, ratio = 0.5
        assert ratio == pytest.approx(0.5)

    def test_zero_area_overlap(self):
        a = BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0)
        b = BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0)
        assert a.vertical_overlap_ratio(b) == 0.0


class TestExtractionReport:
    def test_defaults(self):
        report = ExtractionReport(paper_file="test.pdf", course_code="TEST101")
        assert report.processing_status == ProcessingStatus.SUCCESS
        assert report.pages == 0
        assert report.questions_detected == 0
        assert report.ocr_used is False

    def test_status_values(self):
        for status in ProcessingStatus:
            report = ExtractionReport(
                paper_file="test.pdf",
                course_code="TEST101",
                processing_status=status,
            )
            assert report.processing_status == status


class TestQuestion:
    def test_defaults(self):
        q = Question(
            question_id="TEST101_CAT-1_Q1",
            course_code="TEST101",
            paper_file="test.pdf",
            question_number=1,
        )
        assert q.subquestion is None
        assert q.marks is None
        assert q.verification_status == VerificationStatus.AUTO_EXTRACTED
        assert q.extraction_confidence == 1.0
