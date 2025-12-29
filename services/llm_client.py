"""
Unified LLM Client - Support for multiple LLM providers
#1 = gemini-3-flash (stable)
#2 = gemini-2.5-pro (stable)
#3 = Groq oss-120b (stable)
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal
from enum import Enum

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("LLMClient")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not found in .env")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not found in .env")


class ModelProvider(str, Enum):
    """Available LLM providers"""
    GEMINI_3_FLASH = "gemini-2.5-flash"   # #1 (fallback to 2.5 flash - faster, within quota)
    GEMINI_2_5_PRO = "gemini-2.5-pro"     # #2
    GROQ_OSS_120B = "groq-oss-120b"       # #3


@dataclass
class LLMResponse:
    """Unified response format across providers"""
    content: str
    model: str
    provider: ModelProvider
    raw: Dict[str, Any]


class GeminiClient:
    """Google Gemini API client wrapper"""
    
    def __init__(self, model: str = "gemini-2.5-pro"):
        from google import genai
        from google.genai import types
        
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in .env")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = model
        self.types = types
        self.config = types.GenerateContentConfig(
            temperature=1.0,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="text/plain"
        )
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> LLMResponse:
        """Generate content using Gemini API"""
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
        
        return LLMResponse(
            content=response.text,
            model=self.model,
            provider=ModelProvider.GEMINI_3_FLASH if "3-flash" in self.model else ModelProvider.GEMINI_2_5_PRO,
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
    """Unified interface for multiple LLM providers"""
    
    def __init__(self, provider: ModelProvider = ModelProvider.GROQ_OSS_120B):
        self.provider = provider
        
        if provider == ModelProvider.GEMINI_3_FLASH:
            self.client = GeminiClient(model=provider.value)  # Use the actual provider value (gemini-2.5-flash)
        elif provider == ModelProvider.GEMINI_2_5_PRO:
            self.client = GeminiClient(model=provider.value)
        elif provider == ModelProvider.GROQ_OSS_120B:
            self.client = GroqClient(model="openai/gpt-oss-120b")
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> LLMResponse:
        """Generate content using the selected provider"""
        return self.client.generate(prompt, max_tokens, temperature)
    
    @staticmethod
    def get_provider_by_number(number: int) -> ModelProvider:
        """Get provider by number: 1=Gemini 3-flash, 2=Gemini 2.5-pro, 3=Groq"""
        if number == 1:
            return ModelProvider.GEMINI_3_FLASH
        elif number == 2:
            return ModelProvider.GEMINI_2_5_PRO
        elif number == 3:
            return ModelProvider.GROQ_OSS_120B
        else:
            raise ValueError(f"Invalid provider number: {number}. Use 1, 2, or 3.")


# Default clients for lazy initialization
_gemini_3_flash = None
_gemini_2_5_pro = None
_groq_client = None
_default_client = None

def get_gemini_3_flash():
    global _gemini_3_flash
    if _gemini_3_flash is None:
        _gemini_3_flash = GeminiClient(model="gemini-3-flash")
    return _gemini_3_flash

def get_gemini_2_5_pro():
    global _gemini_2_5_pro
    if _gemini_2_5_pro is None:
        _gemini_2_5_pro = GeminiClient(model="gemini-2.5-pro")
    return _gemini_2_5_pro

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient(model="openai/gpt-oss-120b")
    return _groq_client

def get_default_client():
    global _default_client
    if _default_client is None:
        _default_client = UnifiedLLMClient(provider=ModelProvider.GROQ_OSS_120B)
    return _default_client

# Backward compatibility aliases
gemini_3_flash = get_gemini_3_flash
gemini_2_5_pro = get_gemini_2_5_pro
groq_client = get_groq_client
default_client = get_default_client
