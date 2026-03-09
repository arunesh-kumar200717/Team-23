"""
agents/strategist_agent.py – Agent C: STRATEGIST AGENT

Responsibilities
----------------
• Receive the AnalysisReport produced by Agent B
• Generate a complete marketing strategy using LangChain + Ollama (llama3)
• Produce Instagram captions & WhatsApp promotional messages
• Trigger WhatsApp alerts via the notification module
• Persist all alerts to the database
"""
from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional

from config import CLOTHING_HASHTAGS
from database import db
from notifications.whatsapp_alert import WhatsAppAlert

logger = logging.getLogger(__name__)


def _get_llm():
    try:
        import requests as _req
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        _req.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.7)
    except Exception as exc:
        logger.warning("Ollama unavailable (%s) – using template-based strategy.", exc)
        return None


class StrategistAgent:
    """
    Agent C – Generates actionable marketing strategy from the analysis report.

    Usage::

        agent  = StrategistAgent(user_id=1)
        result = agent.run(analysis_report, scout_report, user_data)
    """

    _STRATEGY_PROMPT = """You are an expert marketing strategist for Indian clothing retailers.

Business Profile:
- Business: {business_name}
- City: {city}
- Category: {clothing_category}
- Price Range: {avg_price_range}

Key Intelligence:
{intelligence_summary}

Based on this intelligence, create a comprehensive marketing strategy that includes:
1. Pricing Strategy (specific price recommendations)
2. New Product Ideas (3-5 product suggestions for this season)
3. Discount Campaign Plan (timing, percentage, products)
4. Instagram Marketing Strategy (with 3 caption examples)
5. WhatsApp Broadcast Message (ready-to-send promotional message)
6. 7-Day Action Plan

Be specific, practical, and focus on the Indian clothing market in {city}."""

    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id

    # ──────────────────────────  MAIN ENTRY  ─────────────────────────────────

    def run(
        self,
        analysis_report: Dict,
        scout_report: Dict,
        user_data: Optional[Dict] = None,
        send_whatsapp: bool = True,
    ) -> Dict:
        """
        Produce a StrategyReport and optionally fire WhatsApp alerts.

        Returns dict with keys:
            pricing_strategy, product_ideas, discount_plan,
            instagram_captions, whatsapp_message, action_plan,
            llm_strategy, alerts_sent, llm_available
        """
        logger.info("Strategist Agent starting…")
        user_data = user_data or {}

        # Build fallback / template-based content first
        pricing   = self._pricing_strategy(analysis_report, user_data)
        products  = self._product_ideas(analysis_report, user_data)
        discounts = self._discount_plan(analysis_report)
        captions  = self._instagram_captions(analysis_report, user_data)
        wa_msg    = self._whatsapp_message(scout_report, user_data)
        action    = self._action_plan(analysis_report, user_data)

        # Attempt full LLM strategy
        llm    = _get_llm()
        llm_ok = False
        llm_strategy = ""

        if llm:
            llm_strategy = self._run_llm_strategy(llm, analysis_report, user_data)
            llm_ok = bool(llm_strategy)

        if not llm_strategy:
            llm_strategy = self._compose_fallback_strategy(
                pricing, products, discounts, captions, wa_msg, action, user_data
            )

        # Save alerts to DB and optionally send via WhatsApp
        alerts_sent = self._fire_alerts(
            scout_report, user_data, wa_msg, send_whatsapp
        )

        result = {
            "pricing_strategy":  pricing,
            "product_ideas":     products,
            "discount_plan":     discounts,
            "instagram_captions": captions,
            "whatsapp_message":  wa_msg,
            "action_plan":       action,
            "llm_strategy":      llm_strategy,
            "alerts_sent":       alerts_sent,
            "llm_available":     llm_ok,
        }
        logger.info("Strategist Agent complete (LLM=%s, alerts=%d).", llm_ok, alerts_sent)
        return result

    # ──────────────────────────  STRATEGY BUILDERS  ──────────────────────────

    def _pricing_strategy(self, analysis: Dict, user_data: Dict) -> List[str]:
        pos      = analysis.get("price_comparison", {}).get("positioning", "Market Average")
        mkt_avg  = analysis.get("price_comparison", {}).get("market_avg", 1200)
        strats   = []
        if pos == "Above Market Average":
            strats += [
                f"Introduce a 'Value Collection' at \u20b9{int(mkt_avg * 0.85)}-{int(mkt_avg * 0.95)} to compete directly.",
                "Justify premium price with visible quality improvements and packaging upgrades.",
                "Offer exclusive loyalty-programme pricing for repeat customers.",
            ]
        elif pos == "Below Market Average":
            strats += [
                "Launch a 'Premium Select' range to capture higher spend customers.",
                f"Gradually increase prices by 10–15% with improved product quality.",
                "Bundle products to increase average order value.",
            ]
        else:
            strats += [
                "Maintain current pricing and differentiate on quality and service.",
                "Introduce a mid-tier 'Exclusive' line at 20–25% above current average.",
                "Offer combo deals to boost revenue without changing core prices.",
            ]
        return strats

    def _product_ideas(self, analysis: Dict, user_data: Dict) -> List[str]:
        trending = analysis.get("trending_categories", [])
        cat      = user_data.get("clothing_category", "Ethnic Wear")
        ideas = [
            f"Launch a {trending[0]} collection targeting young professionals."
            if trending else "Launch a festive ethnic fusion collection.",
            "Introduce eco-friendly / organic cotton line to ride the sustainability wave.",
            "Create a 'Budget Chic' range (₹399–₹799) to attract college students.",
            "Develop a wedding-season capsule collection (8–12 exclusive pieces).",
            f"Expand {cat} range with Indo-Western crossover styles.",
        ]
        return ideas[:5]

    def _discount_plan(self, analysis: Dict) -> List[str]:
        return [
            "Weekend Flash Sale: 20–30% off on selected items every Saturday.",
            "Early Bird Offers: First 50 customers daily get an extra 5% discount.",
            "Buy 2 Get 10% Off, Buy 3 Get 20% Off on kurta/kurti sets.",
            "Loyalty App Exclusive: 15% off for members on the first of every month.",
            "Festival Season Mega Sale: Up to 40% off in October–November.",
        ]

    def _instagram_captions(
        self, analysis: Dict, user_data: Dict
    ) -> List[str]:
        name     = user_data.get("business_name", "Our Store")
        city     = user_data.get("city", "Coimbatore")
        trending = analysis.get("trending_categories", [])
        top_tags = " ".join(random.sample(CLOTHING_HASHTAGS, min(6, len(CLOTHING_HASHTAGS))))
        trend_kw = trending[0] if trending else "Ethnic Fusion"

        return [
            (
                f"✨ Elevate your style with our new {trend_kw} collection! "
                f"Fresh arrivals just dropped at {name}, {city}. "
                f"Shop now and turn heads wherever you go! 🛍️\n{top_tags}"
            ),
            (
                f"🔥 Mega Sale Alert! Up to 40% OFF on our bestsellers. "
                f"Limited time. Limited stock. Hurry to {name} or shop online! "
                f"👗💫\n#Sale #ClothingSale {top_tags}"
            ),
            (
                f"💛 Handpicked styles for every occasion — from casual days to festive nights. "
                f"Visit {name} in {city} and find your perfect look today! "
                f"📍{city}\n{top_tags} #NewCollection"
            ),
        ]

    def _whatsapp_message(
        self, scout_report: Dict, user_data: Dict
    ) -> str:
        business = user_data.get("business_name", "Our Store")
        city     = user_data.get("city", "Coimbatore")
        comps    = scout_report.get("competitors", [])

        # Pick the most noteworthy event to highlight
        highlight = ""
        for comp in comps:
            if comp.get("active_campaigns"):
                highlight = (
                    f"🚨 *Competitor Alert!*\n"
                    f"*{comp['competitor_name']}* is running: "
                    f"_{comp['active_campaigns'][0]}_\n\n"
                )
                break

        msg = (
            f"{highlight}"
            f"👗 *{business} – Exclusive Offer!*\n\n"
            f"✅ New collection now available!\n"
            f"💰 Special discounts for this week only\n"
            f"📍 Visit us in {city}\n\n"
            f"Reply *SHOP* to know more or visit our store today!\n\n"
            f"_Unsubscribe: send STOP_"
        )
        return msg

    def _action_plan(
        self, analysis: Dict, user_data: Dict
    ) -> List[str]:
        return [
            "Day 1-2: Photograph new arrivals and prepare Instagram / WhatsApp content.",
            "Day 3:   Launch a weekend flash-sale announcement on all social platforms.",
            "Day 4-5: Send WhatsApp broadcasts to existing customer list.",
            "Day 6:   Post 3 Instagram reels showcasing trending styles.",
            "Day 7:   Review performance metrics and plan next week's campaign.",
        ]

    # ──────────────────────────  LLM  ────────────────────────────────────────

    def _run_llm_strategy(self, llm, analysis: Dict, user_data: Dict) -> str:
        try:
            import json
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import PromptTemplate

            intel = json.dumps(
                {
                    "price_positioning": analysis.get("price_comparison", {}).get("positioning"),
                    "trending":          analysis.get("trending_categories", [])[:5],
                    "threats":           analysis.get("threats", [])[:3],
                    "opportunities":     analysis.get("opportunities", [])[:3],
                    "top_negative_comps": [
                        c["name"]
                        for c in analysis.get("competitor_analysis", [])
                        if c.get("satisfaction", 100) < 60
                    ],
                },
                indent=2,
            )

            prompt = PromptTemplate(
                template=self._STRATEGY_PROMPT,
                input_variables=[
                    "business_name", "city", "clothing_category",
                    "avg_price_range", "intelligence_summary",
                ],
            )
            chain  = prompt | llm | StrOutputParser()
            return str(
                chain.invoke(
                    {
                        "business_name":      user_data.get("business_name", "Your Business"),
                        "city":               user_data.get("city", "Coimbatore"),
                        "clothing_category":  user_data.get("clothing_category", "Clothing"),
                        "avg_price_range":    user_data.get("avg_price_range", "₹500–₹2000"),
                        "intelligence_summary": intel,
                    }
                )
            )
        except Exception as exc:
            logger.error("LLM strategy error: %s", exc)
            return ""

    @staticmethod
    def _compose_fallback_strategy(
        pricing: List[str],
        products: List[str],
        discounts: List[str],
        captions: List[str],
        wa_msg: str,
        action: List[str],
        user_data: Dict,
    ) -> str:
        business = user_data.get("business_name", "Your Business")
        lines = [
            f"## Marketing Strategy for {business}",
            "",
            "### 💰 Pricing Strategy",
            "\n".join(f"• {p}" for p in pricing),
            "",
            "### 🛍️ New Product Ideas",
            "\n".join(f"• {p}" for p in products),
            "",
            "### 🏷️ Discount Campaign Plan",
            "\n".join(f"• {d}" for d in discounts),
            "",
            "### 📸 Instagram Captions",
            "\n\n---\n".join(f"*Caption {i+1}:*\n{c}" for i, c in enumerate(captions)),
            "",
            "### 💬 WhatsApp Broadcast Message",
            wa_msg,
            "",
            "### 📅 7-Day Action Plan",
            "\n".join(f"• {a}" for a in action),
        ]
        return "\n".join(lines)

    # ──────────────────────────  ALERTS  ─────────────────────────────────────

    def _fire_alerts(
        self,
        scout_report: Dict,
        user_data: Dict,
        wa_message: str,
        send_whatsapp: bool,
    ) -> int:
        user_id  = user_data.get("id")
        notifier = WhatsAppAlert()
        sent_count = 0

        if not user_id:
            return 0

        business = user_data.get("business_name", "Your Shop")
        city     = user_data.get("city", "your city")
        comps    = scout_report.get("competitors", [])

        # ── Per-competitor alerts ─────────────────────────────────────────────
        for comp in comps:
            name = comp["competitor_name"]

            # 1. New-launch alerts — one WhatsApp per product
            for item in comp.get("new_launches", []):
                product = item.get("name", "a new product")
                price   = item.get("price", 0)
                tip     = (
                    f"Consider launching a similar product with a 10% introductory "
                    f"discount to win first-mover customers in {city}."
                )
                caption = (
                    f"✨ Introducing our latest collection – crafted just for you! "
                    f"Shop now at ₹{int(price * 0.9):,} 🛍️ #NewArrival #FashionIn{city.replace(' ', '')}"
                )
                title   = f"🚀 New Launch by {name}"
                message = (
                    f"{name} just launched '{product}' at ₹{price:,}.\n{tip}"
                )
                wa_sent = False
                if send_whatsapp:
                    wa_sent = notifier.send_competitor_alert(
                        competitor_name    = name,
                        update_type        = "new_launch",
                        product_name       = product,
                        product_price      = price,
                        strategy_tip       = tip,
                        instagram_caption  = caption,
                    )
                    if wa_sent:
                        sent_count += 1
                db.log_alert(
                    user_id         = user_id,
                    alert_type      = "new_launch",
                    title           = title,
                    message         = message,
                    competitor_name = name,
                    whatsapp_sent   = wa_sent,
                )

            # 2. Heavy-discount alerts — fire when ≥2 items discounted
            discounted = comp.get("discounted_items", [])
            if len(discounted) >= 2:
                top_item  = discounted[0]
                p_name    = top_item.get("name", "multiple products")
                p_price   = top_item.get("discounted_price") or top_item.get("price", 0)
                tip       = (
                    f"{name} is running discounts on {len(discounted)} products. "
                    f"Launch a flash sale on your best-sellers to retain price-sensitive shoppers."
                )
                caption   = (
                    f"⚡ Flash Sale is LIVE! Don't miss out on our exclusive deals. "
                    f"Limited stock only! 🏷️ #Sale #Fashion#{city.replace(' ', '')}"
                )
                title     = f"💸 {name} Running Heavy Discounts"
                message   = tip
                wa_sent   = False
                if send_whatsapp:
                    wa_sent = notifier.send_competitor_alert(
                        competitor_name    = name,
                        update_type        = "price_drop",
                        product_name       = p_name,
                        product_price      = p_price,
                        strategy_tip       = tip,
                        instagram_caption  = caption,
                    )
                    if wa_sent:
                        sent_count += 1
                db.log_alert(
                    user_id         = user_id,
                    alert_type      = "price_drop",
                    title           = title,
                    message         = message,
                    competitor_name = name,
                    whatsapp_sent   = wa_sent,
                )

            # 3. Active-campaign alerts
            campaigns = comp.get("active_campaigns", [])
            if campaigns:
                campaign_name = campaigns[0] if isinstance(campaigns[0], str) else str(campaigns[0])
                tip     = (
                    f"{name} is running '{campaign_name}'. "
                    f"Boost your visibility with a counter-campaign highlighting your unique strengths."
                )
                caption = (
                    f"🎉 Something big is coming your way! Stay tuned for our exclusive campaign. "
                    f"Follow us for updates 👗 #Fashion #{city.replace(' ', '')}"
                )
                title   = f"📢 {name} Launched a New Campaign"
                message = tip
                wa_sent = False
                if send_whatsapp:
                    wa_sent = notifier.send_competitor_alert(
                        competitor_name   = name,
                        update_type       = "campaign",
                        product_name      = campaign_name,
                        strategy_tip      = tip,
                        instagram_caption = caption,
                    )
                    if wa_sent:
                        sent_count += 1
                db.log_alert(
                    user_id         = user_id,
                    alert_type      = "campaign",
                    title           = title,
                    message         = message,
                    competitor_name = name,
                    whatsapp_sent   = wa_sent,
                )

        # ── Final strategy-summary WhatsApp ───────────────────────────────────
        db.log_alert(
            user_id    = user_id,
            alert_type = "strategy",
            title      = "🤖 AI Strategy Ready",
            message    = "Your daily market intelligence & strategy report has been generated.",
        )
        if send_whatsapp and not sent_count:
            # Fallback: if no individual alerts fired, send the generic strategy message
            ok = notifier.send(wa_message)
            if ok:
                sent_count += 1

        logger.info("WhatsApp alerts sent: %d", sent_count)
        return sent_count
