"""Quick integration test – run with: python test_core.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("--- Database ---")
from database.db import initialize_database
initialize_database()
print("DB initialized OK")

print("\n--- Config ---")
from config import APP_NAME, SAMPLE_COMPETITORS
print("Config loaded OK:", APP_NAME, "| competitors:", len(SAMPLE_COMPETITORS))

print("\n--- Competitor Scraper ---")
from scrapers.competitor_scraper import CompetitorScraper
cs = CompetitorScraper()
data = cs.scrape_competitor(SAMPLE_COMPETITORS[0])
print("Scraped:", data["competitor_name"], "| products:", len(data["products"]))
print("New launches:", len(data["new_launches"]))
print("Discounts:", len(data["discounted_items"]))

print("\n--- Review Scraper ---")
from scrapers.review_scraper import ReviewScraper
rs = ReviewScraper()
revs = rs.scrape_competitor_reviews(SAMPLE_COMPETITORS[0], count=3)
print("Reviews:", len(revs), "| sample label:", revs[0]["sentiment_label"])

print("\n--- Social Scraper ---")
from scrapers.social_scraper import SocialScraper
ss = SocialScraper()
tags = ss.get_trending_hashtags(top_n=5)
print("Hashtags:", len(tags))
topics = ss.get_trending_topics(top_n=3)
print("Topics:", [t["topic"] for t in topics])

print("\n--- DB User Creation ---")
from database import db
ok, msg = db.create_user(
    username="test_user", password="testpass123",
    business_name="Test Textiles", city="Coimbatore",
    shop_type="Retail Store", clothing_category="Ethnic Wear",
    avg_price_range="Mid Range"
)
print("Create user:", msg)

user = db.verify_user("test_user", "testpass123")
print("Verify user:", "OK" if user else "FAIL")

print("\n--- Brochure Reader ---")
from brochure_analysis.brochure_reader import BrochureReader
br = BrochureReader()
dummy_text = b"Summer Sale! 30% off on Kurtas and Sarees. New Collection available."
res = br.analyse(dummy_text, "test.txt", {"business_name": "Test", "city": "Coimbatore"})
print("Brochure analysis:", "OK" if res["analysis_result"] else "FAIL")
print("Products detected:", len(res["products_detected"]))

print("\n=== ALL TESTS PASSED ===")
