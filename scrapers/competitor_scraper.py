"""
scrapers/competitor_scraper.py

Scrapes competitor clothing websites for:
 - New product launches
 - Price drops / discounts
 - Active marketing campaigns

When live scraping fails (private site, bot protection, etc.) the module
falls back to realistic, randomised mock data so the rest of the pipeline
always has something to work with.
"""
from __future__ import annotations

import logging
import random
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from config import SCRAPE_TIMEOUT

logger = logging.getLogger(__name__)

# ─────────────────────────────  MOCK CATALOGUE  ──────────────────────────────

_MOCK_CATALOGUE: Dict[str, List[Dict]] = {
    "Ethnic Wear": [
        {"name": "Banarasi Silk Saree",       "base_price": 2999, "cat": "saree"},
        {"name": "Cotton Embroidered Kurta",   "base_price": 899,  "cat": "kurta"},
        {"name": "Lehenga Choli Set",          "base_price": 4500, "cat": "lehenga"},
        {"name": "Anarkali Suit",              "base_price": 1899, "cat": "suit"},
        {"name": "Kanjivaram Silk Saree",      "base_price": 6999, "cat": "saree"},
        {"name": "Kurti with Palazzo",         "base_price": 1199, "cat": "kurti"},
        {"name": "Designer Kurta Set",         "base_price": 2499, "cat": "kurta_set"},
        {"name": "Sharara Suit",               "base_price": 3299, "cat": "sharara"},
        {"name": "Chikankari Kurti",           "base_price": 1599, "cat": "kurti"},
        {"name": "Phulkari Dupatta Set",       "base_price": 1299, "cat": "dupatta_set"},
    ],
    "Western Wear": [
        {"name": "Classic Denim Jacket",       "base_price": 1299, "cat": "jacket"},
        {"name": "Floral Summer Dress",        "base_price": 999,  "cat": "dress"},
        {"name": "High-Waist Jeans",           "base_price": 1499, "cat": "jeans"},
        {"name": "Crop Top + Skirt Set",       "base_price": 799,  "cat": "set"},
        {"name": "Linen Co-ord Set",           "base_price": 1799, "cat": "coord_set"},
        {"name": "Maxi Dress",                 "base_price": 1199, "cat": "dress"},
        {"name": "Blazer Set",                 "base_price": 2299, "cat": "blazer"},
        {"name": "Jogger Pants",               "base_price": 699,  "cat": "pants"},
        {"name": "Peplum Top",                 "base_price": 699,  "cat": "top"},
        {"name": "Asymmetric Hem Dress",       "base_price": 1399, "cat": "dress"},
    ],
    "Casual & Western": [
        {"name": "Oversized Graphic Tee",      "base_price": 499,  "cat": "t_shirt"},
        {"name": "Hoodie – Winter Edition",    "base_price": 1299, "cat": "hoodie"},
        {"name": "Track Pants Combo",          "base_price": 799,  "cat": "trackpants"},
        {"name": "Polo T-Shirt",               "base_price": 599,  "cat": "polo"},
        {"name": "Cargo Shorts",               "base_price": 699,  "cat": "shorts"},
        {"name": "Linen Casual Shirt",         "base_price": 899,  "cat": "shirt"},
        {"name": "Slim Fit Chinos",            "base_price": 1099, "cat": "chinos"},
        {"name": "Sports Shorts",              "base_price": 449,  "cat": "shorts"},
    ],
    "Cotton Traditional": [
        {"name": "Handloom Cotton Saree",      "base_price": 1599, "cat": "saree"},
        {"name": "Block Print Kurta",          "base_price": 799,  "cat": "kurta"},
        {"name": "Cotton Salwar Kameez",       "base_price": 1199, "cat": "salwar"},
        {"name": "Natural Dye Dupatta",        "base_price": 399,  "cat": "dupatta"},
        {"name": "Khadi Cotton Shirt",         "base_price": 699,  "cat": "shirt"},
        {"name": "Cotton Palazzo Set",         "base_price": 999,  "cat": "palazzo"},
        {"name": "Ikat Print Saree",           "base_price": 1799, "cat": "saree"},
    ],
    "Street Fashion": [
        {"name": "Streetwear Cargo Joggers",   "base_price": 1599, "cat": "joggers"},
        {"name": "Tie-Dye Hoodie",             "base_price": 1799, "cat": "hoodie"},
        {"name": "Graffiti Print Tee",         "base_price": 699,  "cat": "t_shirt"},
        {"name": "Baggy Urban Jeans",          "base_price": 1899, "cat": "jeans"},
        {"name": "Bomber Jacket",              "base_price": 2499, "cat": "jacket"},
        {"name": "Chain Belt Shorts",          "base_price": 849,  "cat": "shorts"},
        {"name": "Reflective Windbreaker",     "base_price": 2199, "cat": "jacket"},
    ],
}

_DEFAULT_CAMPAIGNS = [
    "Summer Sale – Up to 40% Off",
    "New Arrivals – Fresh Collection",
    "Festival Special Offers",
    "End of Season Sale",
    "Buy 2 Get 1 Free",
    "Loyalty Customer Discount – Extra 10%",
    "Weekend Flash Sale",
    "Grand Opening Offer",
    "Combo Deal – Save More",
]


class CompetitorScraper:
    """Scrape competitor clothing stores for market-intelligence data."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    # ──────────────────────────  PUBLIC API  ─────────────────────────────────

    def scrape_competitor(self, competitor: Dict) -> Dict:
        """
        Try live scraping; fall back to mock data on any failure.
        Always returns a fully-populated dict.
        """
        name = competitor.get("name", "Unknown")
        logger.info("Scraping competitor: %s", name)

        live = self._try_live_scrape(competitor.get("website", ""), name)
        if live:
            return live

        return self._mock_data(competitor)

    def scrape_all(self, competitors: List[Dict]) -> List[Dict]:
        results = []
        for comp in competitors:
            results.append(self.scrape_competitor(comp))
        return results

    # ──────────────────────────  LIVE SCRAPING  ──────────────────────────────

    def _try_live_scrape(self, url: str, name: str) -> Optional[Dict]:
        if not url or "example.com" in url:
            return None
        try:
            resp = self.session.get(url, timeout=SCRAPE_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            products = self._extract_products(soup)
            if not products:
                return None
            discounted = [p for p in products if p.get("discount_pct", 0) > 0]
            new_items  = [p for p in products if p.get("is_new")]
            return {
                "competitor_name": name,
                "website": url,
                "products": products,
                "new_launches": new_items,
                "discounted_items": discounted,
                "active_campaigns": [],
                "scraped_at": datetime.now().isoformat(),
                "source": "live",
            }
        except Exception as exc:
            logger.debug("Live scrape failed for %s: %s", name, exc)
            return None

    def _extract_products(self, soup: BeautifulSoup) -> List[Dict]:
        products: List[Dict] = []
        selectors = [
            ".product-card", ".product-item", ".product-tile",
            "[class*='product']", "[class*='item-card']",
        ]
        for sel in selectors:
            items = soup.select(sel)
            if not items:
                continue
            for item in items[:12]:
                name_el  = item.select_one("h2,h3,.product-name,.title,[class*='name']")
                price_el = item.select_one(".price,.product-price,[class*='price']")
                if name_el and price_el:
                    products.append(
                        {
                            "name":         name_el.get_text(strip=True),
                            "price":        self._parse_price(price_el.get_text()),
                            "original_price": self._parse_price(price_el.get_text()),
                            "discount_pct": 0,
                            "is_new":       False,
                            "in_stock":     True,
                            "rating":       0,
                            "reviews_count": 0,
                            "cat":          "general",
                        }
                    )
            if products:
                break
        return products

    @staticmethod
    def _parse_price(text: str) -> float:
        nums = re.findall(r"[\d]+", text.replace(",", ""))
        return float(nums[0]) if nums else 0.0

    # ──────────────────────────  MOCK DATA  ──────────────────────────────────

    def _mock_data(self, competitor: Dict) -> Dict:
        category = competitor.get("category", "Casual & Western")
        pool     = _MOCK_CATALOGUE.get(category, _MOCK_CATALOGUE["Casual & Western"])
        sample   = random.sample(pool, min(random.randint(5, 8), len(pool)))

        products: List[Dict] = []
        for item in sample:
            # ±15 % price jitter, rounded to nearest ₹10
            price = round(item["base_price"] * random.uniform(0.85, 1.15) / 10) * 10
            has_discount = random.random() < 0.35
            disc_pct     = random.choice([10, 15, 20, 25, 30]) if has_discount else 0
            orig         = price
            if has_discount:
                price = round(orig * (1 - disc_pct / 100) / 10) * 10

            products.append(
                {
                    "name":           item["name"],
                    "price":          price,
                    "original_price": orig,
                    "discount_pct":   disc_pct,
                    "cat":            item["cat"],
                    "is_new":         random.random() < 0.22,
                    "in_stock":       random.random() < 0.88,
                    "rating":         round(random.uniform(3.4, 5.0), 1),
                    "reviews_count":  random.randint(4, 200),
                }
            )

        # 40 % chance competitor has active campaigns
        active_campaigns: List[str] = (
            random.sample(_DEFAULT_CAMPAIGNS, random.randint(1, 3))
            if random.random() < 0.4
            else []
        )

        return {
            "competitor_id":    competitor.get("id"),
            "competitor_name":  competitor["name"],
            "website":          competitor.get("website", ""),
            "location":         competitor.get("location", ""),
            "category":         category,
            "products":         products,
            "new_launches":     [p for p in products if p["is_new"]],
            "discounted_items": [p for p in products if p["discount_pct"] > 0],
            "active_campaigns": active_campaigns,
            "scraped_at":       datetime.now().isoformat(),
            "source":           "simulated",
        }
