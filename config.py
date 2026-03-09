"""
config.py – Central configuration for Market Intelligence Bot.
All environment-variable loading happens here; all modules import from this file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = str(DATA_DIR / "market_intelligence.db")

# ── LLM (Ollama local) ───────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL:    str = os.getenv("OLLAMA_MODEL", "llama3")

# ── Twilio WhatsApp ──────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID:    str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN:     str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM:  str = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_WHATSAPP_TO:    str = os.getenv("TWILIO_WHATSAPP_TO", "")

# ── Scraping ─────────────────────────────────────────────────────────────────
SCRAPE_TIMEOUT:  int = 10
MAX_RETRIES:     int = 3

# ── App Meta ─────────────────────────────────────────────────────────────────
APP_NAME    = "Market Intelligence Bot"
APP_VERSION = "1.0.0"

# ── Sample Competitors (Indian Clothing Market – Coimbatore) ─────────────────
SAMPLE_COMPETITORS = [
    {
        "id": 1,
        "name": "FashionHub Coimbatore",
        "website": "https://www.myntra.com",          # publicly accessible for demo
        "location": "RS Puram, Coimbatore",
        "category": "Ethnic Wear",
        "instagram": "@fashionhub_cbe",
    },
    {
        "id": 2,
        "name": "TrendSetters",
        "website": "https://www.ajio.com",
        "location": "Gandhipuram, Coimbatore",
        "category": "Western Wear",
        "instagram": "@trendsetters_cbe",
    },
    {
        "id": 3,
        "name": "StyleZone",
        "website": "https://www.flipkart.com/clothing",
        "location": "Peelamedu, Coimbatore",
        "category": "Casual & Western",
        "instagram": "@stylezone_official",
    },
    {
        "id": 4,
        "name": "The Cotton House",
        "website": "https://www.craftsvilla.com",
        "location": "Saibaba Colony, Coimbatore",
        "category": "Cotton Traditional",
        "instagram": "@cottonhouse_cbe",
    },
    {
        "id": 5,
        "name": "Urban Threads",
        "website": "https://www.bewakoof.com",
        "location": "Brookefields, Coimbatore",
        "category": "Street Fashion",
        "instagram": "@urbanthreads_india",
    },
]

# ── Trending Fashion Categories (India 2026) ─────────────────────────────────
TRENDING_CATEGORIES = [
    "Summer Ethnic Fusion",
    "Sustainable Cotton Wear",
    "Indo-Western Kurtas",
    "Oversized Casual T-Shirts",
    "Festive Lehengas",
    "Lightweight Denim",
    "Formal Linen Shirts",
    "Athleisure Wear",
    "Traditional Silk Sarees",
    "Designer Hoodies",
    "Handloom Revival",
    "Minimalist Streetwear",
]

# ── Top Clothing Hashtags (India) ─────────────────────────────────────────────
CLOTHING_HASHTAGS = [
    "#IndianFashion", "#EthnicWear", "#TraditionalWear",
    "#CoimbatoreStyle", "#FashionIndia", "#KurtaLover",
    "#SareeTwitter", "#IndoWestern", "#SustainableFashion",
    "#Tamilnadu_fashion", "#FestiveFashion", "#NewCollection",
    "#WomenFashion", "#MensFashion", "#NaturalFabric",
    "#HandloomIndia", "#DesiSwag", "#FashionBlogger",
    "#CottonSaree", "#DesignerKurta", "#Lehenga",
    "#BridalWear", "#CasualOOTD", "#StreetStyle",
]
