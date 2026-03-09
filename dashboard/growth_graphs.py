"""
dashboard/growth_graphs.py

All Plotly charts for the Business Performance section.

Graphs provided
---------------
1.  Sales Growth Rate        – line chart
2.  Monthly Revenue          – bar chart
3.  Competitor vs Your Price – grouped bar chart
4.  Customer Review Sentiment– donut chart
5.  Product Performance      – horizontal bar chart
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Plotly theme ─────────────────────────────────────────────────────────────
_THEME     = "plotly_dark"
_ACCENT    = "#e94560"
_SECONDARY = "#f5a623"
_COLORS    = ["#e94560", "#f5a623", "#00b4d8", "#06d6a0", "#9b5de5", "#f15bb5"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. SALES GROWTH RATE
# ─────────────────────────────────────────────────────────────────────────────

def sales_growth_chart(sales_rows: List[Dict]) -> go.Figure:
    """Line chart showing daily sales count with a 7-day rolling average."""
    if not sales_rows:
        sales_rows = _demo_sales()

    df = pd.DataFrame(sales_rows).sort_values("sale_date")
    df["sale_date"]      = pd.to_datetime(df["sale_date"])
    df["rolling_avg"]    = df["daily_sales"].rolling(7, min_periods=1).mean().round(1)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["sale_date"], y=df["daily_sales"],
            mode="lines+markers",
            name="Daily Sales",
            line=dict(color=_ACCENT, width=2),
            marker=dict(size=5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["sale_date"], y=df["rolling_avg"],
            mode="lines",
            name="7-Day Avg",
            line=dict(color=_SECONDARY, width=2.5, dash="dot"),
        )
    )
    fig.update_layout(
        template=_THEME,
        title="📈 Sales Growth Rate",
        xaxis_title="Date",
        yaxis_title="Units Sold",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 2. MONTHLY REVENUE
# ─────────────────────────────────────────────────────────────────────────────

def monthly_revenue_chart(sales_rows: List[Dict]) -> go.Figure:
    """Bar chart of monthly revenue totals."""
    if not sales_rows:
        sales_rows = _demo_sales()

    df = pd.DataFrame(sales_rows)
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["month"]     = df["sale_date"].dt.to_period("M").astype(str)
    monthly         = df.groupby("month", as_index=False)["revenue"].sum()

    fig = px.bar(
        monthly,
        x="month", y="revenue",
        color="revenue",
        color_continuous_scale=["#16213e", _ACCENT],
        labels={"month": "Month", "revenue": "Revenue (₹)"},
        title="💰 Monthly Revenue",
        template=_THEME,
        text_auto=True,
    )
    fig.update_traces(texttemplate="₹%{y:,.0f}", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, showlegend=False)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 3. COMPETITOR vs YOUR PRICE
# ─────────────────────────────────────────────────────────────────────────────

def price_comparison_chart(
    price_data: Optional[Dict],
    user_avg: float = 1200,
) -> go.Figure:
    """Grouped bar: each competitor's avg price stacked against yours."""
    if price_data and price_data.get("competitors"):
        comps  = price_data["competitors"]
        names  = [c["competitor"] for c in comps]
        prices = [c["avg_price"] for c in comps]
        user_avg = price_data.get("user_avg", user_avg)
    else:
        names  = ["FashionHub", "TrendSetters", "StyleZone", "Cotton House", "Urban Threads"]
        prices = [random.randint(900, 2800) for _ in names]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Competitors",
            x=names,
            y=prices,
            marker_color=_ACCENT,
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Your Avg Price",
            x=names,
            y=[user_avg] * len(names),
            mode="lines",
            line=dict(color=_SECONDARY, width=3, dash="dash"),
        )
    )
    fig.update_layout(
        template=_THEME,
        title="🏷️ Competitor vs Your Average Price (₹)",
        xaxis_title="Competitor",
        yaxis_title="Average Price (₹)",
        barmode="group",
        legend=dict(orientation="h", y=1.1),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 4. REVIEW SENTIMENT (donut)
# ─────────────────────────────────────────────────────────────────────────────

def sentiment_donut_chart(sentiment: Optional[Dict]) -> go.Figure:
    """Donut chart of Positive / Neutral / Negative review distribution."""
    if sentiment and any(sentiment.values()):
        labels = list(sentiment.keys())
        values = list(sentiment.values())
    else:
        labels = ["Positive", "Neutral", "Negative"]
        values = [58, 24, 18]

    colours = ["#06d6a0", "#f5a623", "#e94560"]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=colours[:len(labels)]),
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        template=_THEME,
        title="⭐ Customer Review Sentiment",
        showlegend=True,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5. PRODUCT PERFORMANCE (horizontal bar)
# ─────────────────────────────────────────────────────────────────────────────

def product_performance_chart(
    competitor_data: Optional[List[Dict]] = None,
) -> go.Figure:
    """Horizontal bar: units-sold proxy per product category across competitors."""
    if competitor_data:
        # Tally products by category
        cat_count: Dict[str, int] = {}
        for comp in competitor_data:
            for item in comp.get("products", []):
                cat = item.get("cat", "other").replace("_", " ").title()
                cat_count[cat] = cat_count.get(cat, 0) + 1
        if cat_count:
            df = (
                pd.DataFrame(list(cat_count.items()), columns=["Category", "Count"])
                .sort_values("Count")
                .tail(10)
            )
            x_col, y_col = "Count", "Category"
            x_lbl, x_ttl = "Competitor Item Count", "No. of Products in Market"
        else:
            df, x_col, y_col, x_lbl, x_ttl = _default_product_df()
    else:
        df, x_col, y_col, x_lbl, x_ttl = _default_product_df()

    fig = px.bar(
        df,
        x=x_col, y=y_col,
        orientation="h",
        color=x_col,
        color_continuous_scale=["#16213e", "#00b4d8"],
        labels={x_col: x_lbl, y_col: "Category"},
        title="📦 Product Performance by Category",
        template=_THEME,
        text=x_col,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(coloraxis_showscale=False, showlegend=False,
                      xaxis_title=x_ttl)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 6. ENGAGEMENT BUBBLE (bonus / social)
# ─────────────────────────────────────────────────────────────────────────────

def social_engagement_chart(social_data: Optional[List[Dict]] = None) -> go.Figure:
    """Bubble chart: competitor Instagram followers vs. engagement rate."""
    if social_data:
        names       = [s["competitor_name"] for s in social_data]
        followers   = [s.get("followers", 1000) for s in social_data]
        engagement  = [s.get("engagement_rate", 2.0) for s in social_data]
        posts       = [s.get("posts_this_week", 5) * 10 for s in social_data]
    else:
        names      = ["FashionHub", "TrendSetters", "StyleZone", "Cotton House", "Urban Threads"]
        followers  = [12000, 8500, 22000, 5000, 45000]
        engagement = [4.2, 3.8, 5.1, 2.9, 6.7]
        posts      = [70, 50, 90, 30, 140]

    fig = go.Figure(
        go.Scatter(
            x=followers, y=engagement,
            mode="markers+text",
            marker=dict(size=posts, color=_COLORS[:len(names)], opacity=0.8),
            text=names,
            textposition="top center",
        )
    )
    fig.update_layout(
        template=_THEME,
        title="📱 Competitor Social Media Presence",
        xaxis_title="Instagram Followers",
        yaxis_title="Engagement Rate (%)",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _demo_sales() -> List[Dict]:
    today  = date.today()
    base   = 35
    rows   = []
    for i in range(60, 0, -1):
        d   = today - timedelta(days=i)
        qty = max(5, int(base + random.gauss(0, 8)))
        rev = qty * random.uniform(700, 1800)
        rows.append(
            {
                "sale_date":     d.isoformat(),
                "daily_sales":   qty,
                "revenue":       round(rev, 2),
                "inventory_count": random.randint(80, 300),
            }
        )
        base += random.uniform(-1, 2)   # slight upward drift
    return rows


def _default_product_df():
    data = {
        "Category": ["Kurta", "Saree", "T-Shirt", "Jeans", "Hoodie",
                      "Dress", "Jacket", "Palazzo", "Suit", "Lehenga"],
        "Units":    [48, 35, 62, 41, 29, 38, 22, 18, 25, 15],
    }
    df = pd.DataFrame(data).sort_values("Units")
    return df, "Units", "Category", "Units Sold", "Units Sold"
