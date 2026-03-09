"""
brochure_analysis/brochure_reader.py

Extracts text and intelligence from competitor marketing brochures.

Supported formats
-----------------
• PDF  – via PyPDF2
• Images (JPG / PNG / TIFF / BMP) – via pytesseract OCR
• Plain text – passthrough

After extraction the text is analysed by:
1. A keyword-based rule engine (always available)
2. Ollama llama3 via LangChain (when available)

The module is intentionally self-contained so it can be imported
independently of the agent pipeline.
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────  CLOTHING KEYWORDS  ────────────────────────────

_PRODUCT_KEYWORDS = [
    "saree", "kurta", "kurti", "lehenga", "suit", "salwar", "dupatta",
    "dress", "gown", "jacket", "jeans", "shirt", "top", "skirt",
    "hoodie", "blazer", "palazzo", "anarkali", "churidar",
    "sharara", "coord set", "ethnic", "western", "casual", "formal",
    "cotton", "silk", "linen", "chiffon", "georgette", "velvet",
]

_PROMO_KEYWORDS = [
    "sale", "discount", "off", "offer", "free", "buy", "combo", "deal",
    "limited", "exclusive", "festive", "clearance", "flash", "savings",
    "% off", "flat off", "upto", "up to", "special price", "today only",
    "new arrival", "new launch", "fresh stock", "just in",
]

_LLM_PROMPT = """You are an expert retail analyst for the Indian clothing industry.

Analyse the following text extracted from a competitor's marketing brochure:

---
{brochure_text}
---

Provide a structured report with:
1. **Key Products Promoted** (list each with price if mentioned)
2. **Promotional Offers Detected** (discounts, combos, free gifts)
3. **Target Audience** (inferred from the brochure)
4. **Overall Marketing Theme / Campaign**
5. **Suggestions for the User's Business** (3–5 specific, actionable ideas)

Be concise and practical. Focus on actionable intelligence."""


def _get_llm():
    try:
        import requests as _req
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        _req.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.3)
    except Exception as exc:
        logger.warning("Ollama unavailable for brochure analysis: %s", exc)
        return None


class BrochureReader:
    """Extract text and market intelligence from competitor brochures."""

    # ──────────────────────────  PUBLIC API  ─────────────────────────────────

    def analyse(
        self,
        file_bytes: bytes,
        filename: str,
        user_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Full analysis pipeline for an uploaded brochure file.

        Returns
        -------
        {
            "filename": str,
            "file_type": str,
            "extracted_text": str,
            "products_detected": List[str],
            "promos_detected": List[str],
            "analysis_result": str,   # detailed narrative
            "suggestions": str,       # bullet-point suggestions
            "llm_available": bool,
        }
        """
        suffix    = Path(filename).suffix.lower()
        file_type = self._classify(suffix)

        extracted = self._extract_text(file_bytes, suffix)
        if not extracted.strip():
            extracted = "(No readable text could be extracted from this file.)"

        products, promos = self._keyword_extract(extracted)
        analysis, suggestions, llm_ok = self._analyse_text(
            extracted, products, promos, user_data or {}
        )

        return {
            "filename":         filename,
            "file_type":        file_type,
            "extracted_text":   extracted[:3000],   # persist first 3 k chars
            "products_detected": products,
            "promos_detected":   promos,
            "analysis_result":  analysis,
            "suggestions":      suggestions,
            "llm_available":    llm_ok,
        }

    # ──────────────────────────  TEXT EXTRACTION  ────────────────────────────

    def _extract_text(self, data: bytes, suffix: str) -> str:
        if suffix == ".pdf":
            return self._extract_pdf(data)
        if suffix in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}:
            return self._extract_image(data)
        if suffix in {".txt", ".csv"}:
            return data.decode("utf-8", errors="replace")
        # Generic attempt – treat as UTF-8 text
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_pdf(data: bytes) -> str:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            pages  = [p.extract_text() or "" for p in reader.pages]
            return "\n".join(pages)
        except Exception as exc:
            logger.error("PDF extraction error: %s", exc)
            return ""

    @staticmethod
    def _extract_image(data: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
            img  = Image.open(io.BytesIO(data))
            text = pytesseract.image_to_string(img, lang="eng")
            return text
        except Exception as exc:
            logger.error("OCR extraction error: %s", exc)
            return "(OCR failed – ensure Tesseract is installed and on PATH.)"

    # ──────────────────────────  KEYWORD ENGINE  ─────────────────────────────

    @staticmethod
    def _keyword_extract(text: str) -> Tuple[List[str], List[str]]:
        lower = text.lower()

        products: List[str] = []
        for kw in _PRODUCT_KEYWORDS:
            if kw in lower:
                # Extract a snippet of context around the keyword
                idx = lower.find(kw)
                snippet = text[max(0, idx - 20): idx + 50].strip()
                snippet = re.sub(r"\s+", " ", snippet)
                if snippet not in products:
                    products.append(snippet)

        promos: List[str] = []
        for kw in _PROMO_KEYWORDS:
            if kw in lower:
                idx = lower.find(kw)
                snippet = text[max(0, idx - 15): idx + 60].strip()
                snippet = re.sub(r"\s+", " ", snippet)
                if snippet not in promos:
                    promos.append(snippet)

        return products[:10], promos[:10]

    # ──────────────────────────  ANALYSIS  ───────────────────────────────────

    def _analyse_text(
        self,
        text: str,
        products: List[str],
        promos: List[str],
        user_data: Dict,
    ) -> Tuple[str, str, bool]:
        """Return (analysis_narrative, suggestions, llm_used)."""
        llm = _get_llm()
        if llm:
            try:
                analysis   = self._llm_analysis(llm, text[:2000])
                suggestions = self._extract_suggestions_from_llm(analysis, user_data)
                return analysis, suggestions, True
            except Exception as exc:
                logger.error("LLM brochure analysis failed: %s", exc)

        # Rule-based fallback
        return self._rule_analysis(products, promos, user_data), \
               self._rule_suggestions(products, promos, user_data), \
               False

    def _llm_analysis(self, llm, text: str) -> str:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        prompt = PromptTemplate(
            template=_LLM_PROMPT, input_variables=["brochure_text"]
        )
        chain  = prompt | llm | StrOutputParser()
        return str(chain.invoke({"brochure_text": text}))

    @staticmethod
    def _extract_suggestions_from_llm(analysis: str, user_data: Dict) -> str:
        """Pull out the suggestions section from LLM output, or return the tail."""
        lower = analysis.lower()
        for marker in ["suggestions", "recommendation", "action"]:
            idx = lower.find(marker)
            if idx != -1:
                return analysis[idx:]
        return analysis[-800:] if len(analysis) > 800 else analysis

    @staticmethod
    def _rule_analysis(
        products: List[str], promos: List[str], user_data: Dict
    ) -> str:
        p_list = "\n".join(f"  • {p}" for p in products) or "  • (none detected)"
        pr_list = "\n".join(f"  • {p}" for p in promos) or "  • (none detected)"
        return (
            "## Brochure Analysis Report\n\n"
            "### Products / Clothing Items Mentioned\n"
            f"{p_list}\n\n"
            "### Promotional Offers Detected\n"
            f"{pr_list}\n\n"
            "### Summary\n"
            "The brochure highlights competitor product offerings and current promotions. "
            "Review the suggestions below for recommended responses."
        )

    @staticmethod
    def _rule_suggestions(
        products: List[str], promos: List[str], user_data: Dict
    ) -> str:
        cat  = user_data.get("clothing_category", "clothing")
        city = user_data.get("city", "your city")
        sug  = [
            f"Competitor is actively promoting {cat.lower()} – consider launching a fresh collection.",
        ]
        if promos:
            sug.append(
                "Competitor is running discounts. Counter with a 'Quality Guarantee' campaign."
            )
        sug += [
            f"Increase your digital presence in {city} through Instagram Reels.",
            "Create a WhatsApp status / broadcast featuring your latest arrivals.",
            "Introduce a loyalty card / app to retain customers who might be targeted by the competitor.",
        ]
        return "\n".join(f"• {s}" for s in sug)

    # ──────────────────────────  HELPERS  ────────────────────────────────────

    @staticmethod
    def _classify(suffix: str) -> str:
        if suffix == ".pdf":
            return "PDF"
        if suffix in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}:
            return "Image"
        return "Text"
