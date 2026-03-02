"""
LM Studio API Client — OpenAI-compatible chat completions
Replaces llama_service.py (~500 lines) with a clean async HTTP client.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from core.settings import settings

logger = logging.getLogger(__name__)


class LMStudioService:
    def __init__(self) -> None:
        self._base_url = settings.lm_studio_url
        self._completions_url = settings.lm_studio_completions_url
        self._model = settings.ai_model
        self._default_temp = settings.ai_temperature
        self._default_timeout = settings.ai_timeout

    # ── PUBLIC API ────────────────────────────────────────

    async def send_direct_message(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
    ) -> str:
        temp = temperature if temperature is not None else self._default_temp
        tout = timeout or self._default_timeout

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=tout) as client:
            response = await client.post(
                self._completions_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code != 200:
            err = response.text[:500]
            logger.error("LM Studio API error %d: %s", response.status_code, err)
            raise RuntimeError(f"LM Studio API error {response.status_code}: {err}")

        ai_text = response.json()["choices"][0]["message"]["content"]
        return self._clean_response(ai_text)

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._base_url}/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    # ── INTERNAL ──────────────────────────────────────────

    @staticmethod
    def _clean_response(text: str) -> str:
        if not text:
            return text

        final_pattern = r"<\|channel\|>final<\|message\|>(.*?)(?:<\|end\|>|$)"
        final_match = re.search(final_pattern, text, re.DOTALL)
        if final_match:
            text = final_match.group(1)

        special_tokens = [
            r"<\|channel\|>[^<]*<\|message\|>",
            r"<\|channel\|>[^<]*",
            r"<\|message\|>",
            r"<\|end\|>",
            r"<\|start\|>",
            r"<\|assistant\|>",
            r"<\|user\|>",
            r"<\|system\|>",
        ]
        for pat in special_tokens:
            text = re.sub(pat, "", text)

        text = re.sub(r"<\|channel\|>analysis.*?<\|end\|>", "", text, flags=re.DOTALL)
        text = re.sub(r"<\|[^>]*\|>", "", text)
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        text = re.sub(r" +\n", "\n", text)
        text = re.sub(r"  +", " ", text)
        return text.strip()


lm_studio_service = LMStudioService()
