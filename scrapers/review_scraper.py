"""
scrapers/review_scraper.py

Collects and analyses customer reviews for competitor clothing stores.

Google Business / Maps reviews require OAuth with the Maps API; for a
fully-local tool we simulate realistic review data and score sentiment
via TextBlob so the rest of the pipeline has actionable signals.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import Dict, List, Tuple

from textblob import TextBlob

logger = logging.getLogger(__name__)

# ─────────────────────────────  REVIEW TEXT POOLS  ───────────────────────────

_POSITIVE_REVIEWS = [
    "Absolutely love the kurta collection here! Quality is excellent.",
    "Best ethnic wear in Coimbatore. Very affordable prices and great designs.",
    "Staff is very helpful and the fabric quality is top-notch.",
    "Wonderful variety of sarees — both cotton and silk. Highly recommend!",
    "Bought a lehenga for my daughter's wedding here. Everyone complimented it.",
    "Great discounts during festival season. Got a kurta set at 30% off.",
    "Fresh designs every month. Love how they keep up with trends.",
    "The cotton kurtis are so comfortable and reasonably priced.",
    "Online order arrived within 2 days. Packaging was perfect.",
    "The variety of Indo-Western outfits is unmatched in this area.",
    "Staff helped me pick the right outfit for my occasion. Excellent service!",
    "5-star experience. Will definitely come back and recommend to friends.",
    "Amazing collection of handloom sarees at unbelievable prices.",
    "Quick delivery and very accurate colour representation online.",
    "My go-to shop for all festivals. Quality never disappoints.",
]

_NEUTRAL_REVIEWS = [
    "Decent collection. Nothing extraordinary but good value for money.",
    "Average store. Some items are good, others not so much.",
    "New arrivals seem okay but nothing that made me wow.",
    "Selection is average compared to larger boutiques in the city.",
    "Prices are fair. Quality is acceptable for the price range.",
    "Visited during sale — some good picks but crowded.",
    "Online vs in-store experience differs a bit.",
    "Good for casual wear but limited options for ethnic outfits.",
    "Standard quality. Expected slightly better stitching.",
    "Okay for basic everyday wear. Nothing premium though.",
]

_NEGATIVE_REVIEWS = [
    "Disappointed with the quality. Stitching came apart after one wash.",
    "Prices seem higher than other shops nearby. Not worth it.",
    "Waited 20 minutes for someone to help me. Poor customer service.",
    "Ordered online but received a different colour. Returns process is tedious.",
    "The shop is too crowded and disorganised. Hard to find things.",
    "Fabric felt synthetic even though it was labelled as cotton.",
    "Size chart is inaccurate. Had to return the item.",
    "Sale prices are misleading — discounts are on already inflated MRPs.",
    "No exchange policy. Very rigid. Won't visit again.",
    "Photos on Instagram look better than the actual product.",
]


class ReviewScraper:
    """Collect and sentiment-score customer reviews for clothing stores."""

    def scrape_competitor_reviews(
        self, competitor: Dict, count: int = 10
    ) -> List[Dict]:
        """
        Return `count` reviews for a competitor with sentiment analysis.
        In production, replace with a real Google Business API call.
        """
        reviews: List[Dict] = []
        for _ in range(count):
            text, rating = self._random_review()
            sentiment_label, sentiment_score = self._analyse_sentiment(text)
            # Spread review dates over the last 90 days
            days_ago  = random.randint(0, 90)
            rev_date  = (date.today() - timedelta(days=days_ago)).isoformat()
            reviews.append(
                {
                    "competitor_name":  competitor.get("name", "Competitor"),
                    "competitor_id":    competitor.get("id"),
                    "reviewer_name":    self._random_name(),
                    "review_text":      text,
                    "rating":           rating,
                    "sentiment_label":  sentiment_label,
                    "sentiment_score":  sentiment_score,
                    "review_date":      rev_date,
                    "review_source":    "google",
                }
            )
        return reviews

    def scrape_all_competitor_reviews(
        self, competitors: List[Dict], reviews_each: int = 8
    ) -> List[Dict]:
        all_reviews: List[Dict] = []
        for comp in competitors:
            all_reviews.extend(self.scrape_competitor_reviews(comp, reviews_each))
        return all_reviews

    def get_sentiment_distribution(self, reviews: List[Dict]) -> Dict[str, int]:
        dist: Dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
        for r in reviews:
            label = r.get("sentiment_label", "neutral")
            dist[label] = dist.get(label, 0) + 1
        return dist

    def get_average_rating(self, reviews: List[Dict]) -> float:
        if not reviews:
            return 0.0
        return round(sum(r["rating"] for r in reviews) / len(reviews), 2)

    # ──────────────────────────  HELPERS  ────────────────────────────────────

    @staticmethod
    def _analyse_sentiment(text: str) -> Tuple[str, float]:
        score = TextBlob(text).sentiment.polarity  # -1.0 to +1.0
        if score > 0.1:
            return "positive", round(score, 4)
        if score < -0.1:
            return "negative", round(score, 4)
        return "neutral", round(score, 4)

    @staticmethod
    def _random_review() -> Tuple[str, float]:
        roll = random.random()
        if roll < 0.60:          # 60 % positive
            text   = random.choice(_POSITIVE_REVIEWS)
            rating = random.choice([4.0, 4.5, 5.0])
        elif roll < 0.85:        # 25 % neutral
            text   = random.choice(_NEUTRAL_REVIEWS)
            rating = random.choice([3.0, 3.5])
        else:                    # 15 % negative
            text   = random.choice(_NEGATIVE_REVIEWS)
            rating = random.choice([1.0, 1.5, 2.0, 2.5])
        return text, rating

    @staticmethod
    def _random_name() -> str:
        first = ["Priya", "Ravi", "Sunita", "Arun", "Divya", "Karthik",
                 "Meena", "Suresh", "Nalini", "Vijay", "Geetha", "Anand",
                 "Lakshmi", "Murugan", "Saranya", "Deepak", "Kavitha"]
        last  = ["Kumar", "Sharma", "Raj", "Pillai", "Venkat", "Naidu",
                 "Rao", "Gopal", "Krishnan", "Rajan", "Mani", "Subramanian"]
        return f"{random.choice(first)} {random.choice(last)}"
