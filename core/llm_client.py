"""
LLM Client Wrapper
Wraps OpenRouter API for Claude access
"""

import logging
from typing import List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for OpenRouter API (Claude via OpenAI SDK)"""

    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4.5"):
        """
        Initialize LLM client

        Args:
            api_key: OpenRouter API key
            model: Model identifier
        """
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = model
        logger.info(f"LLM Client initialized with model: {model}")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.8,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate chat completion

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Generated text content

        Raises:
            Exception: If API call fails
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content.strip()
            return content

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise
