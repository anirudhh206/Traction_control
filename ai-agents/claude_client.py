"""
AI Client — Google Gemini API Wrapper.

Works with both old (google.generativeai) and new (google.genai) packages.
Automatically detects which one is installed.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
import warnings

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import get_settings
from logging_config import get_logger

__all__ = ["GeminiClient", "TaskComplexity", "get_claude"]

logger = get_logger(__name__)

# Try to import the new package first, fall back to old
try:
    from google import genai
    from google.genai import types
    USE_NEW_API = True
    logger.info("using_new_gemini_api", package="google.genai")
except ImportError:
    try:
        import google.generativeai as genai
        USE_NEW_API = False
        # Suppress the deprecation warning
        warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')
        logger.info("using_old_gemini_api", package="google.generativeai")
    except ImportError:
        raise ImportError(
            "Neither google.genai nor google.generativeai found. "
            "Install with: pip install google-generativeai"
        )


class TaskComplexity(str, Enum):
    """Task complexity levels for appropriate model selection."""
    
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class GeminiClient:
    """
    Type-safe client for Google Gemini API.
    
    Automatically selects models based on task complexity:
    - Simple/Medium → Gemini 1.5 Flash (fast, free)
    - Complex → Gemini 1.5 Pro (powerful)
    """
    
    _MODEL_MAP = {
        TaskComplexity.SIMPLE: "gemini-1.5-flash",
        TaskComplexity.MEDIUM: "gemini-1.5-flash",
        TaskComplexity.COMPLEX: "gemini-1.5-pro",
    }
    
    def __init__(self) -> None:
        """Initialize Gemini client."""
        settings = get_settings()
        
        # Support both gemini_api_key and anthropic_api_key
        api_key = (
            getattr(settings, 'gemini_api_key', None) or 
            getattr(settings, 'anthropic_api_key', None)
        )
        
        if not api_key:
            raise ValueError(
                "API key not found. Add to .env:\n"
                "GEMINI_API_KEY=your-key-here"
            )
        
        self.api_key = api_key
        
        # Initialize based on which package is available
        if USE_NEW_API:
            self.client = genai.Client(api_key=api_key)
        else:
            genai.configure(api_key=api_key)
            self.client = None  # Old API doesn't use client object
        
        logger.info("gemini_client_initialized", use_new_api=USE_NEW_API)
    
    @retry(
        retry=retry_if_exception_type((Exception,)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate AI response using Gemini."""
        try:
            model_name = self._MODEL_MAP[complexity]
            
            # Build full prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            if USE_NEW_API:
                # New API (google.genai)
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens or 1024,
                )
                
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=config,
                )
                
                text = response.text
            else:
                # Old API (google.generativeai)
                model = genai.GenerativeModel(model_name)
                
                generation_config = {
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 40,
                }
                
                if max_tokens:
                    generation_config["max_output_tokens"] = max_tokens
                
                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                )
                
                text = response.text
            
            if not text:
                raise ValueError("Empty response from Gemini")
            
            logger.info(
                "gemini_generation_success",
                model=model_name,
                response_length=len(text),
            )
            
            return text.strip()
        
        except Exception as e:
            logger.error(
                "gemini_generation_failed",
                error=str(e),
                model=self._MODEL_MAP.get(complexity, "unknown"),
            )
            raise
    
    def generate_simple(self, prompt: str, max_tokens: int = 200) -> str:
        """Quick, short responses."""
        return self.generate(
            prompt=prompt,
            complexity=TaskComplexity.SIMPLE,
            max_tokens=max_tokens,
            temperature=0.6,
        )
    
    def generate_creative(self, prompt: str, max_tokens: int = 500) -> str:
        """Creative content with higher temperature."""
        return self.generate(
            prompt=prompt,
            complexity=TaskComplexity.MEDIUM,
            max_tokens=max_tokens,
            temperature=0.9,
        )
    
    def __repr__(self) -> str:
        api_type = "new" if USE_NEW_API else "old"
        return f"<GeminiClient api={api_type}>"


# Backward compatibility
ClaudeClient = GeminiClient

# Global singleton
_client: Optional[GeminiClient] = None


def get_claude() -> GeminiClient:
    """
    Get the global Gemini client instance (singleton).
    Named get_claude() for backward compatibility with existing code.
    """
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client