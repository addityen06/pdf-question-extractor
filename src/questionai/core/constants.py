"""
QuestionAI — Constants
=======================
Shared constants, patterns, and keyword lists used across the extraction pipeline.
"""

from __future__ import annotations

import re

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = "1.0.0"

# ═══════════════════════════════════════════════════════════════════════════════
# FILENAME PARSING
# ═══════════════════════════════════════════════════════════════════════════════

# Master regex for VIT structured filenames:
#   CAT-1_2025-2026_Fall_Semester_D1_Vellore_85f84318.pdf
#   Model_CAT-1_2023-2024_Fall_Semester_A1_Vellore_a03f5c22.pdf
#   FAT_2023-2024_Winter_Semester_D1_Vellore_AnsKey_a03f5dc7.pdf
FILENAME_PATTERN = re.compile(
    r"^(?P<exam_type>(?:Model_)?(?:CAT-[12]|FAT))"
    r"_(?P<year>\d{4}-\d{4})"
    r"_(?P<semester>Fall|Winter|Summer)_Semester"
    r"_(?P<slot>[A-Za-z0-9+]+)"
    r"_(?P<campus>[A-Za-z]+)"
    r"(?:_AnsKey)?"
    r"_(?P<hash>[0-9a-fA-F]+)"
    r"\.pdf$"
)

ANSWER_KEY_MARKER = "_AnsKey_"

# Valid exam type strings
EXAM_TYPES = {"CAT-1", "CAT-2", "FAT", "Model_CAT-1", "Model_CAT-2", "Model_FAT"}

# Valid semester strings
SEMESTERS = {"Fall_Semester", "Winter_Semester", "Summer_Semester"}

# Known campuses
CAMPUSES = {"Vellore", "Chennai"}

# ═══════════════════════════════════════════════════════════════════════════════
# ADMINISTRATIVE CONTENT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Keywords that indicate administrative / non-question content.
# These are checked case-insensitively.
ADMIN_KEYWORDS = [
    "vellore institute of technology",
    "vit",
    "school of",
    "continuous assessment test",
    "final assessment test",
    "assessment test",
    "programme name",
    "course code",
    "course name",
    "faculty name",
    "class number",
    "class nbr",
    "date of examination",
    "exam duration",
    "maximum marks",
    "max. marks",
    "max marks",
    "time allowed",
    "slot:",
    "keeping mobile phone",
    "mobile phone",
    "exam malpractice",
    "electronic gadgets",
    "don't write anything",
    "do not write",
    "registration number",
    "reg. no",
    "student name",
    "hall ticket",
    "seat number",
    "answer all",
    "answer any",
    "instructions:",
    "note:",
    "important:",
    "co statements",
    "course outcomes",
]

# Regex patterns for admin lines
ADMIN_PATTERNS = [
    re.compile(r"page\s+\d+\s*(of\s+\d+)?", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),                              # Bare page numbers
    re.compile(r"VL\d{10,}", re.IGNORECASE),                 # VIT class numbers
    re.compile(r"^\s*-\s*\d+\s*-\s*$"),                      # Page separator lines
]

# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION NUMBER PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Main question number patterns (compiled for speed).
# Each returns named group 'qnum'.
QUESTION_PATTERNS = [
    # "Question 1" or "QUESTION 1"
    re.compile(r"^\s*question\s+(?P<qnum>\d+)", re.IGNORECASE),
    # "Q.1" or "Q1" or "Q. 1" or "Q 1"
    re.compile(r"^\s*Q\.?\s*(?P<qnum>\d+)", re.IGNORECASE),
    # "1." or "1)" at start of line (with possible leading whitespace)
    re.compile(r"^\s*(?P<qnum>\d{1,2})\s*[.)]\s"),
    # "1 " at start of line followed by uppercase or opening paren — careful to avoid
    # matching random numbers.  Requires the text after to look like a question start.
    re.compile(r"^\s*(?P<qnum>\d{1,2})\s+[A-Z(\"']"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# SUBQUESTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Each returns named groups 'qnum' (optional parent) and 'sub'.
SUBQUESTION_PATTERNS = [
    # "3(a)" or "3 (a)" or "3. (a)"
    re.compile(r"^\s*(?P<qnum>\d{1,2})\s*\.?\s*\(\s*(?P<sub>[a-z])\s*\)"),
    # "3. a)" or "3 a)"
    re.compile(r"^\s*(?P<qnum>\d{1,2})\s*\.?\s+(?P<sub>[a-z])\s*\)"),
    # "(a)" standalone (parent inferred from context)
    re.compile(r"^\s*\(\s*(?P<sub>[a-z])\s*\)"),
    # "a)" standalone
    re.compile(r"^\s*(?P<sub>[a-z])\s*\)"),
    # "(i)" "(ii)" "(iii)" "(iv)" roman numeral subquestions
    re.compile(r"^\s*\(\s*(?P<sub>[ivxlc]+)\s*\)"),
    # "i)" "ii)" standalone roman
    re.compile(r"^\s*(?P<sub>[ivx]+)\s*\)"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MARKS PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns to detect marks allocation near a question.
MARKS_PATTERNS = [
    re.compile(r"\[(?P<marks>\d{1,3})\]"),                 # [10]
    re.compile(r"\(\s*(?P<marks>\d{1,3})\s*marks?\s*\)", re.IGNORECASE),  # (10 marks)
    re.compile(r"\(\s*(?P<marks>\d{1,3})\s*M\s*\)"),       # (10M)
    re.compile(r"(?P<marks>\d{1,3})\s*marks?\b", re.IGNORECASE),  # 10 marks
    re.compile(r"\(\s*(?P<marks>\d{1,3})\s*\)"),            # (10) — ambiguous, low priority
    re.compile(r"(?:marks?|score)\s*[:=]\s*(?P<marks>\d{1,3})", re.IGNORECASE),
]

# Max marks detection in header/metadata
MAX_MARKS_PATTERNS = [
    re.compile(r"max(?:imum)?\s*\.?\s*marks?\s*[:=]?\s*(?P<marks>\d{2,3})", re.IGNORECASE),
    re.compile(r"total\s*marks?\s*[:=]?\s*(?P<marks>\d{2,3})", re.IGNORECASE),
]

# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT TYPE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Math / equation indicators
MATH_SYMBOLS = set("∫∑∏√∞≤≥≠∈∀∃∂∇∆≈≡∝±×÷∧∨¬⊂⊃⊆⊇∩∪αβγδεζηθικλμνξπρστυφχψω"
                   "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ")

MATH_KEYWORDS = [
    "integral", "derivative", "differentiate", "integrate", "summation",
    "limit", "matrix", "determinant", "eigenvalue", "eigenvector",
    "laplace", "fourier", "taylor", "maclaurin", "partial derivative",
    "gradient", "divergence", "curl", "evaluate", "solve the equation",
    "prove that", "show that", "find the value",
]

# Programming language keywords (for code block detection)
CODE_KEYWORDS = {
    "c": ["#include", "printf", "scanf", "int main", "void main", "malloc",
          "free(", "sizeof", "struct ", "typedef", "->"],
    "cpp": ["cout", "cin", "std::", "namespace", "class ", "template",
            "#include <iostream>", "virtual", "override"],
    "java": ["public class", "public static void main", "System.out",
             "import java", "extends ", "implements "],
    "python": ["def ", "import ", "from ", "print(", "class ",
               "if __name__", "self.", "elif ", "lambda "],
    "sql": ["SELECT ", "FROM ", "WHERE ", "INSERT ", "UPDATE ", "DELETE ",
            "CREATE TABLE", "ALTER TABLE", "JOIN ", "GROUP BY"],
}

# All code keywords flattened
ALL_CODE_KEYWORDS = [kw for lang_kws in CODE_KEYWORDS.values() for kw in lang_kws]

# Syntax characters common in code
CODE_SYNTAX_CHARS = set("{}[];->==!=&&||<<>>#")

# Monospace font name fragments
MONOSPACE_FONTS = [
    "courier", "consolas", "mono", "menlo", "source code",
    "dejavu sans mono", "liberation mono", "fira code", "inconsolata",
    "cascadia", "jetbrains",
]

# ═══════════════════════════════════════════════════════════════════════════════
# OR / CHOICE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

OR_PATTERN = re.compile(r"^\s*(?:OR|or|Or)\s*$")

# ═══════════════════════════════════════════════════════════════════════════════
# CO / BL ANNOTATION PATTERNS (Course Outcomes, Bloom's Levels)
# ═══════════════════════════════════════════════════════════════════════════════

CO_PATTERN = re.compile(r"\bCO\s*(\d)\b")
BL_PATTERN = re.compile(r"\bBL\s*(\d)\b")
