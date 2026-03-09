"""
dashboard/dashboard.py

War-Room Dashboard – the main Streamlit UI after login.

Sections (sidebar navigation)
------------------------------
🚨 Competitor Alerts
🔮 AI Prediction
⭐ Google Review Analysis
📢 Social Media Trends
📍 Competitor Map
🤖 AI Business Advisor Chat
📊 Business Performance
📄 Brochure Intelligence
⚙️  Settings
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from config import SAMPLE_COMPETITORS, TRENDING_CATEGORIES
from database import db

logger = logging.getLogger(__name__)


# ─────────────────────────────  GLOBAL CSS  ──────────────────────────────────

_CSS = """
<style>
/* Sidebar */
[data-testid="stSidebar"] {background: #0f3460;}
[data-testid="stSidebar"] * {color: #e2e8f0 !important;}

/* Card */
.kpi-card {
    background: linear-gradient(135deg,#1a1a2e,#16213e);
    border-left: 4px solid #e94560;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.kpi-value {font-size:1.8rem;font-weight:800;color:#e94560;}
.kpi-label {font-size:.85rem;color:#a0aec0;}

/* Alert card */
.alert-card {
    background:#1a1a2e;border-left:4px solid #f5a623;
    border-radius:8px;padding:.8rem 1rem;margin:.5rem 0;
}
.alert-type {font-size:.75rem;color:#f5a623;font-weight:700;text-transform:uppercase;}
.alert-title {font-size:1rem;font-weight:600;color:#e2e8f0;}
.alert-msg {font-size:.85rem;color:#a0aec0;}

/* Caption box */
.caption-box {
    background:#16213e;border:1px solid #e94560;border-radius:8px;
    padding:.8rem 1rem;margin:.4rem 0;font-style:italic;color:#e2e8f0;
}
</style>
"""


# ─────────────────────────────  ENTRY POINT  ─────────────────────────────────

def render_dashboard() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    user_data  = st.session_state.get("user_data", {})
    user_id    = st.session_state.get("user_id", 0)
    business   = user_data.get("business_name", "Your Business")

    _sidebar(user_data, user_id)

    page = st.session_state.get("current_page", "Competitor Alerts")

    page_map = {
        "Competitor Alerts":      _page_alerts,
        "AI Prediction":          _page_predictions,
        "Google Review Analysis": _page_reviews,
        "Social Media Trends":    _page_social,
        "Competitor Map":         _page_map,
        "AI Business Advisor":    _page_advisor,
        "Business Performance":   _page_performance,
        "Brochure Intelligence":  _page_brochure,
        "Settings":               _page_settings,
    }

    handler = page_map.get(page, _page_alerts)
    handler(user_id, user_data)


# ─────────────────────────────  SIDEBAR  ─────────────────────────────────────

def _sidebar(user_data: Dict, user_id: int) -> None:
    with st.sidebar:
        st.markdown(
            f"### 🧵 {user_data.get('business_name', 'My Business')}"
        )
        st.caption(f"📍 {user_data.get('city', '')}  |  {user_data.get('clothing_category', '')}")
        st.markdown("---")

        # Run agents button
        if st.button("▶ Run Intelligence Scan", use_container_width=True, type="primary"):
            _run_agents(user_id, user_data)

        st.markdown("---")

        # Navigation
        unread = db.get_unread_count(user_id)
        alert_label = f"🚨 Competitor Alerts" + (f"  **({unread})**" if unread else "")

        nav_items = [
            alert_label,
            "🔮 AI Prediction",
            "⭐ Google Review Analysis",
            "📢 Social Media Trends",
            "📍 Competitor Map",
            "🤖 AI Business Advisor",
            "📊 Business Performance",
            "📄 Brochure Intelligence",
            "⚙️  Settings",
        ]
        # Map display label → internal key
        _key_map = {item: item.lstrip("🚨🔮⭐📢📍🤖📊📄⚙️ ").strip() for item in nav_items}
        _key_map[alert_label] = "Competitor Alerts"

        for item in nav_items:
            key = _key_map[item]
            active = st.session_state.get("current_page") == key
            if st.button(item, use_container_width=True,
                         key=f"nav_{key}",
                         type="secondary" if not active else "primary"):
                st.session_state.current_page = key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ─────────────────────────────  RUN AGENTS  ──────────────────────────────────

def _run_agents(user_id: int, user_data: Dict) -> None:
    """Trigger the full scout → analyst → strategist pipeline."""
    with st.sidebar:
        with st.spinner("🔍 Scouts gathering intelligence…"):
            try:
                from orchestrator import run_pipeline
                competitors = db.get_competitors(user_id)
                if not competitors:
                    # Seed with sample competitors
                    for sc in SAMPLE_COMPETITORS:
                        db.add_competitor(
                            user_id   = user_id,
                            name      = sc["name"],
                            website   = sc.get("website", ""),
                            location  = sc.get("location", ""),
                            category  = sc.get("category", ""),
                            instagram = sc.get("instagram", ""),
                        )
                    competitors = db.get_competitors(user_id)

                from config import TWILIO_ACCOUNT_SID, TWILIO_WHATSAPP_TO
                wa_enabled = bool(
                    TWILIO_ACCOUNT_SID
                    and TWILIO_WHATSAPP_TO
                    and "XXXXXXXXXX" not in TWILIO_WHATSAPP_TO
                )
                result = run_pipeline(
                    user_id       = user_id,
                    user_data     = user_data,
                    competitors   = competitors,
                    send_whatsapp = wa_enabled,
                )
                st.session_state.last_run_report = result
                st.success("✅ Intelligence scan complete!")
            except Exception as exc:
                logger.exception("Agent pipeline error")
                st.error(f"Scan failed: {exc}")


# ─────────────────────────────  PAGE: COMPETITOR ALERTS  ─────────────────────

def _page_alerts(user_id: int, user_data: Dict) -> None:
    st.title("🚨 Competitor Alerts")
    st.caption("Real-time intelligence from competitor stores")

    db.mark_alerts_read(user_id)

    # KPIs from DB
    updates = db.get_recent_updates(user_id, limit=50)
    new_launches = [u for u in updates if u["update_type"] == "new_launch"]
    discounts    = [u for u in updates if u["update_type"] == "price_drop"]
    campaigns    = [u for u in updates if u["update_type"] == "campaign"]

    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, len(updates),      "Total Updates")
    _kpi(c2, len(new_launches), "New Launches",  "🚀")
    _kpi(c3, len(discounts),    "Price Drops",   "💸")
    _kpi(c4, len(campaigns),    "Campaigns",     "📢")

    st.markdown("---")

    # Filter
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        selected_type = st.selectbox(
            "Filter by type",
            ["All", "new_launch", "price_drop", "campaign"],
        )
    with col_f2:
        comp_names = list({u["competitor_name"] for u in updates})
        sel_comp   = st.selectbox("Filter by competitor", ["All"] + sorted(comp_names))

    filtered = updates
    if selected_type != "All":
        filtered = [u for u in filtered if u["update_type"] == selected_type]
    if sel_comp != "All":
        filtered = [u for u in filtered if u["competitor_name"] == sel_comp]

    if not filtered:
        st.info("No alerts yet. Click **▶ Run Intelligence Scan** in the sidebar.")
        _show_sample_alerts()
        return

    for upd in filtered[:25]:
        emoji = {"new_launch": "🚀", "price_drop": "💸", "campaign": "📢"}.get(
            upd["update_type"], "⚠️"
        )
        with st.container():
            st.markdown(
                f"""<div class="alert-card">
                <div class="alert-type">{emoji} {upd['update_type'].replace('_',' ').upper()}</div>
                <div class="alert-title">{upd['title']}</div>
                <div class="alert-msg">{upd.get('description','')}</div>
                <div class="alert-msg" style="margin-top:.3rem;color:#4a5568;">
                  🏪 {upd['competitor_name']} &nbsp;·&nbsp; 🕐 {str(upd['detected_at'])[:16]}
                </div>
                </div>""",
                unsafe_allow_html=True,
            )


def _show_sample_alerts() -> None:
    st.markdown("#### 📋 Sample Alerts Preview")
    samples = [
        ("🚀", "new_launch", "New Launch: Denim Jacket", "FashionHub", "₹1299"),
        ("💸", "price_drop",  "Price Drop: Cotton Kurta", "StyleZone",  "₹799 → ₹599  (25% off)"),
        ("📢", "campaign",    "Campaign: Summer Sale – 40% Off", "TrendSetters", ""),
    ]
    for emoji, typ, title, comp, detail in samples:
        st.markdown(
            f"""<div class="alert-card">
            <div class="alert-type">{emoji} {typ.replace('_',' ').upper()}</div>
            <div class="alert-title">{title}</div>
            <div class="alert-msg">{detail}</div>
            <div class="alert-msg" style="margin-top:.3rem;color:#4a5568;">🏪 {comp}</div>
            </div>""",
            unsafe_allow_html=True,
        )


# ─────────────────────────────  PAGE: AI PREDICTIONS  ────────────────────────

def _page_predictions(user_id: int, user_data: Dict) -> None:
    st.title("🔮 AI Trend Predictions")
    st.caption("Upcoming clothing trends for the next 90 days")

    report = st.session_state.get("last_run_report") or {}
    analysis  = report.get("analysis", {})
    strategy  = report.get("strategy", {})

    trending  = analysis.get("trending_categories") or TRENDING_CATEGORIES[:6]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Trending Categories")
        for i, cat in enumerate(trending[:6], 1):
            score = round(10 - i * 0.4, 1)
            st.progress(int(score * 10), text=f"**{cat}** — Buzz Score {score}/10")

    with col2:
        st.subheader("💡 AI Recommendations")
        if strategy.get("product_ideas"):
            for idea in strategy["product_ideas"]:
                st.markdown(f"• {idea}")
        else:
            for tip in [
                "Launch a festive ethnic fusion collection for Diwali season.",
                "Introduce eco-friendly organic cotton kurtas.",
                "Stock up on oversized graphic tees for the college demographic.",
                "Create a wedding-season capsule (8–12 exclusive pieces).",
                "Bundle kurta+dupatta sets at a 10% combined discount.",
            ]:
                st.markdown(f"• {tip}")

    st.markdown("---")

    # LLM strategy narrative
    if strategy.get("llm_strategy"):
        st.subheader("🤖 Full AI Strategy Report")
        st.markdown(strategy["llm_strategy"])
    elif analysis.get("llm_report"):
        st.subheader("🤖 Market Analysis Report")
        st.markdown(analysis["llm_report"])
    else:
        st.info("Run an Intelligence Scan to generate an AI strategy report.")


# ─────────────────────────────  PAGE: REVIEWS  ───────────────────────────────

def _page_reviews(user_id: int, user_data: Dict) -> None:
    st.title("⭐ Google Review Analysis")

    from dashboard.growth_graphs import sentiment_donut_chart

    sentiment = db.get_sentiment_summary(user_id)
    all_reviews = db.get_all_reviews_for_user(user_id)

    col1, col2 = st.columns([1.2, 1])
    with col1:
        fig = sentiment_donut_chart(sentiment)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        total = sum(sentiment.values()) or 1
        st.metric("Total Reviews",   sum(sentiment.values()))
        st.metric("👍 Positive",     f"{sentiment.get('positive',0)}  "
                  f"({sentiment.get('positive',0)/total*100:.0f}%)")
        st.metric("😐 Neutral",      f"{sentiment.get('neutral',0)}  "
                  f"({sentiment.get('neutral',0)/total*100:.0f}%)")
        st.metric("👎 Negative",     f"{sentiment.get('negative',0)}  "
                  f"({sentiment.get('negative',0)/total*100:.0f}%)")

    st.markdown("---")
    st.subheader("📝 Recent Reviews")
    if all_reviews:
        df = pd.DataFrame(all_reviews)[
            ["competitor_name", "reviewer_name", "review_text", "rating", "sentiment_label"]
        ]
        st.dataframe(df, use_container_width=True, height=320)
    else:
        st.info("Run an Intelligence Scan to populate review data.")


# ─────────────────────────────  PAGE: SOCIAL  ────────────────────────────────

def _page_social(user_id: int, user_data: Dict) -> None:
    st.title("📢 Social Media Trends")

    report = st.session_state.get("last_run_report") or {}
    scout  = report.get("scout", {})

    hashtags = scout.get("trending_hashtags") or []
    topics   = scout.get("trending_topics")   or []

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔖 Trending Hashtags")
        if hashtags:
            hdf = pd.DataFrame(hashtags)
            st.dataframe(
                hdf[["tag", "engagement_score", "posts_count", "trend_direction"]],
                use_container_width=True, height=360,
            )
        else:
            from config import CLOTHING_HASHTAGS
            import random
            dummy = [
                {"tag": t, "posts_count": random.randint(5000, 400000),
                 "engagement_score": round(random.uniform(4, 9.5), 1),
                 "trend_direction": random.choice(["↑ Rising", "→ Stable"])}
                for t in random.sample(CLOTHING_HASHTAGS, 12)
            ]
            st.dataframe(pd.DataFrame(dummy), use_container_width=True, height=360)

    with col2:
        st.subheader("🔥 Trending Topics")
        if topics:
            for t in topics:
                st.markdown(
                    f"**{t['topic']}** — Buzz {t['buzz_score']}/10  "
                    f"({t['weekly_growth']})"
                )
        else:
            import random
            for cat in TRENDING_CATEGORIES[:8]:
                growth = f"+{random.randint(5,40)}%"
                buzz   = round(random.uniform(5, 10), 1)
                st.markdown(f"**{cat}** — Buzz {buzz}/10  ({growth})")

    # Social presence chart
    st.markdown("---")
    from dashboard.growth_graphs import social_engagement_chart
    social_rows = [
        c.get("social", {}) for c in scout.get("competitors", [])
        if c.get("social")
    ]
    fig = social_engagement_chart(social_rows or None)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────  PAGE: MAP  ───────────────────────────────────

def _page_map(user_id: int, user_data: Dict) -> None:
    st.title("📍 Competitor Store Locations")
    st.caption("Geographical overview of competitors in your area")

    competitors = db.get_competitors(user_id)
    if not competitors:
        competitors = [dict(c) for c in SAMPLE_COMPETITORS]

    # Coimbatore area lat/long estimates per locality
    _LOC_COORDS = {
        "RS Puram":      (11.004, 76.961),
        "Gandhipuram":   (11.018, 76.975),
        "Peelamedu":     (11.022, 77.027),
        "Saibaba Colony":(11.011, 76.956),
        "Brookefields":  (11.007, 77.049),
        "default":       (11.0168, 76.9558),
    }

    map_data: List[Dict] = []
    for comp in competitors:
        loc  = comp.get("location", "default")
        key  = next((k for k in _LOC_COORDS if k in loc), "default")
        lat, lon = _LOC_COORDS[key]
        map_data.append(
            {
                "name":     comp["name"],
                "location": loc,
                "category": comp.get("category", ""),
                "lat":      lat  + (hash(comp["name"]) % 200 - 100) * 0.0003,
                "lon":      lon  + (hash(comp["name"]) % 150 - 75)  * 0.0003,
            }
        )

    df = pd.DataFrame(map_data)
    fig = px.scatter_mapbox(
        df,
        lat="lat", lon="lon",
        hover_name="name",
        hover_data={"location": True, "category": True, "lat": False, "lon": False},
        color="category",
        size_max=20,
        zoom=12,
        mapbox_style="open-street-map",
        title="Competitor Locations – Coimbatore",
        color_discrete_sequence=["#e94560", "#f5a623", "#00b4d8", "#06d6a0", "#9b5de5"],
    )
    fig.update_layout(template="plotly_dark", height=520)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df[["name", "location", "category"]].rename(
            columns={"name": "Competitor", "location": "Location", "category": "Category"}
        ),
        use_container_width=True,
    )


# ─────────────────────────────  PAGE: AI ADVISOR  ────────────────────────────

def _page_advisor(user_id: int, user_data: Dict) -> None:
    st.title("🤖 AI Business Advisor Chat")
    st.caption("Powered by LangChain + Ollama (llama3)")

    # Initialise chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    f"Hello! I'm your AI Business Advisor for **{user_data.get('business_name', 'your store')}**. "
                    "Ask me anything about pricing, marketing, trends, or competitor strategies. 💬"
                ),
            }
        ]

    # Display history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask your business advisor…"):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                reply = _advisor_reply(prompt, user_data)
            st.markdown(reply)
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})


def _advisor_reply(question: str, user_data: Dict) -> str:
    """Get reply from Ollama or fall back to a rule-based answer."""
    system_ctx = (
        f"You are a marketing expert for {user_data.get('business_name','a clothing store')} "
        f"in {user_data.get('city','India')}. "
        f"Category: {user_data.get('clothing_category','clothing')}. "
        f"Price range: {user_data.get('avg_price_range','mid-range')}. "
        "Give practical, concise advice for Indian small business owners."
    )
    try:
        import requests as _req
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        _req.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        from langchain_ollama import OllamaLLM
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        prompt_tmpl = PromptTemplate(
            template=(
                "System: {system}\n\nUser Question: {question}\n\nAnswer:"
            ),
            input_variables=["system", "question"],
        )
        chain = prompt_tmpl | OllamaLLM(
            model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.6
        ) | StrOutputParser()
        return str(chain.invoke({"system": system_ctx, "question": question}))
    except Exception:
        return _fallback_advisor(question, user_data)


def _fallback_advisor(question: str, user_data: Dict) -> str:
    q = question.lower()
    city = user_data.get("city", "your city")
    cat  = user_data.get("clothing_category", "clothing")
    if any(w in q for w in ["price", "pricing", "charge"]):
        return (
            f"For {cat} in {city}, consider a tiered pricing strategy: "
            "budget line (₹399–₹699), core range (₹700–₹1999), and a premium line (₹2000+). "
            "This captures all customer segments without undercutting your margins."
        )
    if any(w in q for w in ["instagram", "social", "post", "reel"]):
        return (
            "Top Instagram tactics for clothing stores:\n"
            "1. Post 3–4 Reels/week using trending sounds\n"
            "2. Use hashtags like #EthnicWear #IndianFashion #ClothingHaul\n"
            "3. Show before/after outfit combos\n"
            "4. Run giveaways to boost reach\n"
            "5. Collaborate with local micro-influencers (5k–50k followers)"
        )
    if any(w in q for w in ["discount", "sale", "offer"]):
        return (
            "Effective discount strategies:\n"
            "• End-of-season sale (30–50% off) to clear inventory\n"
            "• Loyalty programme (every ₹5000 spent = ₹200 voucher)\n"
            "• Bundle deals (Kurta + Dupatta = 10% off)\n"
            "• Flash sales (48-hour WhatsApp broadcast specials)\n"
            "Avoid discounting too frequently — it erodes brand value."
        )
    if any(w in q for w in ["competitor", "competition", "rival"]):
        return (
            f"How to stay ahead of competitors in {city}:\n"
            "1. Monitor their Instagram and note new launches weekly\n"
            "2. Match or beat their sale prices within 24 hours\n"
            "3. Focus on a niche category they don't serve well\n"
            "4. Offer superior packaging and personalised service\n"
            "5. Build a WhatsApp community for loyal customers"
        )
    return (
        f"Great question for a {cat} business in {city}! "
        "To get AI-powered insights, ensure Ollama is running locally with the llama3 model. "
        "In the meantime, focus on: consistent social media posting, "
        "competitive pricing, and building customer loyalty through personalised service."
    )


# ─────────────────────────────  PAGE: PERFORMANCE  ───────────────────────────

def _page_performance(user_id: int, user_data: Dict) -> None:
    st.title("📊 Business Performance")

    # ── Data Entry ─────────────────────────────────────────────────────────
    with st.expander("➕ Add / Update Today's Sales Data"):
        with st.form("sales_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                sale_date   = st.date_input("Date", value=date.today())
                daily_sales = st.number_input("Units Sold", min_value=0, value=0)
            with col2:
                revenue     = st.number_input("Revenue (₹)", min_value=0.0, value=0.0, step=50.0)
                inventory   = st.number_input("Inventory Count", min_value=0, value=100)
            with col3:
                reviews_txt = st.text_area("Customer Feedback (optional)", height=90)
            if st.form_submit_button("Save", type="primary"):
                ok = db.upsert_sales(
                    user_id, sale_date.isoformat(), int(daily_sales),
                    float(revenue), int(inventory), reviews_txt
                )
                st.success("Saved ✅") if ok else st.error("Save failed.")

    # ── Load data ──────────────────────────────────────────────────────────
    sales_rows = db.get_sales_data(user_id, days=60)

    from dashboard.growth_graphs import (
        monthly_revenue_chart,
        price_comparison_chart,
        product_performance_chart,
        sales_growth_chart,
        sentiment_donut_chart,
    )

    report    = st.session_state.get("last_run_report") or {}
    analysis  = report.get("analysis", {})
    scout     = report.get("scout",    {})

    # Row 1
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(sales_growth_chart(sales_rows or []),    use_container_width=True)
    with col2:
        st.plotly_chart(monthly_revenue_chart(sales_rows or []), use_container_width=True)

    # Row 2
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(
            price_comparison_chart(analysis.get("price_comparison")),
            use_container_width=True,
        )
    with col4:
        sentiment = db.get_sentiment_summary(user_id)
        st.plotly_chart(sentiment_donut_chart(sentiment), use_container_width=True)

    # Row 3 – full width
    comp_data = [c for c in scout.get("competitors", [])]
    st.plotly_chart(
        product_performance_chart(comp_data or None),
        use_container_width=True,
    )

    # Raw table
    if sales_rows:
        st.subheader("📋 Sales Data Table")
        df = pd.DataFrame(sales_rows)[[
            "sale_date", "daily_sales", "revenue", "inventory_count"
        ]].rename(columns={
            "sale_date": "Date", "daily_sales": "Units Sold",
            "revenue": "Revenue (₹)", "inventory_count": "Inventory",
        })
        st.dataframe(df, use_container_width=True, height=250)


# ─────────────────────────────  PAGE: BROCHURE  ──────────────────────────────

def _page_brochure(user_id: int, user_data: Dict) -> None:
    st.title("📄 Brochure Intelligence")
    st.caption("Upload competitor brochures (PDF or image) for AI analysis")

    uploaded = st.file_uploader(
        "Upload a competitor brochure / flyer",
        type=["pdf", "jpg", "jpeg", "png", "tiff", "bmp", "txt"],
        help="Supports PDF, images (JPG/PNG), and plain text files.",
    )

    if uploaded:
        with st.spinner("🔍 Extracting and analysing…"):
            try:
                from brochure_analysis.brochure_reader import BrochureReader

                reader = BrochureReader()
                result = reader.analyse(
                    file_bytes = uploaded.read(),
                    filename   = uploaded.name,
                    user_data  = user_data,
                )

                # Persist to DB
                db.save_brochure_analysis(
                    user_id         = user_id,
                    filename        = result["filename"],
                    file_type       = result["file_type"],
                    extracted_text  = result["extracted_text"],
                    analysis_result = result["analysis_result"],
                    suggestions     = result["suggestions"],
                )

                tab1, tab2, tab3, tab4 = st.tabs(
                    ["🔍 Analysis", "💡 Suggestions", "📦 Products", "📝 Raw Text"]
                )
                with tab1:
                    st.markdown(result["analysis_result"])
                    if not result["llm_available"]:
                        st.info("💡 Start Ollama for deeper AI analysis.")
                with tab2:
                    st.markdown(result["suggestions"])
                with tab3:
                    if result["products_detected"]:
                        for p in result["products_detected"]:
                            st.markdown(f"• {p}")
                    else:
                        st.write("No specific product mentions detected.")
                    st.markdown("**Promotions:**")
                    for pr in result.get("promos_detected", []):
                        st.markdown(f"• {pr}")
                with tab4:
                    st.text_area("Extracted text", result["extracted_text"], height=300)

            except Exception as exc:
                logger.exception("Brochure analysis error")
                st.error(f"Analysis failed: {exc}")

    # Past analyses
    past = db.get_brochure_analyses(user_id, limit=8)
    if past:
        st.markdown("---")
        st.subheader("📁 Past Brochure Analyses")
        for item in past:
            with st.expander(f"{item['filename']} — {str(item['uploaded_at'])[:16]}"):
                st.markdown(item["analysis_result"])
                if item["suggestions"]:
                    st.markdown("**Suggestions:**")
                    st.markdown(item["suggestions"])


# ─────────────────────────────  PAGE: SETTINGS  ──────────────────────────────

def _page_settings(user_id: int, user_data: Dict) -> None:
    st.title("⚙️  Settings")

    st.subheader("👤 Business Profile")
    st.json(
        {k: v for k, v in user_data.items()
         if k not in {"id", "password_hash", "created_at"}}
    )

    st.subheader("🏪 Manage Competitors")
    competitors = db.get_competitors(user_id)
    if competitors:
        df = pd.DataFrame(competitors)[["name", "location", "category", "website"]]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No competitors added yet. Run an intelligence scan to auto-add sample competitors.")

    with st.expander("➕ Add Custom Competitor"):
        with st.form("add_comp_form"):
            c1, c2 = st.columns(2)
            with c1:
                cname    = st.text_input("Name *")
                cwebsite = st.text_input("Website")
            with c2:
                cloc     = st.text_input("Location")
                ccat     = st.selectbox("Category",
                    ["Ethnic Wear", "Western Wear", "Casual & Western",
                     "Cotton Traditional", "Street Fashion", "Other"])
            cig = st.text_input("Instagram handle")
            if st.form_submit_button("Add Competitor", type="primary"):
                if not cname:
                    st.error("Name is required.")
                else:
                    db.add_competitor(user_id, cname, cwebsite, cloc, ccat, cig)
                    st.success(f"'{cname}' added.")
                    st.rerun()

    st.subheader("🔔 WhatsApp Notifications")
    from config import TWILIO_ACCOUNT_SID, TWILIO_WHATSAPP_TO
    if TWILIO_ACCOUNT_SID and TWILIO_WHATSAPP_TO:
        st.success(f"WhatsApp configured → sending to {TWILIO_WHATSAPP_TO}")
    else:
        st.warning(
            "WhatsApp not configured. Add TWILIO_ACCOUNT_SID and TWILIO_WHATSAPP_TO "
            "to your `.env` file to enable alerts."
        )

    st.subheader("🤖 LLM Status")
    try:
        import requests as _req
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        resp = _req.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        models = [m["name"] for m in resp.json().get("models", [])]
        if any(OLLAMA_MODEL in m for m in models):
            st.success(f"✅ Ollama running – model **{OLLAMA_MODEL}** found.")
        else:
            st.warning(
                f"Ollama is running but model **{OLLAMA_MODEL}** not found. "
                f"Run: `ollama pull {OLLAMA_MODEL}`"
            )
    except Exception:
        st.error(
            "Ollama is not reachable at http://localhost:11434. "
            "Install Ollama and run: `ollama serve && ollama pull llama3`"
        )


# ─────────────────────────────  SHARED HELPERS  ──────────────────────────────

def _kpi(col, value, label: str, emoji: str = "") -> None:
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-value">{emoji} {value}</div>'
            f'<div class="kpi-label">{label}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
