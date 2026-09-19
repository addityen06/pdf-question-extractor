#!/usr/bin/env python3
"""
Stage A CLI Runner
=================================
Automated PDF Question Extraction Pipeline.

Enforces:
1. ONE PDF Paper -> ONE CSV File in textPapers/<course_code>/<paper_stem>.csv
2. Explicit Question Separator: <<<QUESTION_END>>>
3. 100% Deterministic Local Processing with Quality Tiers:
   - auto_extracted
   - review_recommended
   - review_required
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src/ to Python search path so the package resolves when running directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pdfextract.core.config import load_config, PipelineConfig
from pdfextract.core.constants import VERSION
from pdfextract.core.models import ProcessingStatus
from pdfextract.pipeline import run_stage_a_pipeline


def setup_logging(config: PipelineConfig, project_root: Path) -> None:
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if config.logging.log_to_file:
        log_dir = project_root / config.paths.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        log_file = log_dir / f"stage_a_{datetime.now():%Y%m%d_%H%M%S}.log"
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=handlers,
        force=True
    )
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("pymupdf").setLevel(logging.WARNING)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF Question Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to custom YAML config file (default: config/default.yaml)"
    )
    parser.add_argument(
        "--courses",
        nargs="*",
        default=None,
        help="Specific course codes to process (e.g. BACSE104 BMAT101L)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit total number of papers to process"
    )
    parser.add_argument(
        "--skip-answer-keys",
        action="store_true",
        help="Exclude faculty answer key PDFs"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-extraction of previously processed papers"
    )
    parser.add_argument(
        "--papers-dir",
        type=str,
        default=None,
        help="Override source Papers directory"
    )
    args = parser.parse_args()

    config_path = args.config
    if config_path is None:
        default_cfg = PROJECT_ROOT / "config" / "default.yaml"
        if default_cfg.exists():
            config_path = str(default_cfg)

    config = load_config(config_path)
    if args.skip_answer_keys:
        config.batch.skip_answer_keys = True
    if args.papers_dir:
        config.paths.papers_dir = args.papers_dir

    setup_logging(config, PROJECT_ROOT)
    logger = logging.getLogger("pdfextract")

    logger.info("=" * 70)
    logger.info(f"  PDF Extraction Engine v{VERSION}")
    logger.info(f"  Project Root: {PROJECT_ROOT}")
    logger.info(f"  Question Separator: {config.extraction.question_separator}")
    logger.info("  Mode: 1 PDF -> 1 CSV (Independent Per-Paper Extraction)")
    logger.info("=" * 70)

    reports = run_stage_a_pipeline(
        config=config,
        project_root=PROJECT_ROOT,
        selected_courses=args.courses,
        limit=args.limit,
        skip_answer_keys=args.skip_answer_keys,
        force=args.force
    )

    succeeded = sum(1 for r in reports if r.processing_status == ProcessingStatus.SUCCESS)
    warned = sum(1 for r in reports if r.processing_status == ProcessingStatus.WARNING)
    failed = sum(1 for r in reports if r.processing_status == ProcessingStatus.FAILED)
    total_qs = sum(r.questions_detected for r in reports)

    logger.info("=" * 70)
    logger.info("  STAGE A BATCH COMPLETED")
    logger.info(f"  Papers Processed: {len(reports)} | Success: {succeeded} | Warning: {warned} | Failed: {failed}")
    logger.info(f"  Total Questions Extracted: {total_qs}")
    if reports:
        avg_conf = sum(r.overall_confidence for r in reports) / len(reports)
        logger.info(f"  Mean Confidence: {avg_conf:.2f}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
