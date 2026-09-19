from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Iterator

from pdfextract.core.models import PaperMetadata, BatchProcessingState
from pdfextract.ingestion.directory_scanner import scan_papers_directory, count_total_pdfs
from pdfextract.ingestion.filename_parser import parse_filename

logger = logging.getLogger(__name__)

class PaperRegistry:
    """Build and maintain a catalog of all papers with their metadata."""
    def __init__(self):
        self.papers: list[PaperMetadata] = []

    def build(self, root_dir: Path) -> None:
        """Scan directory and build registry."""
        logger.info(f"Building registry from {root_dir}")
        self.papers = []
        directories = scan_papers_directory(root_dir)
        
        for directory in directories:
            for pdf_path in directory.pdf_files:
                try:
                    metadata = parse_filename(pdf_path, directory.course_code)
                    self.papers.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to parse {pdf_path}: {e}")
                    
        logger.info(f"Registry built with {len(self.papers)} papers")

    def get_papers(self, course_code: str) -> list[PaperMetadata]:
        return [p for p in self.papers if p.course_code == course_code]

    def get_all_papers(self) -> list[PaperMetadata]:
        return self.papers

    def get_courses(self) -> list[str]:
        return list(set(p.course_code for p in self.papers))

    def filter_by_exam_type(self, exam_type: str) -> list[PaperMetadata]:
        return [p for p in self.papers if p.exam_type == exam_type]

    def filter_by_year(self, year: str) -> list[PaperMetadata]:
        return [p for p in self.papers if p.academic_year == year]

    def get_stats(self) -> dict:
        courses = self.get_courses()
        stats = {
            "total_papers": len(self.papers),
            "total_courses": len(courses),
            "answer_key_count": sum(1 for p in self.papers if p.is_answer_key),
            "papers_per_course": {c: len(self.get_papers(c)) for c in courses},
            "papers_per_exam_type": {}
        }
        for p in self.papers:
            stats["papers_per_exam_type"][p.exam_type] = stats["papers_per_exam_type"].get(p.exam_type, 0) + 1
        return stats

    def iter_papers(self) -> Iterator[PaperMetadata]:
        return iter(self.papers)

    def iter_unprocessed(self, state: BatchProcessingState) -> Iterator[PaperMetadata]:
        processed_ids = set(state.records.keys())
        for p in self.papers:
            if p.file_path not in processed_ids:
                yield p

    def save(self, file_path: Path) -> None:
        """Save registry to JSON for fast reload."""
        try:
            data = [p.model_dump() for p in self.papers]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved registry to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save registry to {file_path}: {e}")

    def load(self, file_path: Path) -> None:
        """Load registry from JSON."""
        if not file_path.exists():
            logger.warning(f"Registry file not found: {file_path}")
            return
            
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self.papers = [PaperMetadata.model_validate(item) for item in data]
            logger.info(f"Loaded registry with {len(self.papers)} papers from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load registry from {file_path}: {e}")
