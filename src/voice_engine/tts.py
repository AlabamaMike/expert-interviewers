"""
Text-to-Speech (TTS) providers and abstraction layer
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging
from elevenlabs import generate, Voice, VoiceSettings

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    """Result of text-to-speech conversion"""
    audio_data: bytes
    format: str = "mp3"
    sample_rate: int = 44100
    duration: Optional[float] = None


class TTSProvider(ABC):
    """Abstract base class for TTS providers"""

    @abstractmethod
    async def synthesize(
        self, text: str, voice_settings: Optional[Dict[str, Any]] = None
    ) -> AudioResult:
        """
        Convert text to speech

        Args:
            text: Text to convert to speech
            voice_settings: Optional voice configuration

        Returns:
            AudioResult with synthesized audio
        """
        pass

    @abstractmethod
    async def synthesize_streaming(
        self, text: str, voice_settings: Optional[Dict[str, Any]] = None
    ):
        """
        Stream text-to-speech conversion for low latency

        Args:
            text: Text to convert to speech
            voice_settings: Optional voice configuration

        Yields:
            Audio chunks as they become available
        """
        pass


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs TTS implementation"""

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model: str = "eleven_monolingual_v1",
    ):
        """
        Initialize ElevenLabs TTS

        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use
            model: Model to use
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        logger.info(f"Initialized ElevenLabs TTS with voice: {voice_id}")

    async def synthesize(
        self, text: str, voice_settings: Optional[Dict[str, Any]] = None
    ) -> AudioResult:
        """
        Synthesize speech using ElevenLabs

        Args:
            text: Text to synthesize
            voice_settings: Optional settings (stability, similarity_boost)

        Returns:
            AudioResult with synthesized audio
        """
        try:
            # Default voice settings
            settings = VoiceSettings(
                stability=voice_settings.get("stability", 0.5)
                if voice_settings
                else 0.5,
                similarity_boost=voice_settings.get("similarity_boost", 0.75)
                if voice_settings
                else 0.75,
            )

            # Generate audio
            audio_data = generate(
                text=text,
                voice=Voice(voice_id=self.voice_id, settings=settings),
                model=self.model,
                api_key=self.api_key,
            )

            return AudioResult(
                audio_data=audio_data,
                format="mp3",
                sample_rate=44100,
            )

        except Exception as e:
            logger.error(f"Error synthesizing speech with ElevenLabs: {e}")
            raise

    async def synthesize_streaming(
        self, text: str, voice_settings: Optional[Dict[str, Any]] = None
    ):
        """
        Stream synthesized speech for low latency

        Args:
            text: Text to synthesize
            voice_settings: Optional voice settings

        Yields:
            Audio chunks as they're generated
        """
        try:
            # Note: ElevenLabs streaming requires different approach
            # For now, we'll chunk the audio after generation
            result = await self.synthesize(text, voice_settings)

            # Yield in chunks (simulate streaming)
            chunk_size = 4096
            audio_bytes = result.audio_data
            for i in range(0, len(audio_bytes), chunk_size):
                yield audio_bytes[i : i + chunk_size]

        except Exception as e:
            logger.error(f"Error in ElevenLabs streaming synthesis: {e}")
            raise


class MockTTS(TTSProvider):
    """Mock TTS for testing without API calls"""

    async def synthesize(
        self, text: str, voice_settings: Optional[Dict[str, Any]] = None
    ) -> AudioResult:
        """Mock synthesis"""
        # Generate mock audio data
        mock_audio = b"MOCK_AUDIO_DATA_" + text.encode()
        return AudioResult(
            audio_data=mock_audio,
            format="mp3",
            sample_rate=44100,
            duration=len(text) * 0.1,  # Rough estimate
        )

    async def synthesize_streaming(
        self, text: str, voice_settings: Optional[Dict[str, Any]] = None
    ):
        """Mock streaming synthesis"""
        result = await self.synthesize(text, voice_settings)
        chunk_size = 1024
        for i in range(0, len(result.audio_data), chunk_size):
            yield result.audio_data[i : i + chunk_size]


def create_tts_provider(
    provider: str = "elevenlabs",
    api_key: Optional[str] = None,
    voice_id: Optional[str] = None,
    **kwargs,
) -> TTSProvider:
    """
    Factory function to create TTS provider

    Args:
        provider: Provider name ('elevenlabs', 'mock')
        api_key: API key for the provider
        voice_id: Voice ID to use
        **kwargs: Additional provider-specific arguments

    Returns:
        TTSProvider instance
    """
    if provider == "elevenlabs":
        if not api_key or not voice_id:
            raise ValueError("API key and voice_id required for ElevenLabs")
        return ElevenLabsTTS(api_key=api_key, voice_id=voice_id, **kwargs)
    elif provider == "mock":
        return MockTTS()
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")
