"""
agents/scout_agent.py – Agent A: SCOUT AGENT

Responsibilities
----------------
• Orchestrate the three scrapers (competitor, social, review)
• Compile all raw data into a single, structured ScoutReport dict
• Persist competitor updates and reviews to the database
• Pass the ScoutReport downstream to the Analyst Agent
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from database import db
from scrapers.competitor_scraper import CompetitorScraper
from scrapers.review_scraper import ReviewScraper
from scrapers.social_scraper import SocialScraper

logger = logging.getLogger(__name__)


class ScoutAgent:
    """
    Agent A – Gathers all raw market intelligence from competitors.

    Usage::

        agent = ScoutAgent(user_id=1, competitors=[...])
        report = agent.run()
    """

    def __init__(
        self,
        user_id: int,
        competitors: Optional[List[Dict]] = None,
    ) -> None:
        self.user_id     = user_id
        self.competitors = competitors or []
        self._comp_scraper   = CompetitorScraper()
        self._social_scraper = SocialScraper()
        self._review_scraper = ReviewScraper()

    # ──────────────────────────  MAIN ENTRY  ─────────────────────────────────

    def run(self) -> Dict:
        """
        Execute the full scouting pipeline and return a ScoutReport dict.

        ScoutReport structure
        ---------------------
        {
            "user_id": int,
            "generated_at": str (ISO 8601),
            "competitors": [
                {
                    "competitor_id": int | None,
                    "competitor_name": str,
                    "products": [...],
                    "new_launches": [...],
                    "discounted_items": [...],
                    "active_campaigns": [...],
                    "social": {...},
                    "reviews": [...],
                }
            ],
            "trending_hashtags": [...],
            "trending_topics": [...],
            "summary": {
                "total_competitors": int,
                "total_new_launches": int,
                "total_discounts": int,
                "total_campaigns": int,
            }
        }
        """
        logger.info("Scout Agent starting for user_id=%s", self.user_id)

        # 1. Ensure competitors exist in the DB
        self._sync_competitors_to_db()

        # 2. Scrape product / price data
        product_data = self._comp_scraper.scrape_all(self.competitors)

        # 3. Scrape social-media activity
        social_data_map: Dict[str, Dict] = {}
        for sd in self._social_scraper.get_all_competitor_social(self.competitors):
            social_data_map[sd["competitor_name"]] = sd

        # 4. Scrape reviews (10 per competitor)
        all_reviews = self._review_scraper.scrape_all_competitor_reviews(
            self.competitors, reviews_each=10
        )

        # 5. Persist updates + reviews to DB
        self._persist_updates(product_data)
        self._persist_reviews(all_reviews)

        # 6. Build combined report
        competitor_reports: List[Dict] = []
        for pdata in product_data:
            cname   = pdata["competitor_name"]
            reviews = [r for r in all_reviews if r["competitor_name"] == cname]
            competitor_reports.append(
                {
                    **pdata,
                    "social":  social_data_map.get(cname, {}),
                    "reviews": reviews,
                }
            )

        # 7. Trending data (platform-wide)
        trending_hashtags = self._social_scraper.get_trending_hashtags(top_n=15)
        trending_topics   = self._social_scraper.get_trending_topics(top_n=8)

        report: Dict = {
            "user_id":           self.user_id,
            "generated_at":      datetime.now().isoformat(),
            "competitors":       competitor_reports,
            "trending_hashtags": trending_hashtags,
            "trending_topics":   trending_topics,
            "summary": {
                "total_competitors":  len(competitor_reports),
                "total_new_launches": sum(len(c["new_launches"]) for c in competitor_reports),
                "total_discounts":    sum(len(c["discounted_items"]) for c in competitor_reports),
                "total_campaigns":    sum(len(c["active_campaigns"]) for c in competitor_reports),
            },
        }

        logger.info(
            "Scout complete – %d competitors, %d new launches, %d discounts, %d campaigns",
            report["summary"]["total_competitors"],
            report["summary"]["total_new_launches"],
            report["summary"]["total_discounts"],
            report["summary"]["total_campaigns"],
        )
        return report

    # ──────────────────────────  PRIVATE HELPERS  ────────────────────────────

    def _sync_competitors_to_db(self) -> None:
        """Add any competitor that is not yet in the DB for this user."""
        for comp in self.competitors:
            if not db.competitor_exists(self.user_id, comp["name"]):
                comp_id = db.add_competitor(
                    user_id   = self.user_id,
                    name      = comp["name"],
                    website   = comp.get("website", ""),
                    location  = comp.get("location", ""),
                    category  = comp.get("category", ""),
                    instagram = comp.get("instagram", ""),
                )
                comp["id"] = comp_id
                logger.debug("Added competitor to DB: %s (id=%s)", comp["name"], comp_id)

    def _persist_updates(self, product_data: List[Dict]) -> None:
        """Save new launches, discounts, and campaigns to competitor_updates."""
        for pdata in product_data:
            comp_id   = self._get_db_competitor_id(pdata["competitor_name"])
            comp_name = pdata["competitor_name"]

            for item in pdata.get("new_launches", []):
                db.add_competitor_update(
                    competitor_id   = comp_id,
                    competitor_name = comp_name,
                    update_type     = "new_launch",
                    title           = f"New Launch: {item['name']}",
                    description     = f"Price ₹{item['price']}",
                    price           = item["price"],
                )

            for item in pdata.get("discounted_items", []):
                db.add_competitor_update(
                    competitor_id   = comp_id,
                    competitor_name = comp_name,
                    update_type     = "price_drop",
                    title           = f"Price Drop: {item['name']}",
                    description     = (
                        f"{item['discount_pct']}% off – "
                        f"₹{item['original_price']} → ₹{item['price']}"
                    ),
                    price           = item["price"],
                    original_price  = item["original_price"],
                    discount_pct    = item["discount_pct"],
                )

            for campaign in pdata.get("active_campaigns", []):
                db.add_competitor_update(
                    competitor_id   = comp_id,
                    competitor_name = comp_name,
                    update_type     = "campaign",
                    title           = f"Campaign: {campaign}",
                    description     = f"{comp_name} is running: {campaign}",
                )

    def _persist_reviews(self, reviews: List[Dict]) -> None:
        for rev in reviews:
            comp_id = self._get_db_competitor_id(rev["competitor_name"])
            db.add_review(
                competitor_id   = comp_id,
                user_id         = None,
                review_text     = rev["review_text"],
                rating          = rev["rating"],
                sentiment_label = rev["sentiment_label"],
                sentiment_score = rev["sentiment_score"],
                review_source   = rev.get("review_source", "google"),
                reviewer_name   = rev.get("reviewer_name", "Anonymous"),
            )

    def _get_db_competitor_id(self, name: str) -> int:
        """Resolve competitor name → DB id for this user."""
        comps = db.get_competitors(self.user_id)
        for c in comps:
            if c["name"] == name:
                return c["id"]
        # Fallback: insert if missing
        return db.add_competitor(self.user_id, name)
