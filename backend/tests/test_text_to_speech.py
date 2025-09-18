"""
Tests for Text-to-Speech Service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.services.text_to_speech import (
    TextToSpeechService,
    VoiceSettings,
    VoiceGender,
    AudioFormat,
    TTSResult
)

class TestTextToSpeechService:
    """Test cases for TextToSpeechService"""
    
    @pytest.fixture
    def tts_service(self):
        """Create TTS service instance for testing"""
        return TextToSpeechService()
    
    @pytest.fixture
    def sample_voice_settings(self):
        """Sample voice settings for testing"""
        return VoiceSettings(
            language_code="en-US",
            gender=VoiceGender.FEMALE,
            speaking_rate=1.0,
            pitch=0.0,
            audio_format=AudioFormat.MP3
        )
    
    def test_voice_settings_validation(self):
        """Test voice settings validation"""
        # Test valid settings
        settings = VoiceSettings(
            speaking_rate=2.0,
            pitch=10.0,
            volume_gain_db=5.0
        )
        assert settings.speaking_rate == 2.0
        assert settings.pitch == 10.0
        assert settings.volume_gain_db == 5.0
        
        # Test range clamping
        settings = VoiceSettings(
            speaking_rate=10.0,  # Should be clamped to 4.0
            pitch=-50.0,         # Should be clamped to -20.0
            volume_gain_db=100.0 # Should be clamped to 16.0
        )
        assert settings.speaking_rate == 4.0
        assert settings.pitch == -20.0
        assert settings.volume_gain_db == 16.0
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_fallback(self, tts_service, sample_voice_settings):
        """Test speech synthesis with fallback (no Google TTS)"""
        # Mock the client to be None (fallback mode)
        tts_service.client = None
        
        result = await tts_service.synthesize_speech(
            text="Hello, this is a test.",
            voice_settings=sample_voice_settings
        )
        
        assert isinstance(result, TTSResult)
        assert result.text_length == len("Hello, this is a test.")
        assert result.audio_format == AudioFormat.MP3
        assert result.duration_seconds > 0
        assert len(result.audio_data) > 0
    
    @pytest.mark.asyncio
    async def test_synthesize_educational_response(self, tts_service):
        """Test educational response synthesis"""
        result = await tts_service.synthesize_educational_response(
            text_response="Great job! You solved the equation correctly.",
            feedback_type="encouragement"
        )
        
        assert isinstance(result, TTSResult)
        assert result.text_length > 0
        assert result.voice_settings is not None
    
    @pytest.mark.asyncio
    async def test_synthesize_with_preset(self, tts_service):
        """Test synthesis with voice preset"""
        result = await tts_service.synthesize_speech(
            text="This is a test with preset.",
            preset="tutor_female"
        )
        
        assert isinstance(result, TTSResult)
        assert result.voice_settings.gender == VoiceGender.FEMALE
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, tts_service):
        """Test TTS caching functionality"""
        text = "This text should be cached."
        cache_key = "test_cache_key"
        
        # First synthesis
        result1 = await tts_service.synthesize_speech(
            text=text,
            cache_key=cache_key
        )
        
        # Second synthesis with same cache key
        result2 = await tts_service.synthesize_speech(
            text=text,
            cache_key=cache_key
        )
        
        # Should return cached result
        assert result1.audio_data == result2.audio_data
        assert cache_key in tts_service.audio_cache
    
    def test_create_audio_url(self, tts_service):
        """Test audio URL creation"""
        audio_data = b"fake_audio_data"
        audio_format = AudioFormat.MP3
        
        url = tts_service.create_audio_url(audio_data, audio_format)
        
        assert url.startswith("data:audio/mpeg;base64,")
        assert len(url) > len("data:audio/mpeg;base64,")
    
    @pytest.mark.asyncio
    async def test_validate_tts_setup(self, tts_service):
        """Test TTS setup validation"""
        validation = await tts_service.validate_tts_setup()
        
        assert isinstance(validation, dict)
        assert "is_available" in validation
        assert "client_initialized" in validation
        assert "voice_presets_loaded" in validation
        assert "supported_formats" in validation
        assert "test_synthesis" in validation
    
    def test_voice_presets_loaded(self, tts_service):
        """Test that voice presets are properly loaded"""
        assert len(tts_service.voice_presets) > 0
        assert "tutor_female" in tts_service.voice_presets
        assert "tutor_male" in tts_service.voice_presets
        assert "encouragement" in tts_service.voice_presets
        assert "correction" in tts_service.voice_presets
    
    @pytest.mark.asyncio
    async def test_error_handling(self, tts_service):
        """Test error handling in TTS synthesis"""
        # Test with empty text
        result = await tts_service.synthesize_speech(text="")
        assert isinstance(result, TTSResult)
        assert result.text_length == 0
    
    @pytest.mark.asyncio
    async def test_ssml_synthesis_fallback(self, tts_service):
        """Test SSML synthesis with fallback"""
        ssml_text = '<speak>Hello <break time="1s"/> world!</speak>'
        
        result = await tts_service.synthesize_with_ssml(ssml_text)
        
        assert isinstance(result, TTSResult)
        assert result.text_length == len(ssml_text)
    
    @pytest.mark.asyncio
    async def test_get_available_voices_fallback(self, tts_service):
        """Test getting available voices with fallback"""
        # Mock client to None for fallback
        tts_service.client = None
        
        voices = await tts_service.get_available_voices("en-US")
        
        assert isinstance(voices, list)
        assert len(voices) == 0  # Should return empty list in fallback mode
    
    def test_feedback_type_preset_mapping(self, tts_service):
        """Test that feedback types map to appropriate presets"""
        feedback_types = [
            "encouragement",
            "correction", 
            "explanation",
            "hint",
            "question",
            "validation"
        ]
        
        for feedback_type in feedback_types:
            # This would be tested in the actual synthesis method
            # Here we just verify the presets exist
            if feedback_type in ["encouragement", "validation"]:
                assert "encouragement" in tts_service.voice_presets
            elif feedback_type == "correction":
                assert "correction" in tts_service.voice_presets
            elif feedback_type == "explanation":
                assert "explanation" in tts_service.voice_presets
            else:
                assert "tutor_female" in tts_service.voice_presets

@pytest.mark.asyncio
async def test_tts_service_integration():
    """Integration test for TTS service"""
    service = TextToSpeechService()
    
    # Test basic synthesis
    result = await service.synthesize_speech(
        text="Integration test for TTS service.",
        preset="tutor_female"
    )
    
    assert isinstance(result, TTSResult)
    assert result.text_length > 0
    assert result.audio_data is not None
    
    # Test audio URL creation
    if result.audio_data:
        url = service.create_audio_url(result.audio_data, result.audio_format)
        assert url.startswith("data:")

@pytest.mark.asyncio 
async def test_educational_synthesis_integration():
    """Integration test for educational synthesis"""
    service = TextToSpeechService()
    
    test_cases = [
        ("Great work on solving that equation!", "encouragement"),
        ("Let me help you find the error in step 3.", "correction"),
        ("The quadratic formula is used when...", "explanation"),
        ("What do you think happens next?", "question")
    ]
    
    for text, feedback_type in test_cases:
        result = await service.synthesize_educational_response(
            text_response=text,
            feedback_type=feedback_type
        )
        
        assert isinstance(result, TTSResult)
        assert result.text_length == len(text)
        assert result.voice_settings is not None