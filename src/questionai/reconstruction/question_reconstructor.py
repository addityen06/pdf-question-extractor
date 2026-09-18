"""
QuestionAI — Question Reconstructor
=====================================
Assembles detected questions, subquestions, and typed content blocks
into final Question objects — the canonical output of Stage A.
"""

from __future__ import annotations

import logging
from typing import Any

from questionai.core.models import (
    Question,
    ContentBlock,
    BlockType,
    PaperMetadata,
    ParagraphBlock,
    VerificationStatus,
    ExtractionSource,
)
from questionai.content.question_detector import QuestionCandidate

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT BLOCK CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════


def _classify_paragraph_blocks(
    paragraphs: list[ParagraphBlock],
    detected_content: dict[int, ContentBlock],
) -> list[ContentBlock]:
    """
    Convert a question's paragraphs into an ordered list of ContentBlocks.

    Parameters
    ----------
    paragraphs : the paragraphs belonging to this question
    detected_content : mapping from global paragraph index → ContentBlock
                       (pre-detected equations, tables, code, figures)
    """
    blocks: list[ContentBlock] = []

    for para in paragraphs:
        para_id = id(para)

        if para_id in detected_content:
            blocks.append(detected_content[para_id])
        else:
            # Default: text block
            blocks.append(ContentBlock(
                type=BlockType.TEXT,
                content=para.text.strip(),
                confidence=1.0,
                source_page=para.page,
                source_bbox=para.bbox,
            ))

    return blocks


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT FLATTENING
# ═══════════════════════════════════════════════════════════════════════════════


def _flatten_blocks_to_text(blocks: list[ContentBlock]) -> str:
    """
    Produce a single plain-text string from a list of ContentBlocks.
    Used for the CSV `question_text` column.
    """
    parts: list[str] = []

    for b in blocks:
        if b.type == BlockType.TEXT:
            if b.content.strip():
                parts.append(b.content.strip())

        elif b.type == BlockType.EQUATION:
            if b.latex:
                parts.append(f"${b.latex}$")
            elif b.content:
                parts.append(b.content)
            else:
                parts.append("[EQUATION]")

        elif b.type == BlockType.CODE:
            lang = b.language or ""
            parts.append(f"```{lang}\n{b.content}\n```")

        elif b.type == BlockType.TABLE:
            if b.content:
                parts.append(b.content)
            elif b.rows:
                # Render as markdown table
                md_rows = []
                for ri, row in enumerate(b.rows):
                    md_rows.append("| " + " | ".join(str(c) for c in row) + " |")
                    if ri == 0:
                        md_rows.append("| " + " | ".join("---" for _ in row) + " |")
                parts.append("\n".join(md_rows))
            else:
                parts.append("[TABLE]")

        elif b.type == BlockType.FIGURE:
            ref = b.image_path or "unknown"
            cap = f" ({b.caption})" if b.caption else ""
            parts.append(f"[FIGURE: {ref}{cap}]")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION ID GENERATION
# ═══════════════════════════════════════════════════════════════════════════════


def _generate_question_id(
    meta: PaperMetadata,
    question_number: int,
    subquestion: str | None,
) -> str:
    """Generate a globally unique question ID."""
    course = meta.course_code or "UNKNOWN"
    exam = meta.exam_type.value if hasattr(meta.exam_type, 'value') else str(meta.exam_type or "EXAM")
    year = meta.academic_year or "YEAR"
    semester = meta.semester.value if hasattr(meta.semester, 'value') else str(meta.semester or "")

    base = f"{course}_{exam}_{year}"
    if semester:
        base += f"_{semester}"

    q_part = f"Q{question_number}"
    if subquestion:
        q_part += f"_{subquestion}"

    return f"{base}_{q_part}"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RECONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════════


def reconstruct_questions(
    candidates: list[QuestionCandidate],
    detected_content: dict[int, ContentBlock],
    paper_metadata: PaperMetadata,
) -> list[Question]:
    """
    Assemble detected question candidates into final Question objects.

    Parameters
    ----------
    candidates : output of question_detector.detect_questions()
    detected_content : mapping from paragraph id(para) → ContentBlock
        for pre-detected equations, tables, code blocks, and figures.
    paper_metadata : metadata parsed from the PDF filename.

    Returns
    -------
    List of Question objects — the canonical pipeline output.
    """
    logger.info(f"Reconstructing {len(candidates)} question candidates for "
                f"{paper_metadata.file_name}")

    questions: list[Question] = []

    for cand in candidates:
        try:
            # ── Build content blocks ──────────────────────────────────
            blocks = _classify_paragraph_blocks(
                cand.content_paragraphs, detected_content
            )

            # Remove leading paragraph that IS the question number line,
            # but only the numbering portion — keep the actual question text.
            # The first block likely starts with "1. " or "Q1 " which is fine.

            # ── Flatten to text ───────────────────────────────────────
            question_text = _flatten_blocks_to_text(blocks)

            # ── Collect source pages ──────────────────────────────────
            source_pages = sorted(set(
                p.page for p in cand.content_paragraphs if p.page
            ))
            if not source_pages:
                source_pages = [cand.page]

            # ── Build Question ────────────────────────────────────────
            q_id = _generate_question_id(
                paper_metadata,
                cand.question_number,
                cand.subquestion_label,
            )

            q = Question(
                question_id=q_id,
                course_code=paper_metadata.course_code,
                paper_file=paper_metadata.file_name,
                paper_id=getattr(paper_metadata, 'paper_id', ''),
                exam_type=paper_metadata.exam_type.value if hasattr(paper_metadata.exam_type, 'value') else str(paper_metadata.exam_type or ""),
                academic_year=str(paper_metadata.academic_year or ""),
                semester=paper_metadata.semester.value if hasattr(paper_metadata.semester, 'value') else str(paper_metadata.semester or ""),
                slot=str(paper_metadata.slot or ""),
                campus=str(paper_metadata.campus or ""),
                is_answer_key=bool(paper_metadata.is_answer_key),
                question_number=cand.question_number,
                subquestion=cand.subquestion_label,
                parent_question=(
                    cand.question_number if cand.is_subquestion else None
                ),
                marks=cand.marks,
                choice_group=cand.choice_group,
                blocks=blocks,
                question_text=question_text,
                extraction_confidence=min(cand.score / 10.0, 1.0),
                source_pages=source_pages,
            )

            # ── Detect special content flags ──────────────────────────
            has_eq = any(b.type == BlockType.EQUATION for b in blocks)
            has_code = any(b.type == BlockType.CODE for b in blocks)
            has_table = any(b.type == BlockType.TABLE for b in blocks)
            has_fig = any(b.type == BlockType.FIGURE for b in blocks)

            # Store in warnings for now; these become CSV columns later
            if has_eq:
                q.warnings.append("contains_equation")
            if has_code:
                q.warnings.append("contains_code")
            if has_table:
                q.warnings.append("contains_table")
            if has_fig:
                q.warnings.append("contains_figure")

            questions.append(q)

        except Exception as exc:
            logger.warning(
                f"Failed to reconstruct Q{cand.question_number}"
                f"{'(' + cand.subquestion_label + ')' if cand.subquestion_label else ''}: "
                f"{exc}"
            )

    logger.info(f"Reconstructed {len(questions)} questions "
                f"({len([q for q in questions if q.subquestion])} subquestions)")
    return questions
