"""
orchestrator.py

Manages the end-to-end multi-agent pipeline:

    Scout Agent  (A)
        ↓  ScoutReport
    Analyst Agent (B)
        ↓  AnalysisReport
    Strategist Agent (C)
        ↓  StrategyReport  + WhatsApp alerts + DB alerts

Usage from code
---------------
    from orchestrator import run_pipeline
    result = run_pipeline(user_id=1, user_data={...}, competitors=[...])

Usage from CLI (for testing)
-----------------------------
    python orchestrator.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

from agents.analyst_agent import AnalystAgent
from agents.scout_agent import ScoutAgent
from agents.strategist_agent import StrategistAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_pipeline(
    user_id: int,
    user_data: Optional[Dict] = None,
    competitors: Optional[List[Dict]] = None,
    send_whatsapp: bool = False,
) -> Dict:
    """
    Execute Scout → Analyst → Strategist and return a combined result dict.

    Parameters
    ----------
    user_id        : DB id of the logged-in user
    user_data      : User profile dict (business_name, city, etc.)
    competitors    : List of competitor dicts (name, website, category, …)
    send_whatsapp  : Whether to fire WhatsApp notifications

    Returns
    -------
    {
        "scout":    ScoutReport,
        "analysis": AnalysisReport,
        "strategy": StrategyReport,
        "pipeline_duration_s": float,
        "completed_at": str,
    }
    """
    start = datetime.now()
    user_data   = user_data   or {}
    competitors = competitors or []

    logger.info("=== Pipeline START (user_id=%s) ===", user_id)

    # ── STEP 1: Scout ──────────────────────────────────────────────────────
    logger.info("[1/3] Scout Agent running…")
    scout_agent = ScoutAgent(user_id=user_id, competitors=competitors)
    scout_report = scout_agent.run()
    logger.info(
        "[1/3] Scout done: %d competitors, %d new launches, %d discounts",
        scout_report["summary"]["total_competitors"],
        scout_report["summary"]["total_new_launches"],
        scout_report["summary"]["total_discounts"],
    )

    # ── STEP 2: Analyst ────────────────────────────────────────────────────
    logger.info("[2/3] Analyst Agent running…")
    analyst_agent = AnalystAgent()
    analysis_report = analyst_agent.run(
        scout_report = scout_report,
        user_data    = user_data,
    )
    logger.info(
        "[2/3] Analysis done: %d threats, %d opportunities (LLM=%s)",
        len(analysis_report.get("threats", [])),
        len(analysis_report.get("opportunities", [])),
        analysis_report.get("llm_available"),
    )

    # ── STEP 3: Strategist ─────────────────────────────────────────────────
    logger.info("[3/3] Strategist Agent running…")
    strategist_agent = StrategistAgent(user_id=user_id)
    strategy_report = strategist_agent.run(
        analysis_report = analysis_report,
        scout_report    = scout_report,
        user_data       = user_data,
        send_whatsapp   = send_whatsapp,
    )
    logger.info(
        "[3/3] Strategy done: %d alerts sent (LLM=%s)",
        strategy_report.get("alerts_sent", 0),
        strategy_report.get("llm_available"),
    )

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=== Pipeline COMPLETE in %.1fs ===", elapsed)

    return {
        "scout":               scout_report,
        "analysis":            analysis_report,
        "strategy":            strategy_report,
        "pipeline_duration_s": round(elapsed, 2),
        "completed_at":        datetime.now().isoformat(),
    }


# ─────────────────────────────  CLI RUNNER  ──────────────────────────────────

if __name__ == "__main__":
    from database.db import initialize_database
    from config import SAMPLE_COMPETITORS

    initialize_database()

    # Use a demo user so CLI works without a real login
    sample_user = {
        "id":               1,
        "business_name":    "Demo Textiles",
        "city":             "Coimbatore",
        "shop_type":        "Retail Store",
        "clothing_category":"Ethnic Wear",
        "avg_price_range":  "Mid Range (₹700 – ₹1999)",
    }

    print("\n── Running Multi-Agent Pipeline (CLI mode) ──\n")
    result = run_pipeline(
        user_id       = 1,
        user_data     = sample_user,
        competitors   = SAMPLE_COMPETITORS,
        send_whatsapp = False,
    )

    print("\n── Scout Summary ──")
    print(json.dumps(result["scout"]["summary"], indent=2))

    print("\n── Analysis Threats ──")
    for t in result["analysis"].get("threats", [])[:3]:
        print(f"  • {t}")

    print("\n── Strategy Highlights ──")
    for idea in result["strategy"].get("product_ideas", [])[:3]:
        print(f"  • {idea}")

    print(f"\nPipeline completed in {result['pipeline_duration_s']}s")
