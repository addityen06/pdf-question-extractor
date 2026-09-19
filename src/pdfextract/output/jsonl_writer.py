from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from pdfextract.core.models import Question

logger = logging.getLogger(__name__)


def write_questions_jsonl(questions: List[Question], output_dir: Path, course_code: str) -> Path:
    """
    Write rich canonical questions to textPapers/{course_code}/questions.jsonl.
    """
    out_dir = output_dir / course_code
    out_dir.mkdir(parents=True, exist_ok=True)
    
    jsonl_path = out_dir / "questions.jsonl"
    existing_ids = set()
    
    if jsonl_path.exists():
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            obj = json.loads(line)
                            if 'question_id' in obj:
                                existing_ids.add(obj['question_id'])
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass
            
    try:
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            for q in questions:
                if q.question_id not in existing_ids:
                    f.write(q.model_dump_json() + "\n")
                    existing_ids.add(q.question_id)
                    
        logger.info(f"Wrote JSONL questions to {jsonl_path}")
        return jsonl_path
    except Exception as e:
        logger.error(f"Failed to write JSONL {jsonl_path}: {e}")
        raise
