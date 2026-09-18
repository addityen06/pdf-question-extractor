"""
QuestionAI — Stage A Extraction Pipeline
==========================================
Deterministic, verified examination-paper extraction pipeline.

Enforces:
1. ONE PDF Paper -> ONE CSV in textPapers/<course_code>/<paper_stem>.csv
2. Clean CSV-Only Folder in textPapersCSV/<course_code>/<paper_stem>.csv
3. Explicit Programmatic Question Separator (<<<QUESTION_END>>>)
4. Multi-Signal Local Extraction (PyMuPDF / Apple Vision OCR / Blocks)
5. Full Verification Status Tiers (auto_extracted, review_recommended, review_required)
6. Resumable Batch Processing & Complete Paper Isolation
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from questionai.core.config import PipelineConfig
from questionai.core.constants import VERSION
from questionai.core.models import (
    PaperMetadata, PDFPageType, ElementBlock, ParagraphBlock,
    ContentBlock, Question, ExtractionReport, ProcessingStatus,
    ExtractionSource, VerificationStatus
)
from questionai.ingestion.directory_scanner import PaperJob, discover_paper_jobs
from questionai.pdf.pdf_classifier import classify_pdf
from questionai.pdf.pdf_loader import load_pdf
from questionai.pdf.text_extractor import extract_native_text
from questionai.pdf.page_renderer import render_page
from questionai.ocr.image_preprocessor import preprocess_image
from questionai.ocr.ocr_engine import ocr_page
from questionai.ocr.ocr_postprocessor import postprocess_ocr_results
from questionai.layout.layout_analyzer import analyze_layout
from questionai.layout.reading_order import order_paragraphs
from questionai.layout.header_footer_detector import detect_and_remove_admin
from questionai.content.question_detector import detect_questions
from questionai.content.equation_detector import detect_equations
from questionai.content.table_detector import detect_tables
from questionai.content.code_detector import detect_code_blocks
from questionai.content.figure_detector import detect_figures
from questionai.reconstruction.question_reconstructor import reconstruct_questions
from questionai.reconstruction.text_cleaner import clean_question
from questionai.validation.validator import validate_paper
from questionai.validation.confidence import (
    compute_question_confidence, compute_paper_confidence,
    assign_confidence_tier, assign_verification_status
)
from questionai.output.csv_writer import write_paper_csv
from questionai.output.report_generator import write_paper_report, write_batch_summary, print_batch_summary

logger = logging.getLogger(__name__)


def process_single_paper(
    job: PaperJob,
    config: PipelineConfig,
    force: bool = False
) -> tuple[list[Question], ExtractionReport]:
    """
    Process an individual PDF paper independently and generate its CSV and report.
    Writes:
      - textPapers/<course_code>/<paper_stem>.csv (along with assets, reports, raw json)
      - textPapersCSV/<course_code>/<paper_stem>.csv (CSV-only clean mirror)
    """
    t0 = time.time()
    pdf_path = job.pdf_path
    meta = job.metadata

    # Resumability check
    if not force and job.target_csv_path.exists() and job.target_report_path.exists():
        try:
            report_data = json.loads(job.target_report_path.read_text(encoding="utf-8"))
            if report_data.get("processing_status") == ProcessingStatus.SUCCESS.value:
                logger.info(f"Skipping already verified paper: {meta.file_name}")
                report = ExtractionReport(**report_data)
                return [], report
        except Exception:
            pass

    report = ExtractionReport(
        paper_file=meta.file_name,
        course_code=meta.course_code,
        exam_type=meta.exam_type.value if hasattr(meta.exam_type, 'value') else str(meta.exam_type),
        academic_year=meta.academic_year,
        semester=meta.semester.value if hasattr(meta.semester, 'value') else str(meta.semester),
        is_answer_key=meta.is_answer_key,
        extractor_version=VERSION,
        processing_date=datetime.now(timezone.utc).isoformat(),
    )

    questions: list[Question] = []

    try:
        # Step 1: Classify PDF
        classification = classify_pdf(pdf_path, config.extraction)
        report.pages = classification.page_count
        report.pdf_type = classification.overall_type.value

        # Step 2: Load PDF document safely
        pdf_doc = load_pdf(pdf_path)
        all_elements: list[ElementBlock] = []
        ocr_confidences: list[float] = []

        with pdf_doc:
            for page_cls in classification.pages:
                pn = page_cls.page_number
                page = pdf_doc.get_page(pn - 1)
                pw, ph = page.rect.width, page.rect.height

                rendered_img = render_page(page, config.ocr.dpi)

                if page_cls.page_type == PDFPageType.NATIVE:
                    elements = extract_native_text(page, pn)
                    all_elements.extend(elements)
                elif page_cls.page_type == PDFPageType.SCANNED:
                    report.ocr_used = True
                    report.ocr_engine = "apple_vision"
                    processed_img = preprocess_image(rendered_img, config.ocr)
                    elements = ocr_page(processed_img, pn, pw, ph, config.ocr)
                    elements = postprocess_ocr_results(elements, pw, ph, config.ocr)
                    all_elements.extend(elements)
                    ocr_confidences.extend(e.confidence for e in elements if e.confidence is not None)
                else:  # HYBRID
                    report.ocr_used = True
                    report.ocr_engine = "apple_vision"
                    native_el = extract_native_text(page, pn)
                    processed_img = preprocess_image(rendered_img, config.ocr)
                    ocr_el = ocr_page(processed_img, pn, pw, ph, config.ocr)
                    ocr_el = postprocess_ocr_results(ocr_el, pw, ph, config.ocr)
                    merged_el = _merge_hybrid_elements(native_el, ocr_el)
                    all_elements.extend(merged_el)
                    ocr_confidences.extend(e.confidence for e in merged_el if e.source == ExtractionSource.OCR and e.confidence is not None)

                # Figure extraction to paper-specific assets folder in textPapers/
                try:
                    figs = detect_figures(
                        page, rendered_img, pn, all_elements,
                        job.target_assets_dir, job.paper_stem, config.content_detection
                    )
                    report.figures_detected += len(figs)
                    for fig in figs:
                        if fig.image_path:
                            report.figures_saved.append(fig.image_path)
                except Exception as e:
                    logger.warning(f"Figure extraction warning on page {pn}: {e}")

        if ocr_confidences:
            report.avg_ocr_confidence = sum(ocr_confidences) / len(ocr_confidences)

        if not all_elements:
            report.processing_status = ProcessingStatus.FAILED
            report.errors.append("No text or visual elements extractable from PDF")
            report.processing_time_seconds = time.time() - t0
            write_paper_report(report, job.target_report_path)
            return [], report

        # Step 3: Layout analysis and reading order
        all_paragraphs: list[ParagraphBlock] = []
        pages_detected = sorted(set(e.page for e in all_elements))
        for pn in pages_detected:
            page_elements = [e for e in all_elements if e.page == pn]
            paragraphs = analyze_layout(page_elements, pn, 595.0, 842.0, config.extraction)
            paragraphs = order_paragraphs(paragraphs, 595.0)
            all_paragraphs.extend(paragraphs)

        # Step 4: Administrative content removal
        body_paragraphs, admin_paragraphs, header_meta = detect_and_remove_admin(
            all_paragraphs, len(pages_detected), 842.0, config.extraction
        )
        if "max_marks" in header_meta:
            report.stated_max_marks = header_meta["max_marks"]

        if not body_paragraphs:
            report.processing_status = ProcessingStatus.WARNING
            report.warnings.append("No body paragraphs remaining after admin removal")
            report.processing_time_seconds = time.time() - t0
            write_paper_report(report, job.target_report_path)
            return [], report

        # Step 5: Question & Subquestion segmentation
        candidates = detect_questions(body_paragraphs, config.question_detection)
        if not candidates:
            report.processing_status = ProcessingStatus.WARNING
            report.warnings.append("No questions segmented from body paragraphs")
            report.processing_time_seconds = time.time() - t0
            write_paper_report(report, job.target_report_path)
            return [], report

        main_qs = [c for c in candidates if not c.is_subquestion]
        sub_qs = [c for c in candidates if c.is_subquestion]
        report.questions_detected = len(main_qs)
        report.subquestions_detected = len(sub_qs)

        # Step 6: Specialized content detection (Code, Equations, Tables)
        detected_content: dict[int, ContentBlock] = {}

        try:
            eqs = detect_equations(body_paragraphs)
            for pidx, eb in eqs:
                if 0 <= pidx < len(body_paragraphs):
                    detected_content[id(body_paragraphs[pidx])] = eb
            report.equations_detected = len(eqs)
        except Exception as e:
            logger.warning(f"Equation detection error: {e}")

        try:
            codes = detect_code_blocks(body_paragraphs)
            for p_indices, cb in codes:
                for pi in p_indices:
                    if 0 <= pi < len(body_paragraphs):
                        detected_content[id(body_paragraphs[pi])] = cb
            report.code_blocks_detected = len(codes)
        except Exception as e:
            logger.warning(f"Code detection error: {e}")

        try:
            tables = detect_tables(body_paragraphs, all_elements)
            for p_indices, tb in tables:
                for pi in p_indices:
                    if 0 <= pi < len(body_paragraphs):
                        detected_content[id(body_paragraphs[pi])] = tb
            report.tables_detected = len(tables)
        except Exception as e:
            logger.warning(f"Table detection error: {e}")

        # Step 7: Question reconstruction
        questions = reconstruct_questions(candidates, detected_content, meta)

        # Step 8: Conservative text cleaning
        questions = [clean_question(q, config.cleaning) for q in questions]

        # Step 9: Local Validation & Confidence Assessment
        total_marks = sum(q.marks or 0 for q in questions if not q.subquestion)
        report.marks_detected = total_marks if total_marks > 0 else None
        if report.stated_max_marks and report.marks_detected:
            tol = config.validation.marks_tolerance_percent / 100.0
            diff = abs(report.marks_detected - report.stated_max_marks)
            report.marks_match = diff <= (report.stated_max_marks * tol)

        validation = validate_paper(questions, report, config.validation)
        report.validation = validation

        for q in questions:
            det_score = next(
                (c.score for c in candidates if c.question_number == q.question_number and c.subquestion_label == q.subquestion),
                1.0
            )
            q.extraction_confidence = compute_question_confidence(q, det_score, validation, config.confidence)
            tier = assign_confidence_tier(q.extraction_confidence, config.confidence)
            q.verification_status = assign_verification_status(tier)

        # Step 10: Save Raw Extraction Record
        raw_json_path = job.target_csv_path.parent / f"{job.paper_stem}_raw.json"
        try:
            raw_data = [q.model_dump() for q in questions]
            raw_json_path.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed writing raw extraction JSON: {e}")

        report.overall_confidence = compute_paper_confidence(questions)
        report.processing_status = (
            ProcessingStatus.WARNING if validation.warning_count > 0 else ProcessingStatus.SUCCESS
        )

        # Step 11: Output Serialization — Write CSV with Question Separator to textPapers/
        write_paper_csv(
            questions=questions,
            target_csv_path=job.target_csv_path,
            course_code=job.course_code,
            paper_file=meta.file_name,
            exam_type=meta.exam_type.value if hasattr(meta.exam_type, 'value') else str(meta.exam_type),
            academic_year=meta.academic_year,
            semester=meta.semester.value if hasattr(meta.semester, 'value') else str(meta.semester),
            separator=config.extraction.question_separator
        )

        # Also write clean mirror to textPapersCSV/ (CSV-only folder structure)
        if job.target_csv_only_path:
            write_paper_csv(
                questions=questions,
                target_csv_path=job.target_csv_only_path,
                course_code=job.course_code,
                paper_file=meta.file_name,
                exam_type=meta.exam_type.value if hasattr(meta.exam_type, 'value') else str(meta.exam_type),
                academic_year=meta.academic_year,
                semester=meta.semester.value if hasattr(meta.semester, 'value') else str(meta.semester),
                separator=config.extraction.question_separator
            )

    except Exception as e:
        logger.error(f"Failed processing PDF {pdf_path.name}: {e}", exc_info=True)
        report.processing_status = ProcessingStatus.FAILED
        report.errors.append(str(e))
        questions = []

    report.processing_time_seconds = time.time() - t0
    write_paper_report(report, job.target_report_path)

    return questions, report


def _merge_hybrid_elements(native: list[ElementBlock], ocr: list[ElementBlock]) -> list[ElementBlock]:
    if not native:
        return ocr
    if not ocr:
        return native

    merged = list(native)
    for ocr_el in ocr:
        covered = False
        for nat_el in native:
            if nat_el.bbox.overlaps(ocr_el.bbox):
                if nat_el.bbox.vertical_overlap_ratio(ocr_el.bbox) > 0.5:
                    covered = True
                    break
        if not covered:
            ocr_el.source = ExtractionSource.OCR
            merged.append(ocr_el)

    merged.sort(key=lambda e: (e.page, e.bbox.y0, e.bbox.x0))
    return merged


def run_stage_a_pipeline(
    config: PipelineConfig,
    project_root: Path,
    selected_courses: list[str] | None = None,
    limit: int | None = None,
    skip_answer_keys: bool = False,
    force: bool = False
) -> list[ExtractionReport]:
    """
    Master Stage A Pipeline Runner.
    """
    papers_dir = project_root / config.paths.papers_dir
    output_dir = project_root / config.paths.output_dir
    csv_output_dir = project_root / config.paths.csv_output_dir
    reports_dir = project_root / config.paths.reports_dir

    logger.info(f"Stage A Extraction Initialized: Source={papers_dir}, Output={output_dir}, CSV_Only={csv_output_dir}")

    jobs = discover_paper_jobs(
        papers_dir=papers_dir,
        output_base_dir=output_dir,
        csv_output_base_dir=csv_output_dir,
        selected_courses=selected_courses,
        skip_answer_keys=skip_answer_keys
    )

    if limit and limit > 0:
        jobs = jobs[:limit]
        logger.info(f"Limiting execution to {limit} paper jobs.")

    all_reports: list[ExtractionReport] = []
    total_jobs = len(jobs)

    for idx, job in enumerate(jobs, start=1):
        pct = (idx / total_jobs) * 100.0
        logger.info(f"Progress: [{idx}/{total_jobs} Papers Parsed ({pct:.1f}%)] | Current: {job.course_code} / {job.pdf_path.name}")
        questions, report = process_single_paper(job, config, force=force)
        all_reports.append(report)

    try:
        write_batch_summary(all_reports, reports_dir, total_papers=total_jobs)
        print_batch_summary(all_reports, total_papers=total_jobs)
    except Exception as e:
        logger.warning(f"Summary generation warning: {e}")

    return all_reports
