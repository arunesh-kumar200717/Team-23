"""
dashboard/login.py

Streamlit login + signup page for the Market Intelligence Bot.
"""
from __future__ import annotations

import streamlit as st

from database import db


def render_login() -> None:
    """Render the full login / signup UI."""

    # ── Page chrome ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <style>
        .login-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }
        .brand-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(90deg, #e94560, #f5a623);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
        }
        .brand-sub {
            color: #a0aec0;
            text-align: center;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 1.6, 1])
    with col_center:
        st.markdown('<p class="brand-title">🧵 Market Intelligence Bot</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="brand-sub">Multi-Agent AI for Clothing Industry</p>',
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up"])

        # ── LOGIN ─────────────────────────────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input(
                    "Password", type="password", placeholder="Enter your password"
                )
                submitted = st.form_submit_button(
                    "Login →", use_container_width=True, type="primary"
                )

            if submitted:
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    user = db.verify_user(username, password)
                    if user:
                        st.session_state.logged_in       = True
                        st.session_state.user_id         = user["id"]
                        st.session_state.username        = user["username"]
                        st.session_state.user_data       = dict(user)
                        st.session_state.current_page    = "Competitor Alerts"
                        st.session_state.last_run_report = None
                        st.success(f"Welcome back, {user['business_name']}! 🎉")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        # ── SIGN UP ───────────────────────────────────────────────────────────
        with tab_signup:
            with st.form("signup_form"):
                new_username  = st.text_input("Choose Username *")
                new_password  = st.text_input("Password *", type="password",
                                              help="Minimum 8 characters")
                confirm_pass  = st.text_input("Confirm Password *", type="password")
                st.markdown("---")
                business_name = st.text_input("Business Name *",
                                              placeholder="e.g. Sri Murugan Textiles")
                city          = st.text_input("City *",
                                              placeholder="e.g. Coimbatore")
                shop_type     = st.selectbox(
                    "Shop Type *",
                    ["Retail Store", "Wholesale", "Online Store",
                     "Multi-Channel (Online + Offline)"],
                )
                clothing_cat  = st.selectbox(
                    "Primary Clothing Category *",
                    ["Ethnic Wear", "Western Wear", "Casual Wear",
                     "Kids Wear", "Sports / Athleisure", "All Categories"],
                )
                price_range   = st.selectbox(
                    "Average Price Range *",
                    ["Budget (₹200 – ₹699)", "Mid Range (₹700 – ₹1999)",
                     "Premium (₹2000 – ₹4999)", "Luxury (₹5000+)"],
                )
                reg_submit = st.form_submit_button(
                    "Create Account →", use_container_width=True, type="primary"
                )

            if reg_submit:
                errors = _validate_signup(
                    new_username, new_password, confirm_pass,
                    business_name, city
                )
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    ok, msg = db.create_user(
                        username        = new_username,
                        password        = new_password,
                        business_name   = business_name,
                        city            = city,
                        shop_type       = shop_type,
                        clothing_category = clothing_cat,
                        avg_price_range = price_range,
                    )
                    if ok:
                        st.success(msg + " You can now log in.")
                    else:
                        st.error(msg)


# ─────────────────────────────  HELPERS  ─────────────────────────────────────

def _validate_signup(
    username: str,
    password: str,
    confirm: str,
    business: str,
    city: str,
) -> list[str]:
    errors: list[str] = []
    if not username:
        errors.append("Username is required.")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    if not business:
        errors.append("Business name is required.")
    if not city:
        errors.append("City is required.")
    return errors
