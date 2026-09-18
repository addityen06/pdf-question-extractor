from __future__ import annotations
import logging
from pathlib import Path

from questionai.core.models import PaperMetadata
from questionai.core.constants import FILENAME_PATTERN

logger = logging.getLogger(__name__)

def parse_filename(file_path: Path, course_code: str) -> PaperMetadata:
    """Parse structured VIT PDF filenames into PaperMetadata objects."""
    filename = file_path.name
    parse_warnings = []
    
    # Defaults
    exam_type = "Unknown"
    academic_year = "Unknown"
    semester = "Unknown"
    slot = "Unknown"
    campus = "Unknown"
    is_answer_key = "_AnsKey" in filename or "AnsKey" in filename
    file_hash = "Unknown"
    
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
        
        if "_AnsKey_" in filename or filename.endswith("_AnsKey.pdf") or filename.endswith(f"_AnsKey_{file_hash}.pdf"):
            is_answer_key = True
    else:
        parse_warnings.append(f"Filename '{filename}' does not match standard pattern.")
        
        # Fallback parsing
        parts = filename.replace(".pdf", "").split("_")
        
        is_answer_key = "AnsKey" in parts
        if is_answer_key:
            parts.remove("AnsKey")
            
        if parts and parts[0] == "Model":
            if len(parts) > 1:
                parts[1] = f"Model_{parts[1]}"
            parts.pop(0)
            
        if len(parts) >= 6:
            exam_type = parts[0]
            academic_year = parts[1]
            semester = parts[2]
            if len(parts) > 3 and parts[3] == "Semester":
                semester = f"{parts[2]}_Semester"
                parts.pop(3)
            slot = parts[3]
            campus = parts[4]
            file_hash = parts[-1]
        
    return PaperMetadata(
        file_path=str(file_path),
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
