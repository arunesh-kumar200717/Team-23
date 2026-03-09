# README – Multi-Agent Market Intelligence Bot (Clothing Industry)

## Overview

An end-to-end **Multi-Agent AI system** that monitors competitors, analyses their strategies, and generates marketing recommendations — purpose-built for small clothing shop owners in Tier-2 Indian cities like Coimbatore.

```
Scout Agent (A)  →  Analyst Agent (B)  →  Strategist Agent (C)
      ↓                    ↓                        ↓
Web + Social          LangChain +             Strategy Report +
  Scraping            Ollama llama3           WhatsApp Alerts
```

---

## Project Structure

```
market_intelligence_bot/
├── agents/
│   ├── scout_agent.py          # Agent A – scrapes all competitor data
│   ├── analyst_agent.py        # Agent B – LangChain + Ollama analysis
│   └── strategist_agent.py     # Agent C – marketing strategy generation
├── scrapers/
│   ├── competitor_scraper.py   # Product / price / discount scraping
│   ├── social_scraper.py       # Instagram hashtags + social activity
│   └── review_scraper.py       # Customer reviews + sentiment scoring
├── brochure_analysis/
│   └── brochure_reader.py      # PDF / image OCR + AI analysis
├── dashboard/
│   ├── login.py                # Streamlit login + signup
│   ├── dashboard.py            # War Room dashboard (all sections)
│   └── growth_graphs.py        # Plotly charts (5 graph types)
├── database/
│   └── db.py                   # SQLite CRUD layer
├── notifications/
│   └── whatsapp_alert.py       # Twilio WhatsApp alerts
├── data/                       # Auto-created; holds SQLite database
├── config.py                   # All settings + env-variable loading
├── orchestrator.py             # Agent pipeline controller
├── main.py                     # Streamlit entry point
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1 – Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Ollama | Latest |
| Tesseract OCR | Latest (for brochure images) |

### 2 – Install Python dependencies

```bash
cd market_intelligence_bot
pip install -r requirements.txt
```

### 3 – Set up Ollama (LLM)

```bash
# Install Ollama from https://ollama.com
ollama serve          # start the server
ollama pull llama3    # download the model (~4 GB)
```

### 4 – Configure environment variables

```bash
# Copy the example file and fill in your real values
copy .env.example .env
```

Edit `.env`:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+91XXXXXXXXXX
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

> **Note:** WhatsApp is optional. The app runs fully without Twilio credentials.

### 5 – (Optional) Install Tesseract for brochure image OCR

- **Windows:** Download installer from https://github.com/UB-Mannheim/tesseract/wiki  
  Add Tesseract to PATH or set `TESSDATA_PREFIX`.
- **macOS:**   `brew install tesseract`
- **Linux:**   `sudo apt install tesseract-ocr`

### 6 – Run the app

```bash
streamlit run main.py
```

Open your browser at **http://localhost:8501**

---

## Usage Guide

### First Time
1. Click **Sign Up** → fill in your business details
2. Log in with your new account
3. Click **▶ Run Intelligence Scan** in the sidebar
4. Explore all War Room sections

### War Room Sections

| Section | What it shows |
|---|---|
| 🚨 Competitor Alerts | New launches, price drops, campaigns detected |
| 🔮 AI Prediction | Trending categories + AI strategy |
| ⭐ Google Review Analysis | Sentiment graphs for competitor reviews |
| 📢 Social Media Trends | Instagram hashtags + engagement data |
| 📍 Competitor Map | Interactive Coimbatore store location map |
| 🤖 AI Business Advisor | Chat with the LangChain + Ollama chatbot |
| 📊 Business Performance | 5 Plotly charts + sales data entry |
| 📄 Brochure Intelligence | Upload competitor PDFs/images for AI analysis |
| ⚙️ Settings | Manage competitors, check LLM/WhatsApp status |

### Business Performance – data entry
Navigate to **📊 Business Performance** → expand the *Add / Update Today's Sales Data* form → enter units sold, revenue, inventory count and optional customer feedback → click **Save**.

### Brochure Intelligence
Go to **📄 Brochure Intelligence** → upload a competitor's PDF flyer or image → receive:
- Extracted text
- Detected products and promotions
- AI-generated business suggestions

### Test the pipeline via CLI (no UI)
```bash
python orchestrator.py
```

---

## Agent Communication Flow

```
┌─────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                      │
│             orchestrator.run_pipeline()              │
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  SCOUT AGENT (A) – agents/scout_agent.py             │
│  • Runs CompetitorScraper, SocialScraper,            │
│    ReviewScraper                                     │
│  • Returns ScoutReport (JSON)                        │
└──────┬───────────────────────────────────────────────┘
       │ ScoutReport
       ▼
┌──────────────────────────────────────────────────────┐
│  ANALYST AGENT (B) – agents/analyst_agent.py         │
│  • Price comparison, sentiment, threat detection     │
│  • LangChain + Ollama llama3 for narrative           │
│  • Returns AnalysisReport                            │
└──────┬───────────────────────────────────────────────┘
       │ AnalysisReport
       ▼
┌──────────────────────────────────────────────────────┐
│  STRATEGIST AGENT (C) – agents/strategist_agent.py   │
│  • Generates pricing / product / campaign strategy   │
│  • Creates Instagram captions + WhatsApp messages    │
│  • Fires WhatsApp alerts via Twilio                  │
│  • Returns StrategyReport                            │
└──────────────────────────────────────────────────────┘
```

---

## WhatsApp Alert Example

```
🚨 Competitor Alert!

Brand: FashionHub Coimbatore
New Launch: Denim Jacket
Price: ₹1299

Suggested Strategy:
Launch a similar product with 10% introductory discount.

Suggested Instagram Caption:
"Upgrade your style with our new denim collection 🔥"
```

---

## Graphs Available (📊 Business Performance)

1. **Sales Growth Rate** – line chart with 7-day rolling average
2. **Monthly Revenue** – bar chart by month
3. **Competitor vs Your Price** – grouped bar + your avg line
4. **Customer Review Sentiment** – donut chart (positive/neutral/negative)
5. **Product Performance by Category** – horizontal bar chart

---

## Tech Stack

| Component | Technology |
|---|---|
| UI / Dashboard | Streamlit |
| LLM / Agents | LangChain + Ollama llama3 |
| Web Scraping | Requests + BeautifulSoup |
| Database | SQLite |
| Visualisation | Plotly |
| Notifications | Twilio WhatsApp API |
| OCR | pytesseract + Pillow |
| PDF Parsing | PyPDF2 |
| Sentiment | TextBlob |
| Auth | bcrypt |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "Ollama not reachable" | Run `ollama serve` and check `http://localhost:11434` |
| "llama3 model not found" | Run `ollama pull llama3` |
| OCR returns empty text | Install Tesseract and ensure it is on PATH |
| WhatsApp not sending | Check `.env` credentials; join the Twilio sandbox |
| Import error on startup | Run `pip install -r requirements.txt` |

---

*Built with Python 3.11 · LangChain · Ollama · Streamlit · SQLite*
