"""
Speech-to-Text (STT) providers and abstraction layer
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass
import asyncio
from deepgram import Deepgram
import logging

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription"""
    text: str
    confidence: float
    words: list
    is_final: bool = True
    language: Optional[str] = None
    duration: Optional[float] = None


class STTProvider(ABC):
    """Abstract base class for STT providers"""

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """
        Transcribe streaming audio in real-time

        Args:
            audio_stream: Async generator yielding audio chunks

        Yields:
            TranscriptionResult objects as they become available
        """
        pass

    @abstractmethod
    async def transcribe_file(self, audio_file_path: str) -> TranscriptionResult:
        """
        Transcribe a complete audio file

        Args:
            audio_file_path: Path to audio file

        Returns:
            TranscriptionResult with complete transcription
        """
        pass


class DeepgramSTT(STTProvider):
    """Deepgram STT implementation"""

    def __init__(self, api_key: str, model: str = "nova-2"):
        """
        Initialize Deepgram STT

        Args:
            api_key: Deepgram API key
            model: Model to use (nova-2, enhanced, base)
        """
        self.api_key = api_key
        self.model = model
        self.client = Deepgram(api_key)
        logger.info(f"Initialized Deepgram STT with model: {model}")

    async def transcribe_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """
        Transcribe streaming audio using Deepgram's live transcription

        Args:
            audio_stream: Async generator yielding audio chunks (PCM, 16kHz)

        Yields:
            TranscriptionResult objects for interim and final results
        """
        try:
            # Configure streaming options
            options = {
                "punctuate": True,
                "interim_results": True,
                "language": "en",
                "model": self.model,
                "smart_format": True,
            }

            # Create live transcription connection
            deepgram_connection = await self.client.transcription.live(options)

            # Buffer for collecting results
            result_queue = asyncio.Queue()

            def on_message(result):
                """Handle incoming transcription results"""
                try:
                    if result.get("is_final"):
                        channel = result["channel"]
                        alternative = channel["alternatives"][0]

                        transcription_result = TranscriptionResult(
                            text=alternative["transcript"],
                            confidence=alternative["confidence"],
                            words=alternative.get("words", []),
                            is_final=True,
                            duration=result.get("duration"),
                        )
                        asyncio.create_task(result_queue.put(transcription_result))
                except Exception as e:
                    logger.error(f"Error processing Deepgram message: {e}")

            # Register message handler
            deepgram_connection.registerHandler(
                deepgram_connection.event.TRANSCRIPT_RECEIVED, on_message
            )

            # Start processing audio stream
            async def send_audio():
                try:
                    async for audio_chunk in audio_stream:
                        await deepgram_connection.send(audio_chunk)
                    await deepgram_connection.finish()
                except Exception as e:
                    logger.error(f"Error sending audio to Deepgram: {e}")

            # Start sending audio in background
            audio_task = asyncio.create_task(send_audio())

            # Yield results as they arrive
            while True:
                try:
                    result = await asyncio.wait_for(result_queue.get(), timeout=0.1)
                    yield result
                except asyncio.TimeoutError:
                    if audio_task.done():
                        break
                    continue

        except Exception as e:
            logger.error(f"Error in Deepgram stream transcription: {e}")
            raise

    async def transcribe_file(self, audio_file_path: str) -> TranscriptionResult:
        """
        Transcribe a complete audio file using Deepgram

        Args:
            audio_file_path: Path to audio file

        Returns:
            TranscriptionResult with complete transcription
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                audio_data = audio_file.read()

            options = {
                "punctuate": True,
                "language": "en",
                "model": self.model,
                "smart_format": True,
            }

            response = await self.client.transcription.prerecorded(
                {"buffer": audio_data, "mimetype": "audio/wav"}, options
            )

            # Extract result
            channel = response["results"]["channels"][0]
            alternative = channel["alternatives"][0]

            return TranscriptionResult(
                text=alternative["transcript"],
                confidence=alternative["confidence"],
                words=alternative.get("words", []),
                is_final=True,
                duration=response["metadata"].get("duration"),
            )

        except Exception as e:
            logger.error(f"Error transcribing file with Deepgram: {e}")
            raise


class MockSTT(STTProvider):
    """Mock STT for testing without API calls"""

    async def transcribe_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Mock streaming transcription"""
        # Simulate processing
        async for _ in audio_stream:
            yield TranscriptionResult(
                text="This is a mock transcription",
                confidence=0.95,
                words=[],
                is_final=True,
            )
            await asyncio.sleep(0.1)

    async def transcribe_file(self, audio_file_path: str) -> TranscriptionResult:
        """Mock file transcription"""
        return TranscriptionResult(
            text="This is a mock transcription of the audio file",
            confidence=0.95,
            words=[],
            is_final=True,
            duration=10.0,
        )


def create_stt_provider(
    provider: str = "deepgram", api_key: Optional[str] = None, **kwargs
) -> STTProvider:
    """
    Factory function to create STT provider

    Args:
        provider: Provider name ('deepgram', 'mock')
        api_key: API key for the provider
        **kwargs: Additional provider-specific arguments

    Returns:
        STTProvider instance
    """
    if provider == "deepgram":
        if not api_key:
            raise ValueError("API key required for Deepgram")
        return DeepgramSTT(api_key=api_key, **kwargs)
    elif provider == "mock":
        return MockSTT()
    else:
        raise ValueError(f"Unknown STT provider: {provider}")
