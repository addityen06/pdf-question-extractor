from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from pdfextract.core.models import ExtractionReport, ProcessingStatus

logger = logging.getLogger(__name__)


def write_paper_report(report: ExtractionReport, target_report_path: Path) -> Path:
    """
    Write individual paper extraction report to its dedicated JSON path.
    Output: textPapers/<course_code>/<paper_stem>_extraction_report.json
    """
    target_report_path = Path(target_report_path)
    target_report_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(target_report_path, 'w', encoding='utf-8') as f:
            f.write(report.model_dump_json(indent=2))
        logger.info(f"Wrote paper report: {target_report_path}")
        return target_report_path
    except Exception as e:
        logger.error(f"Failed to write paper report {target_report_path}: {e}")
        raise


def write_batch_summary(all_reports: List[ExtractionReport], reports_dir: Path, total_papers: Optional[int] = None) -> Path:
    """Write batch execution summary report to logs/ or reports/."""
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "batch_summary.json"
    
    succeeded = sum(1 for r in all_reports if r.processing_status == ProcessingStatus.SUCCESS)
    warned = sum(1 for r in all_reports if r.processing_status == ProcessingStatus.WARNING)
    failed = sum(1 for r in all_reports if r.processing_status == ProcessingStatus.FAILED)
    
    summary = {
        "papers_parsed": len(all_reports),
        "total_papers": total_papers or len(all_reports),
        "success_count": succeeded,
        "warning_count": warned,
        "failed_count": failed,
        "total_questions_extracted": sum(r.questions_detected for r in all_reports),
        "avg_confidence": (sum(r.overall_confidence for r in all_reports) / len(all_reports)) if all_reports else 0.0,
        "total_equations_detected": sum(r.equations_detected for r in all_reports),
        "total_tables_detected": sum(r.tables_detected for r in all_reports),
        "total_code_blocks_detected": sum(r.code_blocks_detected for r in all_reports),
        "total_figures_detected": sum(r.figures_detected for r in all_reports)
    }
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        return path
    except Exception as e:
        logger.error(f"Failed to write batch summary {path}: {e}")
        raise


def print_batch_summary(all_reports: List[ExtractionReport], total_papers: Optional[int] = None) -> None:
    """Display rich formatted summary table in terminal showing papers parsed / total papers."""
    if not all_reports:
        print("No papers processed.")
        return
        
    total_count = total_papers if total_papers is not None else len(all_reports)
    parsed_count = len(all_reports)
    pct = (parsed_count / total_count * 100) if total_count > 0 else 100.0

    console = Console()
    table = Table(title=f"PDF Extraction Summary — [{parsed_count}/{total_count} Papers Parsed ({pct:.1f}%)]")
    
    table.add_column("Paper File", style="cyan", no_wrap=True)
    table.add_column("Course", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Questions", justify="right", style="yellow")
    table.add_column("Marks", justify="right", style="blue")
    table.add_column("Confidence", justify="right")
    table.add_column("Status", style="bold")
    
    for r in all_reports:
        status_val = r.processing_status.value if hasattr(r.processing_status, 'value') else str(r.processing_status)
        status_color = "green" if status_val == "success" else "yellow" if status_val == "warning" else "red"
        
        marks_str = str(r.marks_detected) if r.marks_detected is not None else "-"
        if r.stated_max_marks:
            marks_str += f" / {r.stated_max_marks}"
            
        table.add_row(
            r.paper_file[:32] + "..." if len(r.paper_file) > 35 else r.paper_file,
            r.course_code,
            r.pdf_type,
            str(r.questions_detected),
            marks_str,
            f"{r.overall_confidence:.2f}",
            f"[{status_color}]{status_val.upper()}[/{status_color}]"
        )
        
    console.print(table)
