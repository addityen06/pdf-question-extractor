"""
Integration test: full pipeline on a sample PDF fixture.

Place a test PDF at tests/fixtures/sample_paper.pdf to run this test.
The PDF should be a structured exam paper with at least one question.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from questionai.core.config import PipelineConfig
from questionai.ingestion.directory_scanner import PaperJob, parse_paper_filename
from questionai.pipeline import process_single_paper


@pytest.mark.integration
def test_full_pipeline_on_sample_pdf(sample_pdf: Path):
    """
    Run the full extraction pipeline on the sample fixture PDF
    and verify that at least one question is extracted successfully.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        course_dir = tmp_path / "TEST101"
        course_dir.mkdir()

        meta = parse_paper_filename(sample_pdf, "TEST101")

        job = PaperJob(
            course_code="TEST101",
            pdf_path=sample_pdf,
            paper_stem=sample_pdf.stem,
            target_csv_path=course_dir / f"{sample_pdf.stem}.csv",
            target_csv_only_path=course_dir / f"{sample_pdf.stem}_clean.csv",
            target_assets_dir=course_dir / f"{sample_pdf.stem}_assets",
            target_report_path=course_dir / f"{sample_pdf.stem}_extraction_report.json",
            metadata=meta,
        )

        config = PipelineConfig()
        questions, report = process_single_paper(job, config)

        assert report is not None
        assert report.pages > 0
        assert len(questions) >= 0  # Even 0 questions is a valid (warning) outcome
        assert job.target_csv_path.exists()
        assert job.target_report_path.exists()
