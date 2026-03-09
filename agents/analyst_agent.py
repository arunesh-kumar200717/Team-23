"""
agents/analyst_agent.py – Agent B: ANALYST AGENT

Responsibilities
----------------
• Receive the ScoutReport produced by Agent A
• Perform price comparison, trend detection, opportunity analysis
• Run sentiment analysis on competitor reviews
• Use LangChain + Ollama (llama3) to generate a business-intelligence report
• Gracefully fall back to a rule-based report when the LLM is unavailable
"""
from __future__ import annotations

import json
import logging
import statistics
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_llm():
    """
    Lazy-import and return an Ollama LLM instance.
    Returns None if Ollama is not reachable so the agent can fall back.
    """
    try:
        import requests as _req
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        # Quick connectivity check
        _req.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.4)
    except Exception as exc:
        logger.warning("Ollama unavailable (%s) – using rule-based analysis.", exc)
        return None


class AnalystAgent:
    """
    Agent B – Analyses ScoutReport and produces a BusinessIntelligenceReport.

    Usage::

        agent  = AnalystAgent()
        report = agent.run(scout_report)
    """

    _ANALYSIS_PROMPT = """You are a senior market analyst for the Indian clothing industry.
A scout agent has collected the following competitor intelligence data:

{scout_summary}

The user runs a clothing business with the following profile:
- Business: {business_name}
- Category: {clothing_category}
- City: {city}
- Avg. Price Range: {avg_price_range}

Please provide a detailed business intelligence report with:
1. Price Comparison Analysis (Where does the user stand vs competitors?)
2. Competitor Strengths and Weaknesses
3. Trending Clothing Categories to target
4. Key Threats to the user's business
5. Top 3 Opportunities the user should act on immediately

Be specific, actionable, and concise. Format your response with clear section headers."""

    # ──────────────────────────  MAIN ENTRY  ─────────────────────────────────

    def run(self, scout_report: Dict, user_data: Optional[Dict] = None) -> Dict:
        """
        Analyse scout data and return a BusinessIntelligenceReport dict.

        Report structure
        ----------------
        {
            "price_comparison": {...},
            "sentiment_summary": {...},
            "trending_categories": [...],
            "threats": [...],
            "opportunities": [...],
            "competitor_analysis": [...],
            "llm_report": str,          # full AI-generated narrative
            "llm_available": bool,
        }
        """
        logger.info("Analyst Agent starting analysis…")

        user_data = user_data or {}
        competitors = scout_report.get("competitors", [])

        price_comp   = self._price_comparison(competitors, user_data)
        sentiment    = self._sentiment_summary(competitors)
        trending     = self._detect_trending_categories(scout_report)
        threats      = self._identify_threats(competitors)
        opps         = self._identify_opportunities(competitors, trending)
        comp_analysis = self._analyse_competitors(competitors)

        llm     = _get_llm()
        llm_txt = ""
        llm_ok  = False

        if llm:
            llm_txt = self._run_llm_analysis(
                llm, scout_report, user_data,
                price_comp, sentiment, trending, threats, opps,
            )
            llm_ok = True
        else:
            llm_txt = self._rule_based_report(
                price_comp, sentiment, trending, threats, opps, user_data
            )

        report = {
            "price_comparison":   price_comp,
            "sentiment_summary":  sentiment,
            "trending_categories": trending,
            "threats":            threats,
            "opportunities":      opps,
            "competitor_analysis": comp_analysis,
            "llm_report":         llm_txt,
            "llm_available":      llm_ok,
        }
        logger.info("Analyst Agent complete (LLM=%s).", llm_ok)
        return report

    # ──────────────────────────  ANALYSIS METHODS  ───────────────────────────

    def _price_comparison(
        self, competitors: List[Dict], user_data: Dict
    ) -> Dict:
        """Compute avg price per competitor and flag cheap / expensive."""
        results: List[Dict] = []
        all_prices: List[float] = []

        for comp in competitors:
            prices = [
                p["price"] for p in comp.get("products", []) if p.get("price", 0) > 0
            ]
            if prices:
                avg = round(statistics.mean(prices), 2)
                mn  = min(prices)
                mx  = max(prices)
            else:
                avg = mn = mx = 0.0
            all_prices.append(avg)
            results.append(
                {
                    "competitor": comp["competitor_name"],
                    "avg_price":  avg,
                    "min_price":  mn,
                    "max_price":  mx,
                    "products_count": len(prices),
                }
            )

        market_avg = round(statistics.mean(all_prices), 2) if all_prices else 0.0

        # Try parsing user's price range, e.g. "₹500 – ₹2000"
        try:
            import re
            nums = re.findall(r"\d+", str(user_data.get("avg_price_range", "")))
            user_avg = round(statistics.mean([float(n) for n in nums]), 2) if nums else market_avg
        except Exception:
            user_avg = market_avg

        positioning = (
            "Below Market Average" if user_avg < market_avg * 0.9
            else "Above Market Average" if user_avg > market_avg * 1.1
            else "Market Average"
        )

        return {
            "competitors":    results,
            "market_avg":     market_avg,
            "user_avg":       user_avg,
            "positioning":    positioning,
        }

    def _sentiment_summary(self, competitors: List[Dict]) -> Dict:
        total = {"positive": 0, "neutral": 0, "negative": 0}
        per_comp: List[Dict] = []

        for comp in competitors:
            counts = {"positive": 0, "neutral": 0, "negative": 0}
            ratings: List[float] = []
            for review in comp.get("reviews", []):
                label = (review.get("sentiment_label") or "neutral").lower()
                counts[label] = counts.get(label, 0) + 1
                total[label]  = total.get(label, 0) + 1
                if review.get("rating"):
                    ratings.append(review["rating"])
            per_comp.append(
                {
                    "competitor": comp["competitor_name"],
                    "counts":     counts,
                    "avg_rating": round(statistics.mean(ratings), 2) if ratings else 0,
                }
            )

        return {"total": total, "per_competitor": per_comp}

    def _detect_trending_categories(self, scout_report: Dict) -> List[str]:
        topics = [t["topic"] for t in scout_report.get("trending_topics", [])]
        # Also look at what competitors are launching
        for comp in scout_report.get("competitors", []):
            for item in comp.get("new_launches", []):
                cat = item.get("cat", "")
                if cat and cat not in topics:
                    topics.append(cat.replace("_", " ").title())
        return topics[:10]

    def _identify_threats(self, competitors: List[Dict]) -> List[str]:
        threats: List[str] = []
        for comp in competitors:
            name = comp["competitor_name"]
            if comp.get("active_campaigns"):
                threats.append(
                    f"{name} is running {len(comp['active_campaigns'])} active campaigns."
                )
            if len(comp.get("new_launches", [])) >= 2:
                threats.append(
                    f"{name} launched {len(comp['new_launches'])} new products recently."
                )
            if len(comp.get("discounted_items", [])) >= 3:
                threats.append(
                    f"{name} is offering heavy discounts – could divert your customers."
                )
        return threats[:8] if threats else ["No immediate major threats detected."]

    def _identify_opportunities(
        self, competitors: List[Dict], trending: List[str]
    ) -> List[str]:
        opps: List[str] = []

        # Low-sentiment competitors → opportunity to win their unhappy customers
        for comp in competitors:
            neg_reviews = [
                r for r in comp.get("reviews", [])
                if r.get("sentiment_label") == "negative"
            ]
            if len(neg_reviews) >= 3:
                opps.append(
                    f"{comp['competitor_name']} has {len(neg_reviews)} negative reviews "
                    "– improve your service/quality to capture dissatisfied customers."
                )

        # Trending categories not yet covered heavily by any competitor
        if trending:
            opps.append(
                f"Trending categories to launch: {', '.join(trending[:3])}."
            )

        opps.append("Run an Instagram reel campaign with trending hashtags to boost visibility.")
        opps.append("Introduce a loyalty programme to retain repeat customers.")
        opps.append("Bundle offers (e.g., Kurta + Dupatta combo) can increase basket size.")
        return opps[:6]

    def _analyse_competitors(self, competitors: List[Dict]) -> List[Dict]:
        results: List[Dict] = []
        for comp in competitors:
            pos_rev = sum(
                1 for r in comp.get("reviews", []) if r.get("sentiment_label") == "positive"
            )
            total_rev = len(comp.get("reviews", []))
            sat_pct = round(pos_rev / max(total_rev, 1) * 100, 1)
            results.append(
                {
                    "name":          comp["competitor_name"],
                    "category":      comp.get("category", ""),
                    "new_launches":  len(comp.get("new_launches", [])),
                    "discounts":     len(comp.get("discounted_items", [])),
                    "campaigns":     len(comp.get("active_campaigns", [])),
                    "satisfaction":  sat_pct,
                    "social_handle": comp.get("social", {}).get("instagram_handle", ""),
                    "followers":     comp.get("social", {}).get("followers", 0),
                }
            )
        return results

    # ──────────────────────────  LLM METHODS  ────────────────────────────────

    def _run_llm_analysis(
        self, llm, scout_report: Dict, user_data: Dict,
        price_comp: Dict, sentiment: Dict,
        trending: List[str], threats: List[str], opps: List[str],
    ) -> str:
        try:
            from langchain_core.prompts import PromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            scout_summary = json.dumps(
                {
                    "competitors_count": len(scout_report.get("competitors", [])),
                    "new_launches": sum(
                        len(c["new_launches"]) for c in scout_report.get("competitors", [])
                    ),
                    "price_comparison": price_comp,
                    "sentiment": sentiment["total"],
                    "trending": trending[:5],
                    "threats": threats[:4],
                    "opportunities": opps[:4],
                },
                indent=2,
            )

            prompt = PromptTemplate(
                template=self._ANALYSIS_PROMPT,
                input_variables=[
                    "scout_summary", "business_name",
                    "clothing_category", "city", "avg_price_range",
                ],
            )
            chain  = prompt | llm | StrOutputParser()
            result = chain.invoke(
                {
                    "scout_summary":      scout_summary,
                    "business_name":      user_data.get("business_name", "Your Business"),
                    "clothing_category":  user_data.get("clothing_category", "Clothing"),
                    "city":               user_data.get("city", "Coimbatore"),
                    "avg_price_range":    user_data.get("avg_price_range", "Mid Range"),
                }
            )
            return str(result)
        except Exception as exc:
            logger.error("LLM analysis error: %s", exc)
            return self._rule_based_report(
                price_comp, sentiment, trending, threats, opps, user_data
            )

    @staticmethod
    def _rule_based_report(
        price_comp: Dict,
        sentiment: Dict,
        trending: List[str],
        threats: List[str],
        opps: List[str],
        user_data: Dict,
    ) -> str:
        business = user_data.get("business_name", "Your Business")
        cat      = user_data.get("clothing_category", "clothing")
        pos      = price_comp.get("positioning", "Market Average")

        lines = [
            f"## Market Intelligence Report for {business}",
            "",
            "### Price Comparison",
            f"Your average pricing is **{pos}** relative to competitors. "
            f"Market average: ₹{price_comp.get('market_avg', 0):,.0f}  |  "
            f"Your estimate: ₹{price_comp.get('user_avg', 0):,.0f}",
            "",
            "### Sentiment Overview",
            f"Competitor reviews – Positive: {sentiment['total'].get('positive', 0)}, "
            f"Neutral: {sentiment['total'].get('neutral', 0)}, "
            f"Negative: {sentiment['total'].get('negative', 0)}",
            "",
            "### Trending Categories",
            "• " + "\n• ".join(trending[:5] or ["No specific trends detected."]),
            "",
            "### Threats",
            "• " + "\n• ".join(threats[:4]),
            "",
            "### Opportunities",
            "• " + "\n• ".join(opps[:4]),
            "",
            "### Recommendation",
            (
                f"Focus on expanding your {cat} range with trending styles. "
                "Leverage competitor weaknesses by highlighting quality and service. "
                "Run an Instagram campaign using top trending hashtags to boost awareness."
            ),
        ]
        return "\n".join(lines)
