from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List

from pdfextract.core.models import Question, BlockType
from pdfextract.core.config import DEFAULT_QUESTION_SEPARATOR

logger = logging.getLogger(__name__)


def write_paper_csv(
    questions: List[Question],
    target_csv_path: Path,
    course_code: str,
    paper_file: str,
    exam_type: str = "",
    academic_year: str = "",
    semester: str = "",
    separator: str = DEFAULT_QUESTION_SEPARATOR
) -> Path:
    """
    Write extracted questions for ONE individual PDF paper to its own CSV file.
    Output: textPapers/<course_code>/<paper_stem>.csv

    Enforces:
    1. Terminal question separator appended to question_text.
    2. Explicit 'separator' column in CSV schema.
    3. Distinct records per subquestion (3a, 3b, etc.).
    """
    target_csv_path = Path(target_csv_path)
    target_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort questions in strict sequential order
    sorted_qs = sorted(questions, key=lambda q: (q.question_number, q.subquestion or ""))
    
    try:
        with open(target_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            # Standard Stage A CSV Schema
            writer.writerow([
                "question_number",
                "subquestion",
                "marks",
                "question_type",
                "question_text",
                "separator",
                "confidence",
                "verification_status",
                "course_code",
                "paper_file",
                "exam_type",
                "academic_year",
                "semester",
                "has_equation",
                "has_code",
                "has_table",
                "has_figure",
                "choice_group"
            ])
            
            for q in sorted_qs:
                has_eq = any(b.type == BlockType.EQUATION or getattr(b.type, 'value', '') == "equation" for b in q.blocks)
                has_code = any(b.type == BlockType.CODE or getattr(b.type, 'value', '') == "code" for b in q.blocks)
                has_table = any(b.type == BlockType.TABLE or getattr(b.type, 'value', '') == "table" for b in q.blocks)
                has_figure = any(b.type == BlockType.FIGURE or getattr(b.type, 'value', '') == "figure" for b in q.blocks)
                
                q_type = q.question_type or ("programming" if has_code else "numerical" if has_eq else "theory")
                
                exam_val = q.exam_type.value if hasattr(q.exam_type, 'value') else str(q.exam_type or exam_type)
                sem_val = q.semester.value if hasattr(q.semester, 'value') else str(q.semester or semester)
                ver_val = q.verification_status.value if hasattr(q.verification_status, 'value') else str(q.verification_status)
                
                # Enforce separator invariant: clean base text and append separator
                clean_text = q.question_text.strip()
                if clean_text.endswith(separator):
                    clean_text = clean_text[:-len(separator)].strip()
                final_question_text = f"{clean_text}\n{separator}"
                
                writer.writerow([
                    q.question_number,
                    q.subquestion or "",
                    q.marks if q.marks is not None else "",
                    q_type,
                    final_question_text,
                    separator,
                    f"{q.extraction_confidence:.2f}",
                    ver_val,
                    q.course_code or course_code,
                    q.paper_file or paper_file,
                    exam_val,
                    q.academic_year or academic_year,
                    sem_val,
                    has_eq,
                    has_code,
                    has_table,
                    has_figure,
                    q.choice_group or ""
                ])
                
        logger.info(f"Generated paper CSV: {target_csv_path} ({len(sorted_qs)} questions)")
        return target_csv_path
    except Exception as e:
        logger.error(f"Failed to write paper CSV {target_csv_path}: {e}")
        raise
