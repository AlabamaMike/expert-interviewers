"""
LLM provider abstraction for response analysis and generation
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from anthropic import Anthropic, AsyncAnthropic

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    model: str
    tokens_used: int
    finish_reason: str
    metadata: Dict[str, Any]


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a response from the LLM

        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a schema

        Args:
            prompt: User prompt
            output_schema: JSON schema for output structure
            system_prompt: System prompt
            **kwargs: Additional arguments

        Returns:
            Parsed structured output
        """
        pass


class ClaudeProvider(LLMProvider):
    """Anthropic Claude LLM provider"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        default_max_tokens: int = 4096,
    ):
        """
        Initialize Claude provider

        Args:
            api_key: Anthropic API key
            model: Model to use
            default_max_tokens: Default maximum tokens
        """
        self.api_key = api_key
        self.model = model
        self.default_max_tokens = default_max_tokens
        self.client = AsyncAnthropic(api_key=api_key)
        logger.info(f"Initialized Claude provider with model: {model}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate response using Claude

        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Temperature (0-1)
            max_tokens: Max tokens to generate
            **kwargs: Additional arguments

        Returns:
            LLMResponse with generated content
        """
        try:
            max_tokens = max_tokens or self.default_max_tokens

            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=messages,
                **kwargs,
            )

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason,
                metadata={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )

        except Exception as e:
            logger.error(f"Error generating with Claude: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate structured output using Claude

        Args:
            prompt: User prompt
            output_schema: JSON schema for output
            system_prompt: System prompt
            **kwargs: Additional arguments

        Returns:
            Parsed JSON output
        """
        import json

        # Enhance prompt with schema
        enhanced_prompt = f"""{prompt}

Please respond with a valid JSON object matching this schema:
{json.dumps(output_schema, indent=2)}

Respond with ONLY the JSON object, no additional text."""

        response = await self.generate(
            prompt=enhanced_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for structured output
            **kwargs,
        )

        try:
            # Parse JSON from response
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            logger.error(f"Response content: {response.content}")
            raise


class MockLLMProvider(LLMProvider):
    """Mock LLM for testing"""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> LLMResponse:
        """Mock generation"""
        return LLMResponse(
            content="This is a mock LLM response to: " + prompt[:50],
            model="mock-model",
            tokens_used=100,
            finish_reason="stop",
            metadata={},
        )

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Mock structured generation"""
        return {"mock": "structured_output", "prompt": prompt[:30]}


def create_llm_provider(
    provider: str = "claude",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """
    Factory function to create LLM provider

    Args:
        provider: Provider name ('claude', 'mock')
        api_key: API key for the provider
        model: Model to use
        **kwargs: Additional provider-specific arguments

    Returns:
        LLMProvider instance
    """
    if provider == "claude":
        if not api_key:
            raise ValueError("API key required for Claude")
        return ClaudeProvider(api_key=api_key, model=model or "claude-3-sonnet-20240229", **kwargs)
    elif provider == "mock":
        return MockLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
