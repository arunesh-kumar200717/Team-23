"""
notifications/whatsapp_alert.py

Sends WhatsApp messages via the Twilio Sandbox API.

Setup (one-time)
----------------
1. Create a Twilio account at https://www.twilio.com
2. Enable the WhatsApp Sandbox (Messaging → Try it Out → Send a WhatsApp Message)
3. Your phone must join the sandbox first by sending the join phrase.
4. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_TO in .env

The module is intentionally non-fatal: if Twilio is not configured or the
send fails, it logs the error and returns False so the rest of the app
continues to function normally.
"""
from __future__ import annotations

import logging
from typing import Optional

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    TWILIO_WHATSAPP_TO,
)

logger = logging.getLogger(__name__)


class WhatsAppAlert:
    """Thin wrapper around the Twilio WhatsApp Messages API."""

    def __init__(
        self,
        to_number: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> None:
        self._to   = to_number   or TWILIO_WHATSAPP_TO
        self._from = from_number or TWILIO_WHATSAPP_FROM

    # ──────────────────────────  PUBLIC API  ─────────────────────────────────

    def send(self, body: str) -> bool:
        """
        Send a WhatsApp message. Returns True on success, False otherwise.
        """
        if not self._is_configured():
            logger.warning(
                "WhatsApp alert skipped – Twilio credentials not set in .env"
            )
            return False

        try:
            from twilio.rest import Client  # lazy import

            client  = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body   = body,
                from_  = self._from,
                to     = self._to,
            )
            logger.info("WhatsApp message sent: SID=%s", message.sid)
            return True
        except Exception as exc:
            logger.error("WhatsApp send failed: %s", exc)
            return False

    def send_competitor_alert(
        self,
        competitor_name: str,
        update_type: str,      # "new_launch" | "price_drop" | "campaign"
        product_name: str = "",
        product_price: float = 0,
        strategy_tip: str = "",
        instagram_caption: str = "",
    ) -> bool:
        """
        Compose and send a structured competitor-alert WhatsApp message.

        Example output
        --------------
        🚨 Competitor Alert!

        Brand: XYZ Clothing
        New Launch: Denim Jacket
        Price: ₹1299

        Suggested Strategy:
        Launch a similar product with 10% discount.

        Suggested Instagram Caption:
        "Upgrade your style with our new denim collection 🔥"
        """
        type_emoji = {
            "new_launch": "🚀",
            "price_drop": "💸",
            "campaign":   "📢",
        }.get(update_type, "⚠️")

        type_label = {
            "new_launch": "New Launch",
            "price_drop": "Price Drop",
            "campaign":   "New Campaign",
        }.get(update_type, "Update")

        lines = [
            f"🚨 *Competitor Alert!*",
            "",
            f"*Brand:* {competitor_name}",
            f"*{type_label}:* {product_name}" if product_name else "",
            f"*Price:* ₹{product_price:,.0f}" if product_price else "",
            "",
        ]

        if strategy_tip:
            lines += ["*Suggested Strategy:*", strategy_tip, ""]

        if instagram_caption:
            lines += ['*Suggested Instagram Caption:*', f'"{instagram_caption}"', ""]

        body = "\n".join(l for l in lines if l is not None)
        return self.send(body.strip())

    def send_strategy_report(
        self, business_name: str, highlights: list[str]
    ) -> bool:
        """Send a summary of the latest AI strategy to WhatsApp."""
        bullet_lines = "\n".join(f"• {h}" for h in highlights[:5])
        body = (
            f"📊 *{business_name} – Daily Strategy Report*\n\n"
            f"{bullet_lines}\n\n"
            f"_Open the Market Intelligence Dashboard for full details._"
        )
        return self.send(body)

    # ──────────────────────────  HELPERS  ────────────────────────────────────

    def _is_configured(self) -> bool:
        return bool(
            TWILIO_ACCOUNT_SID
            and TWILIO_AUTH_TOKEN
            and self._to
            and "XXXXXXXXXX" not in self._to   # placeholder guard
        )
