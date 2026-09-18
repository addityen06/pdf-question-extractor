from __future__ import annotations

import logging
import re
from questionai.core.models import ParagraphBlock, ContentBlock, BlockType
from questionai.core.constants import MATH_SYMBOLS, MATH_KEYWORDS

logger = logging.getLogger(__name__)

# Common symbol replacements to LaTeX
LATEX_REPLACEMENTS = [
    ('²', '^2'), ('³', '^3'), ('⁴', '^4'), ('ⁿ', '^n'),
    ('₁', '_1'), ('₂', '_2'), ('₃', '_3'), ('ᵢ', '_i'), ('ₙ', '_n'),
    ('∫', r'\int '), ('∑', r'\sum '), ('∏', r'\prod '),
    ('√', r'\sqrt'), ('∞', r'\infty '), ('≤', r'\le '), ('≥', r'\ge '),
    ('≠', r'\ne '), ('±', r'\pm '), ('×', r'\times '), ('÷', r'\div '),
    ('∂', r'\partial '), ('∇', r'\nabla '), ('∆', r'\Delta '),
    ('α', r'\alpha '), ('β', r'\beta '), ('γ', r'\gamma '), ('δ', r'\delta '),
    ('ε', r'\epsilon '), ('θ', r'\theta '), ('λ', r'\lambda '), ('μ', r'\mu '),
    ('π', r'\pi '), ('σ', r'\sigma '), ('τ', r'\tau '), ('φ', r'\phi '),
    ('ω', r'\omega '), ('∈', r'\in '), ('∉', r'\notin '), ('⊂', r'\subset '),
    ('⊆', r'\subseteq '), ('∪', r'\cup '), ('∩', r'\cap ')
]


def detect_equations(paragraphs: list[ParagraphBlock]) -> list[tuple[int, ContentBlock]]:
    """
    Detect mathematical equations and matrices in paragraphs.
    """
    detected: list[tuple[int, ContentBlock]] = []
    
    for i, para in enumerate(paragraphs):
        text = (para.text or "").strip()
        if not text:
            continue
            
        score = 0
        
        # 1. Math symbols count
        sym_count = sum(1 for sym in MATH_SYMBOLS if sym in text)
        if sym_count >= 2:
            score += 3
        elif sym_count == 1:
            score += 1
            
        # 2. Math keywords
        for kw in MATH_KEYWORDS:
            if kw.lower() in text.lower():
                score += 1
                break
                
        # 3. Math equation patterns (e.g. f(x) =, y =, dy/dx, \int, matrices)
        if re.search(r'\b[a-zA-Z]\s*\([a-zA-Z0-9,\s]+\)\s*=', text):
            score += 2
        if re.search(r'd[yx]/d[tx]|dy/dx|\b\d+x\s*[+\-=]', text):
            score += 2
        if re.search(r'\[\s*\d+\s+\d+.*\]', text, re.DOTALL): # Matrix like
            score += 3
            
        # If score indicates strong math content and paragraph is formula-focused
        if score >= 3:
            latex_text = text
            for orig, rep in LATEX_REPLACEMENTS:
                latex_text = latex_text.replace(orig, rep)
                
            # Handle matrices if grid of numbers in brackets
            if '[' in latex_text and ']' in latex_text and any(c.isdigit() for c in latex_text):
                lines = [l.strip() for l in latex_text.splitlines() if l.strip()]
                if len(lines) >= 2 and all(len(re.findall(r'\d+', l)) >= 2 for l in lines):
                    matrix_rows = []
                    for l in lines:
                        cleaned_l = l.replace('[', '').replace(']', '').strip()
                        matrix_rows.append(' & '.join(cleaned_l.split()))
                    latex_text = r"\begin{bmatrix} " + r" \\ ".join(matrix_rows) + r" \end{bmatrix}"
                    
            block = ContentBlock(
                type=BlockType.EQUATION,
                content=text,
                latex=latex_text,
                confidence=0.85,
                source_page=para.page,
                source_bbox=para.bbox
            )
            detected.append((i, block))
            
    return detected
