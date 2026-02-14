"""Claude API Client with Intelligent Model Selection."""

import time
from typing import Literal
from enum import Enum

import anthropic
from anthropic import Anthropic, APIError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import get_settings
from logging_config import get_logger

logger = get_logger(__name__)


class TaskComplexity(str, Enum):
    """Task complexity levels for model selection."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class ClaudeModel(str, Enum):
    """Available Claude models."""
    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-5-20250929"


class ClaudeClient:
    """Production-ready Claude API client."""
    
    def __init__(self) -> None:
        """Initialize Claude API client."""
        settings = get_settings()
        self._client = Anthropic(api_key=settings.anthropic_api_key)
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._request_count = 0
        logger.info("claude_client_initialized")
    
    def _get_model(self, complexity: TaskComplexity) -> ClaudeModel:
        """Select model based on task complexity."""
        if complexity == TaskComplexity.COMPLEX:
            return ClaudeModel.SONNET
        return ClaudeModel.HAIKU
    
    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        reraise=True
    )
    def _make_request(
        self,
        model: ClaudeModel,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> anthropic.types.Message:
        """Make API request with retry logic."""
        try:
            response = self._client.messages.create(
                model=model.value,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens
            self._request_count += 1
            
            logger.info(
                "claude_request_completed",
                model=model.value,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )
            
            return response
            
        except Exception as e:
            logger.error("claude_api_error", error=str(e))
            raise
    
    def generate(
        self,
        prompt: str,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        system: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 1.0
    ) -> str:
        """Generate text using Claude."""
        try:
            model = self._get_model(complexity)
            
            if system is None:
                settings = get_settings()
                system = f"""You are a helpful AI assistant for {settings.product_name}.

{settings.product_name}: {settings.product_tagline}
Website: {settings.product_url}

Be concise, helpful, and authentic."""
            
            response = self._make_request(
                model=model,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text
            
            return text_content.strip()
            
        except Exception as e:
            logger.error("claude_generation_failed", error=str(e))
            raise
    
    def generate_thread(
        self,
        topic: str,
        tweet_count: int = 5,
        style: Literal["controversial", "educational", "story"] = "educational"
    ) -> list[str]:
        """Generate a Twitter thread."""
        settings = get_settings()
        
        prompt = f"""Create a {tweet_count}-tweet Twitter thread about: {topic}

Style: {style}

Product: {settings.product_name} - {settings.product_tagline}

Requirements:
1. Bold hook (first tweet)
2. Each tweet ≤280 characters
3. Natural, conversational tone
4. Include examples
5. Soft CTA (last tweet)

Format: Return ONLY numbered tweets 1-{tweet_count}."""
        
        response = self.generate(
            prompt=prompt,
            complexity=TaskComplexity.COMPLEX,
            max_tokens=1500,
            temperature=0.9
        )
        
        tweets = []
        for line in response.split('\n'):
            line = line.strip()
            if line and any(line.startswith(f"{i}.") or line.startswith(f"{i})") for i in range(1, 11)):
                tweet = line.split('.', 1)[1].strip() if '.' in line else line.split(')', 1)[1].strip()
                if len(tweet) <= 280 and tweet:
                    tweets.append(tweet)
        
        return tweets[:tweet_count]
    
    def generate_reply(self, original_message: str) -> str:
        """Generate a helpful reply."""
        settings = get_settings()
        
        prompt = f"""Reply to: "{original_message}"

Product (mention only if relevant): {settings.product_name}

Requirements:
1. Be genuinely helpful
2. Max 280 characters
3. Natural tone
4. No hard selling

Return ONLY the reply."""
        
        reply = self.generate(
            prompt=prompt,
            complexity=TaskComplexity.SIMPLE,
            max_tokens=200,
            temperature=0.7
        )
        
        if len(reply) > 280:
            reply = reply[:277] + "..."
        
        return reply
    
    def get_usage_stats(self) -> dict[str, int | float]:
        """Get API usage statistics."""
        haiku_input_cost = 0.25 / 1_000_000
        haiku_output_cost = 1.25 / 1_000_000
        
        input_cost = self._total_input_tokens * haiku_input_cost
        output_cost = self._total_output_tokens * haiku_output_cost
        total_cost = input_cost + output_cost
        
        return {
            'total_requests': self._request_count,
            'total_input_tokens': self._total_input_tokens,
            'total_output_tokens': self._total_output_tokens,
            'estimated_cost_usd': round(total_cost, 4)
        }


_claude_client: ClaudeClient | None = None


def get_claude() -> ClaudeClient:
    """Get Claude API client (singleton)."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client