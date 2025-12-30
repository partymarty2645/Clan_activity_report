"""
Unified LLM Client - Support for multiple LLM providers
#1 = gemini-2.5-flash-lite (production - higher rate limits for agents/free tier)
#2 = gemini-2.5-flash (fallback - standard tier)
#3 = Groq oss-120b (fallback - always available)

RATE LIMITING: 
- Gemini Flash Lite = ~15 RPM
- Gemini Flash/Pro = ~2 RPM
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal
from enum import Enum

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("LLMClient")

# ===== RATE LIMITING =====
class RateLimiter:
    """Enforces minimum delay between API calls for rate limit compliance"""
    def __init__(self, min_interval_seconds: float = 4.0):
        self.min_interval = min_interval_seconds
        self.last_call_time = 0.0
    
    def wait_if_needed(self):
        """Block until enough time has passed since last call"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.info(f"⏳ Rate limit: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        self.last_call_time = time.time()

# Rate limiters
_flash_lite_limiter = RateLimiter(min_interval_seconds=4.0) # ~15 RPM
_standard_limiter = RateLimiter(min_interval_seconds=30.0) # 2 RPM

# ===== END RATE LIMITING =====

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not found in .env")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in .env")


class ModelProvider(str, Enum):
    """Available LLM providers"""
    GEMINI_FLASH_LITE = "gemini-2.5-flash-lite" # #1 Primary (High RPM)
    GEMINI_FLASH = "gemini-2.5-flash"           # #2 Secondary (Low RPM)
    GROQ_OSS_120B = "groq-oss-120b"             # #3 Fallback


@dataclass
class LLMResponse:
    """Unified response format across providers"""
    content: str
    model: str
    provider: ModelProvider
    raw: Dict[str, Any]


class GeminiClient:
    """Google Gemini API client wrapper"""
    
    def __init__(self, model: str):
        try:
            from google import genai  # type: ignore
            from google.genai import types  # type: ignore
        except ImportError as e:
            raise ImportError(f"google-genai library not installed. Install with: pip install google-genai\nError: {e}")
        
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in .env")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = model
        self.types = types
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> LLMResponse:
        """Generate content using Gemini API"""
        # Enforce appropriate rate limit
        if "lite" in self.model:
            _flash_lite_limiter.wait_if_needed()
        else:
            _standard_limiter.wait_if_needed()
        
        config = self.types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="text/plain"
        )
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        
        # Determine provider enum
        provider = ModelProvider.GEMINI_FLASH_LITE if "lite" in self.model else ModelProvider.GEMINI_FLASH

        return LLMResponse(
            content=response.text,
            model=self.model,
            provider=provider,
            raw={"text": response.text}
        )


class GroqClient:
    """Groq OpenAI-compatible API client wrapper"""
    
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in .env")
        self.api_key = GROQ_API_KEY
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        self.timeout = 60
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> LLMResponse:
        """Generate content using Groq API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "top_p": 0.95,
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        
        if response.status_code == 429:
            raise RuntimeError("Groq rate limit exceeded (429)")
        
        response.raise_for_status()
        resp_data = response.json()
        
        content = ""
        if "choices" in resp_data and len(resp_data["choices"]) > 0:
            choice = resp_data["choices"][0]
            if isinstance(choice.get("message"), dict):
                content = choice["message"].get("content", "")
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=ModelProvider.GROQ_OSS_120B,
            raw=resp_data
        )


class UnifiedLLMClient:
    """Unified interface for multiple LLM providers with fallback logic"""
    
    def __init__(self, provider: Optional[ModelProvider] = None):
        # Default to highest priority if not specified
        self.current_provider = provider or ModelProvider.GEMINI_FLASH_LITE
        self.client = self._get_client(self.current_provider)
        
    def _get_client(self, provider: ModelProvider):
        try:
            if provider == ModelProvider.GEMINI_FLASH_LITE:
                return GeminiClient(model=provider.value)
            elif provider == ModelProvider.GEMINI_FLASH:
                return GeminiClient(model=provider.value)
            elif provider == ModelProvider.GROQ_OSS_120B:
                return GroqClient(model="openai/gpt-oss-120b")
            else:
                return GroqClient(model="openai/gpt-oss-120b")
        except Exception as e:
            logger.error(f"Failed to initialize {provider}: {e}")
            return None # Handle in generate

    def generate(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> LLMResponse:
        """Generate content with automatic fallback"""
        
        # Priority Order: 
        # 1. Gemini Flash Lite
        # 2. Gemini Flash
        # 3. Groq OSS 120b
        
        providers = [
            ModelProvider.GEMINI_FLASH_LITE,
            ModelProvider.GEMINI_FLASH,
            ModelProvider.GROQ_OSS_120B
        ]
        
        errors = []
        
        for provider in providers:
            try:
                # Attempt to use this provider
                logger.info(f"Attempting generation with {provider.value}...")
                client = self._get_client(provider)
                if not client:
                    continue
                    
                response = client.generate(prompt, max_tokens, temperature)
                logger.info(f"✅ Success with {provider.value}")
                return response
                
            except Exception as e:
                error_msg = f"{provider.value} failed: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
        
        # If all fail
        raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")

    @staticmethod
    def get_provider_by_number(number: int) -> ModelProvider:
        """Get provider by number: 1=Flash Lite, 2=Flash, 3=Groq"""
        if number == 1:
            return ModelProvider.GEMINI_FLASH_LITE
        elif number == 2:
            return ModelProvider.GEMINI_FLASH
        elif number == 3:
            return ModelProvider.GROQ_OSS_120B
        else:
            raise ValueError(f"Invalid provider number: {number}. Use 1, 2, or 3.")


def get_default_client():
    return UnifiedLLMClient()

# Backward compatibility aliases
default_client = get_default_client
