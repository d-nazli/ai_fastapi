"""
Webhook service — async POST to portal-meet-backend
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import httpx

from core.settings import settings

logger = logging.getLogger(__name__)


async def send_webhook(data: Dict[str, Any]) -> None:
    """
    Sends webhook payload to portal-meet-backend.
    Runs as a fire-and-forget background task.
    """
    url = settings.webhook_url
    api_key = settings.webhook_api_key

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }

    try:
        logger.info("[WEBHOOK] Sending to %s for userId=%s", url, data.get("userId"))
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=data, headers=headers)

        if response.status_code == 200:
            logger.info("[WEBHOOK] Success — status %d", response.status_code)
        else:
            logger.warning(
                "[WEBHOOK] Failed — status %d, body: %s",
                response.status_code,
                response.text[:300],
            )
    except httpx.TimeoutException:
        logger.error("[WEBHOOK] Timeout — %s", url)
    except httpx.ConnectError:
        logger.error("[WEBHOOK] Connection refused — %s (service may be down)", url)
    except Exception as exc:
        logger.exception("[WEBHOOK] Unexpected error: %s", exc)


def fire_and_forget_webhook(data: Dict[str, Any]) -> None:
    """Schedules the webhook coroutine as a background task on the running event loop."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_webhook(data))
    except RuntimeError:
        logger.warning("[WEBHOOK] No running event loop — skipping webhook")
