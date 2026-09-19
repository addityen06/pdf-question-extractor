from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from pdfextract.core.models import PaperMetadata, ExamType, Semester
from pdfextract.core.constants import FILENAME_PATTERN

logger = logging.getLogger(__name__)


@dataclass
class PaperJob:
    """Represents a single independent PDF paper extraction job."""
    course_code: str
    pdf_path: Path
    paper_stem: str
    target_csv_path: Path
    target_csv_only_path: Path
    target_assets_dir: Path
    target_report_path: Path
    metadata: PaperMetadata


def extract_course_code(dir_name: str) -> str:
    """
    Extract course code from a directory name, handling brackets or descriptive suffixes.
    Example: 'Electric_Vehicle_Instrumentation_and_Data_Analytics_[ВАМЕЕ344]' -> 'ВАМЕЕ344'
    Example: 'BACSE104' -> 'BACSE104'
    """
    match = re.search(r'\[(.*?)\]', dir_name)
    if match:
        extracted = match.group(1).strip()
        if extracted:
            return extracted
    return dir_name.strip()


def parse_paper_filename(file_path: Path, course_code: str) -> PaperMetadata:
    """
    Parse structured exam metadata from the PDF filename.
    """
    filename = file_path.name
    parse_warnings = []
    
    exam_type = "Unknown"
    academic_year = "Unknown"
    semester = "Unknown"
    slot = "Unknown"
    campus = "Unknown"
    is_answer_key = "_AnsKey" in filename or "AnsKey" in filename
    file_hash = file_path.stem.split("_")[-1] if "_" in file_path.stem else "Unknown"

    match = FILENAME_PATTERN.match(filename)
    if match:
        gd = match.groupdict()
        exam_type = gd.get("exam_type", exam_type)
        academic_year = gd.get("year", academic_year)
        if "semester" in gd:
            semester = f"{gd['semester']}_Semester"
        slot = gd.get("slot", slot)
        campus = gd.get("campus", campus)
        file_hash = gd.get("hash", file_hash)
    else:
        parse_warnings.append(f"Filename '{filename}' does not match standard pattern.")
        parts = file_path.stem.split("_")
        if len(parts) >= 5:
            exam_type = parts[0]
            academic_year = parts[1]
            semester = parts[2]
            slot = parts[3]
            campus = parts[4]

    return PaperMetadata(
        file_path=str(file_path.resolve()),
        file_name=filename,
        course_code=course_code,
        exam_type=exam_type,
        academic_year=academic_year,
        semester=semester,
        slot=slot,
        campus=campus,
        is_answer_key=is_answer_key,
        file_hash=file_hash,
        parse_warnings=parse_warnings
    )


def discover_paper_jobs(
    papers_dir: Path,
    output_base_dir: Path,
    csv_output_base_dir: Path | None = None,
    selected_courses: list[str] | None = None,
    skip_answer_keys: bool = False
) -> list[PaperJob]:
    """
    Scans Papers/ and builds individual PaperJob objects.
    Enforces exact 1:1 mapping: ONE PDF -> ONE CSV / ASSETS / REPORT.
    Populates:
      - target_csv_path in textPapers/<course>/<paper_stem>.csv
      - target_csv_only_path in textPapersCSV/<course>/<paper_stem>.csv (CSV-only directory)
    """
    papers_path = Path(papers_dir)
    output_path = Path(output_base_dir)
    csv_output_path = Path(csv_output_base_dir) if csv_output_base_dir else (output_path.parent / "textPapersCSV")
    
    if not papers_path.exists() or not papers_path.is_dir():
        logger.error(f"Papers directory not found: {papers_path}")
        return []

    jobs: list[PaperJob] = []
    skip_dirs = {'.venv', '__pycache__', '.git', '.idea', '.vscode', 'textPapers', 'textPapersCSV', 'reports', 'logs'}

    for course_entry in sorted(papers_path.iterdir()):
        if not course_entry.is_dir() or course_entry.name.startswith('.') or course_entry.name in skip_dirs:
            continue

        course_code = extract_course_code(course_entry.name)

        if selected_courses and course_code not in selected_courses and course_entry.name not in selected_courses:
            continue

        course_output_dir = output_path / course_code
        course_csv_only_dir = csv_output_path / course_code
        pdf_files = sorted(course_entry.glob('**/*.pdf'))

        for pdf_file in pdf_files:
            metadata = parse_paper_filename(pdf_file, course_code)

            if skip_answer_keys and metadata.is_answer_key:
                logger.info(f"Skipping answer key PDF: {pdf_file.name}")
                continue

            paper_stem = pdf_file.stem

            # Exact per-paper paths
            target_csv = course_output_dir / f"{paper_stem}.csv"
            target_csv_only = course_csv_only_dir / f"{paper_stem}.csv"
            target_assets = course_output_dir / f"{paper_stem}_assets"
            target_report = course_output_dir / f"{paper_stem}_extraction_report.json"

            job = PaperJob(
                course_code=course_code,
                pdf_path=pdf_file,
                paper_stem=paper_stem,
                target_csv_path=target_csv,
                target_csv_only_path=target_csv_only,
                target_assets_dir=target_assets,
                target_report_path=target_report,
                metadata=metadata
            )
            jobs.append(job)

    logger.info(f"Discovered {len(jobs)} independent PDF paper jobs across {len(set(j.course_code for j in jobs))} courses.")
    return jobs
