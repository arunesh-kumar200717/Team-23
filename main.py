"""
main.py – Streamlit entry point for Market Intelligence Bot.

Run with:
    streamlit run main.py
"""
import logging

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title  = "Market Intelligence Bot",
    page_icon   = "🧵",
    layout      = "wide",
    initial_sidebar_state = "expanded",
    menu_items  = {
        "Get Help":    None,
        "Report a bug": None,
        "About":        "Multi-Agent Market Intelligence Bot – Clothing Industry",
    },
)

# ── Bootstrap: DB init ────────────────────────────────────────────────────────
from database.db import initialize_database
initialize_database()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt= "%H:%M:%S",
)

# ── Route: login vs dashboard ─────────────────────────────────────────────────
if not st.session_state.get("logged_in", False):
    from dashboard.login import render_login
    render_login()
else:
    from dashboard.dashboard import render_dashboard
    render_dashboard()
