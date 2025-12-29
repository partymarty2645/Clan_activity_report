import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("GroqClient")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TIMEOUT_SECONDS = int(os.getenv("GROQ_TIMEOUT_SECONDS", "60"))

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}


class RateLimitError(Exception):
    """Raised when Groq returns HTTP 429."""


@dataclass
class GroqResponse:
    raw: Dict[str, Any]

    @property
    def output_text(self) -> str:
        if "choices" in self.raw and len(self.raw["choices"]) > 0:
            choice = self.raw["choices"][0]
            if isinstance(choice.get("message"), dict):
                return choice["message"].get("content", "")
        return ""


class GroqClient:
    """Simple wrapper for Groq OpenAI-compatible responses endpoint."""

    def create_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 1.0,
        top_p: float = 0.95,
    ) -> GroqResponse:
        payload = {
            "model": model or DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "top_p": top_p,
        }

        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=HEADERS,
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )

        if response.status_code == 429:
            logger.error("Groq returned 429 rate limit")
            raise RateLimitError(response.text)

        response.raise_for_status()
        return GroqResponse(response.json())


client = GroqClient()
