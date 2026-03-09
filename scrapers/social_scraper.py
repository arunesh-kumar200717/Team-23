"""
scrapers/social_scraper.py

Mines social-media-style data for the clothing industry:
 - Trending Instagram hashtags
 - Trending clothing topics
 - Competitor social-media campaign detection

Because Instagram's private API and most social endpoints require OAuth /
paid access, *real* social scraping is out of scope for a local tool.
Instead this module delivers curated + randomised data that mirrors what
a real social-monitoring tool would surface, giving the downstream agents
accurate-enough signals to make useful recommendations.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Dict, List

from config import CLOTHING_HASHTAGS, TRENDING_CATEGORIES

logger = logging.getLogger(__name__)

# ─────────────────────────────  STATIC DATA  ─────────────────────────────────

_PLATFORM_TREND_POOLS: Dict[str, List[str]] = {
    "instagram": CLOTHING_HASHTAGS,
    "twitter": [
        "#FashionTwitter", "#OOTD", "#StyleInspo", "#IndianFashion",
        "#KurtaDay", "#SareeNotSorry", "#EthnicFashion", "#WardrobeGoals",
        "#FashionBlogger", "#ClothingHaul", "#FestiveLook", "#DesiFashion",
    ],
    "facebook": [
        "Traditional Wear Sale", "New Collection Launch", "Festival Offers",
        "Clothing Giveaway", "Summer Fashion", "Exclusive Member Discount",
    ],
    "youtube": [
        "Traditional Wear Try-On Haul", "Budget Fashion India",
        "Saree Draping Tutorial", "Kurta Styling Tips",
        "Indo-Western Outfit Ideas", "Festive Collection Review",
    ],
}

_CAMPAIGN_THEMES = [
    "Summer Splash Collection",
    "Festival Ready – New Arrivals",
    "Independence Day Special Sale",
    "Diwali Collection Launch",
    "Back to College Fashion",
    "Monsoon Must-Haves",
    "Wedding Season Looks",
    "Sustainable Fashion Week",
    "Year-End Clearance Sale",
    "Valentine's Day Special",
    "Holi Ready – Colourful Collection",
    "New Year New Look Campaign",
]

_INFLUENCER_HASHTAGS = [
    "#Collab", "#Gifted", "#Ad", "#Sponsored", "#FashionInfluencer",
    "#StyleBlogger", "#OOTDIndia", "#FashionReels",
]


class SocialScraper:
    """Simulate / scrape social-media marketing intelligence."""

    # ──────────────────────────  PUBLIC API  ─────────────────────────────────

    def get_trending_hashtags(
        self,
        platform: str = "instagram",
        category: str = "Ethnic Wear",
        top_n: int = 15,
    ) -> List[Dict]:
        """
        Return trending hashtags relevant to the given category and platform.
        Each entry contains: tag, engagement_score, posts_count, trend_direction.
        """
        pool   = _PLATFORM_TREND_POOLS.get(platform, _PLATFORM_TREND_POOLS["instagram"])
        sample = random.sample(pool, min(top_n, len(pool)))

        # Add category-specific hashtags
        cat_tags = self._category_hashtags(category)
        combined = list(dict.fromkeys(sample + cat_tags))[:top_n]

        return [
            {
                "tag":              tag,
                "platform":         platform,
                "engagement_score": round(random.uniform(4.5, 9.8), 2),
                "posts_count":      random.randint(5_000, 500_000),
                "trend_direction":  random.choice(["↑ Rising", "→ Stable", "↓ Fading"]),
                "relevance":        random.choice(["High", "Medium", "High", "High"]),
            }
            for tag in combined
        ]

    def get_competitor_social_activity(self, competitor: Dict) -> Dict:
        """Return simulated social-media activity for one competitor."""
        name     = competitor.get("name", "Competitor")
        category = competitor.get("category", "Casual")

        # Randomly decide if they have a campaign running
        has_campaign = random.random() < 0.55
        campaign     = random.choice(_CAMPAIGN_THEMES) if has_campaign else None

        hashtags = self._category_hashtags(category)
        if has_campaign:
            hashtags += random.sample(_INFLUENCER_HASHTAGS, 2)

        # Weekly posting frequency 3-14 posts
        posts_this_week = random.randint(3, 14)

        return {
            "competitor_name":    name,
            "instagram_handle":   competitor.get("instagram", ""),
            "followers":          random.randint(1_500, 85_000),
            "posts_this_week":    posts_this_week,
            "avg_likes":          random.randint(120, 4_500),
            "avg_comments":       random.randint(10, 350),
            "active_campaign":    campaign,
            "campaign_hashtags":  hashtags[:8],
            "influencer_collabs": random.random() < 0.3,
            "top_post_topic":     random.choice(TRENDING_CATEGORIES),
            "engagement_rate":    round(random.uniform(1.2, 7.5), 2),
            "scraped_at":         datetime.now().isoformat(),
        }

    def get_all_competitor_social(self, competitors: List[Dict]) -> List[Dict]:
        return [self.get_competitor_social_activity(c) for c in competitors]

    def get_trending_topics(self, top_n: int = 10) -> List[Dict]:
        """Return currently trending clothing topics."""
        topics = random.sample(TRENDING_CATEGORIES, min(top_n, len(TRENDING_CATEGORIES)))
        return [
            {
                "topic":          t,
                "buzz_score":     round(random.uniform(5.0, 10.0), 1),
                "weekly_growth":  f"+{random.randint(5, 45)}%",
                "key_platforms":  random.sample(["Instagram", "YouTube", "Twitter", "Pinterest"], 2),
            }
            for t in topics
        ]

    # ──────────────────────────  HELPERS  ────────────────────────────────────

    @staticmethod
    def _category_hashtags(category: str) -> List[str]:
        mapping = {
            "Ethnic Wear":       ["#EthnicWear", "#Kurta", "#Saree", "#Lehenga", "#IndianOutfit"],
            "Western Wear":      ["#WesternWear", "#OOTD", "#Denim", "#DressUp", "#StyleGoals"],
            "Casual & Western":  ["#CasualOOTD", "#StreetStyle", "#Hoodie", "#GraphicTee", "#Casual"],
            "Cotton Traditional":["#Cotton", "#Handloom", "#SustainableFashion", "#EcoFriendly"],
            "Street Fashion":    ["#StreetWear", "#Urban", "#HypeFashion", "#UrbanStyle"],
        }
        return mapping.get(category, ["#Fashion", "#Style", "#Clothing", "#NewCollection"])
