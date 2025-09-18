"""
Tests for audio processing service
"""
import pytest
import asyncio
import numpy as np
import base64
from unittest.mock import Mock, patch, AsyncMock
from app.services.audio_processor import AudioProcessor, AudioProcessingError, AudioQuality, VoiceActivityLevel

class TestAudioProcessor:
    
    @pytest.fixture
    def audio_processor(self):
        """Create audio processor instance for testing"""
        with patch('app.services.audio_processor.speech.SpeechClient'):
            processor = AudioProcessor()
            return processor
    
    @pytest.fixture
    def sample_audio_data(self):
        """Generate sample audio data for testing"""
        # Generate 16kHz, 16-bit PCM audio (100ms)
        sample_rate = 16000
        duration = 0.1  # 100ms
        samples = int(sample_rate * duration)
        
        # Generate sine wave at 440Hz (A note) with moderate amplitude
        t = np.linspace(0, duration, samples, False)
        audio_signal = np.sin(2 * np.pi * 440 * t) * 0.3  # Reduce amplitude to avoid clipping
        
        # Convert to 16-bit PCM
        audio_int16 = (audio_signal * 32767).astype(np.int16)
        return audio_int16.tobytes()
    
    @pytest.fixture
    def silent_audio_data(self):
        """Generate silent audio data for testing"""
        samples = int(16000 * 0.1)  # 100ms of silence
        audio_int16 = np.zeros(samples, dtype=np.int16)
        return audio_int16.tobytes()
    
    @pytest.fixture
    def noisy_audio_data(self):
        """Generate noisy audio data for testing"""
        samples = int(16000 * 0.1)  # 100ms
        # Generate random noise
        noise = np.random.normal(0, 0.1, samples)
        audio_int16 = (noise * 32767).astype(np.int16)
        return audio_int16.tobytes()
    
    def test_audio_processor_initialization(self, audio_processor):
        """Test audio processor initialization"""
        assert audio_processor.sample_rate == 16000
        assert audio_processor.chunk_duration_ms == 30
        assert audio_processor.vad is not None
        assert audio_processor.audio_buffer == []
    
    @pytest.mark.asyncio
    async def test_process_audio_chunk_with_speech(self, audio_processor, sample_audio_data):
        """Test processing audio chunk with speech content"""
        session_id = "test_session"
        user_id = "test_user"
        
        # Mock VAD to return speech detected
        with patch.object(audio_processor, '_detect_voice_activity') as mock_vad:
            mock_vad.return_value = {
                'has_speech': True,
                'activity_level': VoiceActivityLevel.MEDIUM,
                'energy': 1000.0,
                'confidence': 0.8
            }
            
            result = await audio_processor.process_audio_chunk(
                sample_audio_data, session_id, user_id
            )
            
            assert result['status'] == 'processed'
            assert result['voice_activity']['has_speech'] is True
            assert result['quality']['is_acceptable'] is True
            assert len(audio_processor.audio_buffer) == 1
    
    @pytest.mark.asyncio
    async def test_process_audio_chunk_silent(self, audio_processor, silent_audio_data):
        """Test processing silent audio chunk"""
        session_id = "test_session"
        user_id = "test_user"
        
        # Add some data to buffer first
        audio_processor.audio_buffer.append({
            'data': b'test_data',
            'timestamp': None,
            'quality': {},
            'session_id': session_id,
            'user_id': user_id
        })
        
        with patch.object(audio_processor, '_process_speech_segment') as mock_process:
            mock_process.return_value = {
                'transcript': 'test transcription',
                'confidence': 0.9
            }
            
            result = await audio_processor.process_audio_chunk(
                silent_audio_data, session_id, user_id
            )
            
            assert result['status'] == 'processed'
            assert result['voice_activity']['has_speech'] is False
            assert result['transcription'] is not None
            mock_process.assert_called_once()
    
    def test_assess_audio_quality_good(self, audio_processor, sample_audio_data):
        """Test audio quality assessment with good quality audio"""
        audio_array = np.frombuffer(sample_audio_data, dtype=np.int16)
        
        quality = audio_processor._assess_audio_quality(audio_array)
        
        assert 'volume_db' in quality
        assert 'snr_db' in quality
        assert 'clipping_ratio' in quality
        assert 'quality_score' in quality
        assert 'quality_level' in quality
        assert 'is_acceptable' in quality
        
        # Good quality audio should have acceptable metrics
        assert quality['clipping_ratio'] < 0.1
        assert quality['quality_score'] > 0.0
    
    def test_assess_audio_quality_poor(self, audio_processor, silent_audio_data):
        """Test audio quality assessment with poor quality audio"""
        audio_array = np.frombuffer(silent_audio_data, dtype=np.int16)
        
        quality = audio_processor._assess_audio_quality(audio_array)
        
        # Silent audio should have poor quality metrics
        assert quality['volume_db'] < -40
        assert quality['quality_level'] == AudioQuality.POOR
        assert quality['is_acceptable'] is False
    
    def test_detect_voice_activity_with_speech(self, audio_processor, sample_audio_data):
        """Test voice activity detection with speech"""
        # Ensure correct chunk size for VAD
        chunk_size = audio_processor.chunk_size * 2  # 2 bytes per sample
        if len(sample_audio_data) != chunk_size:
            sample_audio_data = sample_audio_data[:chunk_size]
            if len(sample_audio_data) < chunk_size:
                sample_audio_data += b'\x00' * (chunk_size - len(sample_audio_data))
        
        result = audio_processor._detect_voice_activity(sample_audio_data)
        
        assert 'has_speech' in result
        assert 'activity_level' in result
        assert 'energy' in result
        assert 'confidence' in result
        
        # Should detect some activity in the audio signal
        assert result['energy'] > 0
    
    def test_detect_voice_activity_silent(self, audio_processor, silent_audio_data):
        """Test voice activity detection with silence"""
        # Ensure correct chunk size for VAD
        chunk_size = audio_processor.chunk_size * 2
        if len(silent_audio_data) != chunk_size:
            silent_audio_data = silent_audio_data[:chunk_size]
            if len(silent_audio_data) < chunk_size:
                silent_audio_data += b'\x00' * (chunk_size - len(silent_audio_data))
        
        result = audio_processor._detect_voice_activity(silent_audio_data)
        
        assert result['has_speech'] is False
        assert result['activity_level'] == VoiceActivityLevel.SILENT
        assert result['energy'] == 0.0
    
    def test_calculate_quality_score(self, audio_processor):
        """Test quality score calculation"""
        # Test excellent quality
        score = audio_processor._calculate_quality_score(-15, 25, 0.0)
        assert score > 0.8
        
        # Test poor quality
        score = audio_processor._calculate_quality_score(-50, 5, 0.5)
        assert score < 0.4
    
    def test_get_quality_level(self, audio_processor):
        """Test quality level determination"""
        assert audio_processor._get_quality_level(0.9) == AudioQuality.EXCELLENT
        assert audio_processor._get_quality_level(0.7) == AudioQuality.GOOD
        assert audio_processor._get_quality_level(0.5) == AudioQuality.FAIR
        assert audio_processor._get_quality_level(0.3) == AudioQuality.POOR
    
    def test_get_activity_level(self, audio_processor):
        """Test activity level determination"""
        # Test silent
        level = audio_processor._get_activity_level(0, False)
        assert level == VoiceActivityLevel.SILENT
        
        # Test low activity
        level = audio_processor._get_activity_level(50000, True)
        assert level == VoiceActivityLevel.LOW
        
        # Test medium activity
        level = audio_processor._get_activity_level(500000, True)
        assert level == VoiceActivityLevel.MEDIUM
        
        # Test high activity
        level = audio_processor._get_activity_level(2000000, True)
        assert level == VoiceActivityLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_process_speech_segment_success(self, audio_processor):
        """Test successful speech segment processing"""
        # Mock Google Speech client
        mock_response = Mock()
        mock_result = Mock()
        mock_alternative = Mock()
        mock_alternative.transcript = "Hello world"
        mock_alternative.confidence = 0.95
        mock_alternative.words = []
        mock_result.alternatives = [mock_alternative]
        mock_response.results = [mock_result]
        
        audio_processor.speech_client = Mock()
        audio_processor.speech_client.recognize = Mock(return_value=mock_response)
        
        # Add test data to buffer
        audio_processor.audio_buffer = [{
            'data': b'test_audio_data' * 1000,  # Make it long enough
            'timestamp': None,
            'quality': {},
            'session_id': 'test',
            'user_id': 'test'
        }]
        
        result = await audio_processor._process_speech_segment()
        
        assert result is not None
        assert result['transcript'] == "Hello world"
        assert result['confidence'] == 0.95
        assert len(audio_processor.audio_buffer) == 0  # Buffer should be cleared
    
    @pytest.mark.asyncio
    async def test_process_speech_segment_no_client(self, audio_processor):
        """Test speech segment processing without client"""
        audio_processor.speech_client = None
        audio_processor.audio_buffer = [{'data': b'test'}]
        
        result = await audio_processor._process_speech_segment()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_speech_segment_too_short(self, audio_processor):
        """Test speech segment processing with too short audio"""
        audio_processor.speech_client = Mock()
        audio_processor.audio_buffer = [{
            'data': b'short',  # Too short
            'timestamp': None,
            'quality': {},
            'session_id': 'test',
            'user_id': 'test'
        }]
        
        result = await audio_processor._process_speech_segment()
        assert result is None
        assert len(audio_processor.audio_buffer) == 0  # Buffer should be cleared
    
    @pytest.mark.asyncio
    async def test_process_audio_chunk_empty_data(self, audio_processor):
        """Test processing empty audio data"""
        with pytest.raises(AudioProcessingError, match="Empty audio data received"):
            await audio_processor.process_audio_chunk(b'', 'session', 'user')
    
    @pytest.mark.asyncio
    async def test_validate_audio_setup_success(self, audio_processor):
        """Test successful audio setup validation"""
        audio_processor.speech_client = Mock()
        
        result = await audio_processor.validate_audio_setup()
        
        assert result['speech_client'] is True
        assert result['vad_available'] is True
        assert result['is_ready'] is True
        assert len(result['errors']) == 0
    
    @pytest.mark.asyncio
    async def test_validate_audio_setup_no_client(self, audio_processor):
        """Test audio setup validation without speech client"""
        audio_processor.speech_client = None
        
        result = await audio_processor.validate_audio_setup()
        
        assert result['speech_client'] is False
        assert result['is_ready'] is False
        assert len(result['errors']) > 0
    
    def test_process_transcription_response_empty(self, audio_processor):
        """Test processing empty transcription response"""
        mock_response = Mock()
        mock_response.results = []
        
        result = audio_processor._process_transcription_response(mock_response)
        
        assert result['transcript'] == ''
        assert result['confidence'] == 0.0
        assert result['words'] == []
        assert result['alternatives'] == []
    
    def test_process_transcription_response_with_words(self, audio_processor):
        """Test processing transcription response with word-level data"""
        # Mock word info
        mock_word = Mock()
        mock_word.word = "hello"
        mock_word.confidence = 0.9
        mock_word.start_time.total_seconds.return_value = 0.0
        mock_word.end_time.total_seconds.return_value = 0.5
        
        # Mock alternative
        mock_alternative = Mock()
        mock_alternative.transcript = "hello world"
        mock_alternative.confidence = 0.95
        mock_alternative.words = [mock_word]
        
        # Mock result
        mock_result = Mock()
        mock_result.alternatives = [mock_alternative]
        
        # Mock response
        mock_response = Mock()
        mock_response.results = [mock_result]
        
        result = audio_processor._process_transcription_response(mock_response)
        
        assert result['transcript'] == "hello world"
        assert result['confidence'] == 0.95
        assert len(result['words']) == 1
        assert result['words'][0]['word'] == "hello"
        assert result['words'][0]['confidence'] == 0.9