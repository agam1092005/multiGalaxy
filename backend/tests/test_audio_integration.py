"""
Integration tests for audio processing functionality
"""
import pytest
import asyncio
import numpy as np
from app.services.audio_processor import AudioProcessor

class TestAudioIntegration:
    
    @pytest.mark.asyncio
    async def test_audio_processor_basic_functionality(self):
        """Test basic audio processor functionality without external dependencies"""
        processor = AudioProcessor()
        
        # Test initialization
        assert processor.sample_rate == 16000
        assert processor.vad is not None
        
        # Test quality assessment with synthetic data
        audio_array = np.random.randint(-1000, 1000, 1600, dtype=np.int16)
        quality = processor._assess_audio_quality(audio_array)
        
        assert 'volume_db' in quality
        assert 'quality_score' in quality
        assert isinstance(quality['is_acceptable'], (bool, np.bool_))
        
        # Test VAD with synthetic data
        audio_bytes = audio_array.tobytes()
        # Pad to correct size for VAD
        chunk_size = processor.chunk_size * 2
        if len(audio_bytes) < chunk_size:
            audio_bytes += b'\x00' * (chunk_size - len(audio_bytes))
        else:
            audio_bytes = audio_bytes[:chunk_size]
            
        vad_result = processor._detect_voice_activity(audio_bytes)
        assert 'has_speech' in vad_result
        assert 'activity_level' in vad_result
        
    @pytest.mark.asyncio
    async def test_audio_validation(self):
        """Test audio setup validation"""
        processor = AudioProcessor()
        
        validation = await processor.validate_audio_setup()
        
        assert 'speech_client' in validation
        assert 'vad_available' in validation
        assert 'is_ready' in validation
        assert isinstance(validation['errors'], list)
        
    def test_quality_score_calculation(self):
        """Test quality score calculation with known values"""
        processor = AudioProcessor()
        
        # Test with good quality parameters
        good_score = processor._calculate_quality_score(-15, 20, 0.0)
        assert 0.5 <= good_score <= 1.0
        
        # Test with poor quality parameters
        poor_score = processor._calculate_quality_score(-50, 5, 0.5)
        assert 0.0 <= poor_score <= 0.5
        
    def test_activity_level_detection(self):
        """Test voice activity level detection"""
        processor = AudioProcessor()
        
        # Test different energy levels
        silent = processor._get_activity_level(0, False)
        assert silent == 'silent'
        
        low = processor._get_activity_level(50000, True)
        assert low == 'low'
        
        medium = processor._get_activity_level(500000, True)
        assert medium == 'medium'
        
        high = processor._get_activity_level(2000000, True)
        assert high == 'high'