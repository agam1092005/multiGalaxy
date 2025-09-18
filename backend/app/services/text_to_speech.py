"""
Text-to-Speech Service for Multi-Galaxy-Note

This service integrates Google Cloud Text-to-Speech API to generate natural speech
from AI responses, providing synchronized voice and visual explanations.
"""

import asyncio
import logging
import os
import io
import base64
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import uuid
import tempfile

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    texttospeech = None

logger = logging.getLogger(__name__)

class VoiceGender(str, Enum):
    """Voice gender options"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class VoiceSpeed(str, Enum):
    """Voice speed options"""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"

class AudioFormat(str, Enum):
    """Audio format options"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"

@dataclass
class VoiceSettings:
    """Voice configuration settings"""
    language_code: str = "en-US"
    voice_name: Optional[str] = None
    gender: VoiceGender = VoiceGender.FEMALE
    speaking_rate: float = 1.0  # 0.25 to 4.0
    pitch: float = 0.0  # -20.0 to 20.0
    volume_gain_db: float = 0.0  # -96.0 to 16.0
    audio_format: AudioFormat = AudioFormat.MP3
    
    def __post_init__(self):
        # Validate ranges
        self.speaking_rate = max(0.25, min(4.0, self.speaking_rate))
        self.pitch = max(-20.0, min(20.0, self.pitch))
        self.volume_gain_db = max(-96.0, min(16.0, self.volume_gain_db))

@dataclass
class TTSResult:
    """Result of text-to-speech conversion"""
    audio_data: bytes
    audio_format: AudioFormat
    duration_seconds: Optional[float] = None
    text_length: int = 0
    voice_settings: Optional[VoiceSettings] = None
    audio_url: Optional[str] = None  # For web playback
    
class TextToSpeechService:
    """
    Text-to-Speech service using Google Cloud Text-to-Speech API
    """
    
    def __init__(self):
        """Initialize the TTS service"""
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Initialize client if credentials are available
        self.client = None
        if GOOGLE_TTS_AVAILABLE and (self.credentials_path or self.project_id):
            try:
                self.client = texttospeech.TextToSpeechClient()
                logger.info("Google Text-to-Speech client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Google TTS client: {e}")
                self.client = None
        else:
            logger.warning("Google Text-to-Speech not available or not configured")
        
        # Default voice settings for different contexts
        self.voice_presets = {
            "tutor_female": VoiceSettings(
                language_code="en-US",
                voice_name="en-US-Journey-F",
                gender=VoiceGender.FEMALE,
                speaking_rate=0.9,
                pitch=2.0,
                volume_gain_db=0.0
            ),
            "tutor_male": VoiceSettings(
                language_code="en-US",
                voice_name="en-US-Journey-D",
                gender=VoiceGender.MALE,
                speaking_rate=0.9,
                pitch=-2.0,
                volume_gain_db=0.0
            ),
            "explanation": VoiceSettings(
                language_code="en-US",
                voice_name="en-US-Neural2-F",
                gender=VoiceGender.FEMALE,
                speaking_rate=0.8,
                pitch=1.0,
                volume_gain_db=0.0
            ),
            "encouragement": VoiceSettings(
                language_code="en-US",
                voice_name="en-US-Neural2-A",
                gender=VoiceGender.FEMALE,
                speaking_rate=1.1,
                pitch=3.0,
                volume_gain_db=2.0
            ),
            "correction": VoiceSettings(
                language_code="en-US",
                voice_name="en-US-Neural2-C",
                gender=VoiceGender.FEMALE,
                speaking_rate=0.85,
                pitch=0.0,
                volume_gain_db=0.0
            )
        }
        
        # Cache for generated audio
        self.audio_cache: Dict[str, TTSResult] = {}
        self.max_cache_size = 100
        
    async def synthesize_speech(
        self,
        text: str,
        voice_settings: Optional[VoiceSettings] = None,
        preset: Optional[str] = None,
        cache_key: Optional[str] = None
    ) -> TTSResult:
        """
        Convert text to speech using Google TTS API
        
        Args:
            text: Text to convert to speech
            voice_settings: Voice configuration settings
            preset: Predefined voice preset name
            cache_key: Optional cache key for reusing results
            
        Returns:
            TTSResult with audio data and metadata
        """
        try:
            # Check cache first
            if cache_key and cache_key in self.audio_cache:
                logger.info(f"Using cached TTS result for key: {cache_key}")
                return self.audio_cache[cache_key]
            
            # Get voice settings
            if preset and preset in self.voice_presets:
                voice_settings = self.voice_presets[preset]
            elif not voice_settings:
                voice_settings = self.voice_presets["tutor_female"]
            
            # Generate speech
            if self.client:
                result = await self._synthesize_with_google_tts(text, voice_settings)
            else:
                result = await self._synthesize_with_fallback(text, voice_settings)
            
            # Cache result if cache key provided
            if cache_key:
                await self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            # Return fallback result
            return TTSResult(
                audio_data=b"",
                audio_format=AudioFormat.MP3,
                text_length=len(text),
                voice_settings=voice_settings
            )
    
    async def _synthesize_with_google_tts(
        self,
        text: str,
        voice_settings: VoiceSettings
    ) -> TTSResult:
        """Synthesize speech using Google Cloud TTS"""
        
        # Prepare synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Configure voice
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_settings.language_code,
            name=voice_settings.voice_name,
            ssml_gender=self._get_google_gender(voice_settings.gender)
        )
        
        # Configure audio
        audio_config = texttospeech.AudioConfig(
            audio_encoding=self._get_google_encoding(voice_settings.audio_format),
            speaking_rate=voice_settings.speaking_rate,
            pitch=voice_settings.pitch,
            volume_gain_db=voice_settings.volume_gain_db
        )
        
        # Perform synthesis
        response = await asyncio.to_thread(
            self.client.synthesize_speech,
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Calculate approximate duration (rough estimate)
        words = len(text.split())
        wpm = 150 * voice_settings.speaking_rate  # Approximate words per minute
        duration = (words / wpm) * 60 if wpm > 0 else 0
        
        return TTSResult(
            audio_data=response.audio_content,
            audio_format=voice_settings.audio_format,
            duration_seconds=duration,
            text_length=len(text),
            voice_settings=voice_settings
        )
    
    async def _synthesize_with_fallback(
        self,
        text: str,
        voice_settings: VoiceSettings
    ) -> TTSResult:
        """Fallback synthesis for testing or when Google TTS is unavailable"""
        
        logger.warning("Using fallback TTS synthesis (no actual audio generated)")
        
        # Generate mock audio data for testing
        mock_audio = b"MOCK_AUDIO_DATA_" + text.encode('utf-8')[:100]
        
        # Calculate mock duration
        words = len(text.split())
        wpm = 150 * voice_settings.speaking_rate
        duration = (words / wpm) * 60 if wpm > 0 else 0
        
        return TTSResult(
            audio_data=mock_audio,
            audio_format=voice_settings.audio_format,
            duration_seconds=duration,
            text_length=len(text),
            voice_settings=voice_settings
        )
    
    def _get_google_gender(self, gender: VoiceGender):
        """Convert VoiceGender to Google TTS gender"""
        if not GOOGLE_TTS_AVAILABLE or not texttospeech:
            return None
            
        gender_map = {
            VoiceGender.MALE: texttospeech.SsmlVoiceGender.MALE,
            VoiceGender.FEMALE: texttospeech.SsmlVoiceGender.FEMALE,
            VoiceGender.NEUTRAL: texttospeech.SsmlVoiceGender.NEUTRAL
        }
        return gender_map.get(gender, texttospeech.SsmlVoiceGender.FEMALE)
    
    def _get_google_encoding(self, audio_format: AudioFormat):
        """Convert AudioFormat to Google TTS encoding"""
        if not GOOGLE_TTS_AVAILABLE or not texttospeech:
            return None
            
        encoding_map = {
            AudioFormat.MP3: texttospeech.AudioEncoding.MP3,
            AudioFormat.WAV: texttospeech.AudioEncoding.LINEAR16,
            AudioFormat.OGG: texttospeech.AudioEncoding.OGG_OPUS
        }
        return encoding_map.get(audio_format, texttospeech.AudioEncoding.MP3)
    
    async def _cache_result(self, cache_key: str, result: TTSResult):
        """Cache TTS result with size management"""
        
        # Remove oldest entries if cache is full
        if len(self.audio_cache) >= self.max_cache_size:
            # Remove first entry (oldest)
            oldest_key = next(iter(self.audio_cache))
            del self.audio_cache[oldest_key]
        
        self.audio_cache[cache_key] = result
        logger.debug(f"Cached TTS result for key: {cache_key}")
    
    async def synthesize_educational_response(
        self,
        text_response: str,
        feedback_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TTSResult:
        """
        Synthesize speech for educational AI responses with appropriate voice settings
        
        Args:
            text_response: AI response text to synthesize
            feedback_type: Type of feedback (encouragement, correction, etc.)
            context: Additional context for voice selection
            
        Returns:
            TTSResult with synthesized audio
        """
        
        # Select appropriate voice preset based on feedback type
        preset_map = {
            "encouragement": "encouragement",
            "correction": "correction",
            "explanation": "explanation",
            "hint": "tutor_female",
            "question": "tutor_female",
            "validation": "encouragement"
        }
        
        preset = preset_map.get(feedback_type, "tutor_female")
        
        # Generate cache key
        cache_key = f"edu_{feedback_type}_{hash(text_response)}"
        
        return await self.synthesize_speech(
            text=text_response,
            preset=preset,
            cache_key=cache_key
        )
    
    async def synthesize_with_ssml(
        self,
        ssml_text: str,
        voice_settings: Optional[VoiceSettings] = None
    ) -> TTSResult:
        """
        Synthesize speech using SSML (Speech Synthesis Markup Language)
        
        Args:
            ssml_text: SSML formatted text
            voice_settings: Voice configuration
            
        Returns:
            TTSResult with synthesized audio
        """
        
        if not self.client:
            logger.warning("SSML synthesis requires Google TTS client")
            return await self._synthesize_with_fallback(ssml_text, voice_settings or VoiceSettings())
        
        try:
            voice_settings = voice_settings or self.voice_presets["tutor_female"]
            
            # Prepare SSML input
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
            
            # Configure voice and audio
            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_settings.language_code,
                name=voice_settings.voice_name,
                ssml_gender=self._get_google_gender(voice_settings.gender)
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=self._get_google_encoding(voice_settings.audio_format),
                speaking_rate=voice_settings.speaking_rate,
                pitch=voice_settings.pitch,
                volume_gain_db=voice_settings.volume_gain_db
            )
            
            # Perform synthesis
            response = await asyncio.to_thread(
                self.client.synthesize_speech,
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return TTSResult(
                audio_data=response.audio_content,
                audio_format=voice_settings.audio_format,
                text_length=len(ssml_text),
                voice_settings=voice_settings
            )
            
        except Exception as e:
            logger.error(f"Error synthesizing SSML: {e}")
            return await self._synthesize_with_fallback(ssml_text, voice_settings)
    
    async def get_available_voices(self, language_code: str = "en-US") -> List[Dict[str, Any]]:
        """
        Get list of available voices for a language
        
        Args:
            language_code: Language code (e.g., "en-US")
            
        Returns:
            List of available voice information
        """
        
        if not self.client:
            logger.warning("Voice listing requires Google TTS client")
            return []
        
        try:
            # List available voices
            voices = await asyncio.to_thread(self.client.list_voices)
            
            # Filter by language and format response
            available_voices = []
            for voice in voices.voices:
                if language_code in voice.language_codes:
                    available_voices.append({
                        "name": voice.name,
                        "language_codes": list(voice.language_codes),
                        "gender": voice.ssml_gender.name,
                        "natural_sample_rate": voice.natural_sample_rate_hertz
                    })
            
            return available_voices
            
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []
    
    def create_audio_url(self, audio_data: bytes, audio_format: AudioFormat) -> str:
        """
        Create a data URL for audio playback in web browsers
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format
            
        Returns:
            Data URL string for web playback
        """
        
        mime_types = {
            AudioFormat.MP3: "audio/mpeg",
            AudioFormat.WAV: "audio/wav",
            AudioFormat.OGG: "audio/ogg"
        }
        
        mime_type = mime_types.get(audio_format, "audio/mpeg")
        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
        
        return f"data:{mime_type};base64,{encoded_audio}"
    
    async def validate_tts_setup(self) -> Dict[str, Any]:
        """
        Validate TTS service setup and configuration
        
        Returns:
            Dictionary with validation results
        """
        
        validation_result = {
            "is_available": GOOGLE_TTS_AVAILABLE,
            "client_initialized": self.client is not None,
            "credentials_configured": bool(self.credentials_path or self.project_id),
            "voice_presets_loaded": len(self.voice_presets) > 0,
            "cache_enabled": True,
            "supported_formats": [fmt.value for fmt in AudioFormat],
            "test_synthesis": False
        }
        
        # Test synthesis if client is available
        if self.client:
            try:
                test_result = await self.synthesize_speech("Test synthesis", preset="tutor_female")
                validation_result["test_synthesis"] = len(test_result.audio_data) > 0
            except Exception as e:
                logger.error(f"TTS test synthesis failed: {e}")
                validation_result["test_synthesis"] = False
        
        return validation_result

# Global TTS service instance
text_to_speech_service = TextToSpeechService()