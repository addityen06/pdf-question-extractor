"""
Question Detector
================================
Multi-signal question boundary detection: the most critical module in the pipeline.
Uses text patterns, font emphasis, marks proximity, vertical gaps, and indentation
to detect question boundaries WITHOUT relying solely on regex.
"""

from __future__ import annotations

import logging
import re
import statistics
from dataclasses import dataclass, field
from typing import Any

from pdfextract.core.models import (
    ParagraphBlock, LineBlock, BoundingBox, BlockType,
)
from pdfextract.core.constants import (
    QUESTION_PATTERNS, SUBQUESTION_PATTERNS,
    MARKS_PATTERNS, OR_PATTERN,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class QuestionCandidate:
    """A detected question boundary candidate with its scoring signals."""
    paragraph: ParagraphBlock
    question_number: int
    score: float
    page: int
    y_position: float
    marks: int | None = None
    is_subquestion: bool = False
    subquestion_label: str | None = None
    content_paragraphs: list[ParagraphBlock] = field(default_factory=list)
    choice_group: str | None = None
    signals: dict[str, float] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _compute_body_font_stats(
    paragraphs: list[ParagraphBlock],
) -> tuple[float, float]:
    """Compute the median font size and average line gap across body paragraphs."""
    font_sizes: list[float] = []
    line_gaps: list[float] = []

    for para in paragraphs:
        for line in para.lines:
            if line.avg_font_size and line.avg_font_size > 0:
                font_sizes.append(line.avg_font_size)
            if line.line_spacing_above is not None and line.line_spacing_above > 0:
                line_gaps.append(line.line_spacing_above)

    median_font = statistics.median(font_sizes) if font_sizes else 10.0
    avg_gap = statistics.mean(line_gaps) if line_gaps else 12.0
    return median_font, avg_gap


def _extract_question_number(text: str) -> int | None:
    """Try every QUESTION_PATTERN against *text* and return the captured number."""
    for pat in QUESTION_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return int(m.group("qnum"))
            except (IndexError, ValueError):
                continue
    return None


def _extract_marks(text: str) -> int | None:
    """Try every MARKS_PATTERN and return the first detected marks value."""
    for pat in MARKS_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return int(m.group("marks"))
            except (IndexError, ValueError):
                continue
    return None


def _is_subquestion_start(text: str) -> tuple[bool, str | None, int | None]:
    """
    Check if *text* starts with a subquestion pattern.
    Returns (is_sub, label, parent_question_number_or_None).
    """
    for pat in SUBQUESTION_PATTERNS:
        m = pat.match(text)
        if m:
            groups = m.groupdict()
            sub_label = groups.get("sub")
            parent_num = None
            if "qnum" in groups:
                try:
                    parent_num = int(groups["qnum"])
                except (TypeError, ValueError):
                    pass
            return True, sub_label, parent_num
    return False, None, None


def _line_is_bold(para: ParagraphBlock) -> bool:
    """Check if the first line of the paragraph is bold."""
    if para.lines:
        return para.lines[0].is_bold
    return False


def _line_font_size(para: ParagraphBlock) -> float | None:
    """Return the font size of the first line."""
    if para.lines and para.lines[0].avg_font_size:
        return para.lines[0].avg_font_size
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


def detect_questions(
    paragraphs: list[ParagraphBlock],
    config: Any = None,
) -> list[QuestionCandidate]:
    """
    Detect question boundaries using multi-signal scoring.

    Signals
    -------
    S1  TEXT PATTERN   (weight 3)  regex match on question number patterns
    S2  FONT EMPHASIS  (weight 2)  bold or larger-than-median font
    S3  MARKS NEARBY   (weight 2)  marks indicator in the same paragraph text
    S4  VERTICAL GAP   (weight 1)  gap above > 1.5× average line gap
    S5  INDENT CHANGE  (weight 1)  x0 shifts left vs. previous paragraph

    Phases
    ------
    1. Score every paragraph and collect candidates
    2. Validate sequential numbering and resolve conflicts
    3. Assign content boundaries (each Q owns paragraphs until next Q)
    4. Detect "OR" choices between adjacent questions
    """
    if not paragraphs:
        return []

    threshold = 3
    if config is not None:
        threshold = getattr(config, "question_signal_threshold", 3)

    median_font, avg_gap = _compute_body_font_stats(paragraphs)

    # ── Phase 1: Score every paragraph ────────────────────────────────────

    raw_candidates: list[QuestionCandidate] = []

    for idx, para in enumerate(paragraphs):
        text = para.text.strip()
        if not text:
            continue

        score = 0.0
        signals: dict[str, float] = {}

        # S1: Text pattern
        qnum = _extract_question_number(text)
        if qnum is not None:
            score += 3.0
            signals["text_pattern"] = 3.0

        # Also check subquestion patterns so we don't miss them
        is_sub, sub_label, parent_num = _is_subquestion_start(text)

        # S2: Font emphasis
        if _line_is_bold(para):
            score += 2.0
            signals["font_bold"] = 2.0
        else:
            fs = _line_font_size(para)
            if fs is not None and fs > median_font * 1.1:
                score += 1.5
                signals["font_size"] = 1.5

        # S3: Marks nearby (in same paragraph text)
        marks_val = _extract_marks(text)
        if marks_val is not None:
            score += 2.0
            signals["marks_nearby"] = 2.0

        # S4: Vertical gap above
        if para.lines and para.lines[0].line_spacing_above is not None:
            gap = para.lines[0].line_spacing_above
            if gap > avg_gap * 1.5:
                score += 1.0
                signals["vertical_gap"] = 1.0

        # S5: Indentation change (shifted left compared to previous paragraph)
        if idx > 0:
            prev_x0 = paragraphs[idx - 1].bbox.x0
            curr_x0 = para.bbox.x0
            if curr_x0 < prev_x0 - 10:  # shifted left → new question likely
                score += 1.0
                signals["indent_left_shift"] = 1.0

        # ── Decide if this is a candidate ─────────────────────────────────

        if qnum is not None and score >= threshold:
            raw_candidates.append(QuestionCandidate(
                paragraph=para,
                question_number=qnum,
                score=score,
                page=para.page,
                y_position=para.bbox.y0,
                marks=marks_val,
                is_subquestion=False,
                subquestion_label=None,
                content_paragraphs=[],
                signals=signals,
            ))
        elif is_sub and sub_label:
            # Subquestion — will be further processed later
            parent = parent_num if parent_num is not None else (
                raw_candidates[-1].question_number if raw_candidates else 0
            )
            raw_candidates.append(QuestionCandidate(
                paragraph=para,
                question_number=parent,
                score=score,
                page=para.page,
                y_position=para.bbox.y0,
                marks=marks_val,
                is_subquestion=True,
                subquestion_label=sub_label,
                content_paragraphs=[],
                signals=signals,
            ))

    if not raw_candidates:
        # Fallback: if zero candidates found with scoring, try regex-only with
        # a lower threshold so we can at least segment *something*.
        logger.warning("No question candidates found via multi-signal scoring; "
                       "falling back to regex-only detection")
        for para in paragraphs:
            qnum = _extract_question_number(para.text.strip())
            if qnum is not None:
                raw_candidates.append(QuestionCandidate(
                    paragraph=para,
                    question_number=qnum,
                    score=1.0,
                    page=para.page,
                    y_position=para.bbox.y0,
                    marks=_extract_marks(para.text),
                    is_subquestion=False,
                    content_paragraphs=[],
                    signals={"regex_fallback": 1.0},
                ))

    # ── Phase 2: Validate sequential numbering ────────────────────────────

    # Separate main questions from subquestions
    main_candidates = [c for c in raw_candidates if not c.is_subquestion]
    sub_candidates = [c for c in raw_candidates if c.is_subquestion]

    # Sort main candidates by page then y-position
    main_candidates.sort(key=lambda c: (c.page, c.y_position))

    # De-duplicate: if two candidates have the same question_number,
    # keep the one with the higher score
    seen_nums: dict[int, QuestionCandidate] = {}
    for c in main_candidates:
        if c.question_number in seen_nums:
            if c.score > seen_nums[c.question_number].score:
                seen_nums[c.question_number] = c
        else:
            seen_nums[c.question_number] = c
    main_candidates = sorted(seen_nums.values(), key=lambda c: (c.page, c.y_position))

    # Check for missing numbers
    if main_candidates:
        nums = [c.question_number for c in main_candidates]
        expected = list(range(nums[0], nums[-1] + 1))
        missing = set(expected) - set(nums)
        if missing:
            logger.warning(f"Missing question numbers: {sorted(missing)}")

    # ── Phase 3: Assign content boundaries ────────────────────────────────

    # Build paragraph index map
    para_index = {id(p): i for i, p in enumerate(paragraphs)}

    # Merge main + sub candidates together, sorted by document position
    all_candidates = sorted(
        main_candidates + sub_candidates,
        key=lambda c: (c.page, c.y_position),
    )

    for ci, cand in enumerate(all_candidates):
        start_idx = para_index.get(id(cand.paragraph), 0)
        if ci + 1 < len(all_candidates):
            next_start = para_index.get(id(all_candidates[ci + 1].paragraph), len(paragraphs))
        else:
            next_start = len(paragraphs)
        cand.content_paragraphs = paragraphs[start_idx:next_start]

    # ── Phase 4: Detect "OR" choice groups ────────────────────────────────

    choice_group_counter = 0
    for ci in range(len(all_candidates) - 1):
        current = all_candidates[ci]
        next_cand = all_candidates[ci + 1]
        # Check if any paragraph between them (or the start of next) contains "OR"
        between_start = para_index.get(id(current.paragraph), 0)
        between_end = para_index.get(id(next_cand.paragraph), 0)
        for pidx in range(between_start, between_end):
            if pidx < len(paragraphs) and OR_PATTERN.match(paragraphs[pidx].text.strip()):
                choice_group_counter += 1
                group_id = f"OR_{choice_group_counter}"
                current.choice_group = group_id
                next_cand.choice_group = group_id
                logger.debug(f"Detected OR choice group {group_id} between "
                             f"Q{current.question_number} and Q{next_cand.question_number}")
                break

    logger.info(f"Detected {len(main_candidates)} main questions, "
                f"{len(sub_candidates)} subquestions")
    return all_candidates
