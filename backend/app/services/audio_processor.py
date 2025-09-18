"""
Audio processing service for speech-to-text conversion and audio quality validation
"""
import asyncio
import base64
import io
import logging
import numpy as np
try:
    import webrtcvad
except ImportError:
    from .mock_webrtcvad import Vad as webrtcvad
    webrtcvad.Vad = webrtcvad
from typing import Optional, Dict, Any, List, Tuple
try:
    from google.cloud import speech
    from google.cloud.speech import RecognitionConfig, RecognitionAudio
except ImportError:
    # Mock classes for testing when Google Cloud Speech is not available
    class MockSpeechClient:
        def recognize(self, config, audio):
            class MockResponse:
                results = []
            return MockResponse()
    
    class MockRecognitionConfig:
        AudioEncoding = type('AudioEncoding', (), {'LINEAR16': 'LINEAR16'})
        def __init__(self, **kwargs):
            pass
    
    class MockRecognitionAudio:
        def __init__(self, **kwargs):
            pass
    
    speech = type('speech', (), {'SpeechClient': MockSpeechClient})
    RecognitionConfig = MockRecognitionConfig
    RecognitionAudio = MockRecognitionAudio
import os
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class AudioQuality(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

class VoiceActivityLevel(str, Enum):
    SILENT = "silent"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""
    pass

class AudioProcessor:
    """
    Handles audio capture, processing, and speech-to-text conversion
    """
    
    def __init__(self):
        # Initialize Google Speech-to-Text client
        try:
            self.speech_client = speech.SpeechClient()
        except Exception as e:
            logger.error(f"Failed to initialize Google Speech client: {e}")
            self.speech_client = None
        
        # Voice Activity Detection
        self.vad = webrtcvad.Vad(2)  # Aggressiveness level 2 (0-3)
        
        # Audio configuration
        self.sample_rate = 16000  # 16kHz for optimal speech recognition
        self.chunk_duration_ms = 30  # 30ms chunks for VAD
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)
        
        # Quality thresholds
        self.min_volume_threshold = 0.01
        self.max_noise_ratio = 0.3
        self.min_speech_duration = 0.5  # seconds
        
        # Buffer for continuous processing
        self.audio_buffer = []
        self.speech_segments = []
        
    async def process_audio_chunk(
        self, 
        audio_data: bytes, 
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process incoming audio chunk for voice activity detection and quality assessment
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM, 16kHz)
            session_id: Learning session identifier
            user_id: User identifier
            
        Returns:
            Dictionary containing processing results
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Validate audio format
            if len(audio_array) == 0:
                raise AudioProcessingError("Empty audio data received")
            
            # Assess audio quality
            quality_metrics = self._assess_audio_quality(audio_array)
            
            # Voice Activity Detection
            vad_result = self._detect_voice_activity(audio_data)
            
            # Add to buffer if speech is detected
            if vad_result['has_speech']:
                self.audio_buffer.append({
                    'data': audio_data,
                    'timestamp': datetime.utcnow(),
                    'quality': quality_metrics,
                    'session_id': session_id,
                    'user_id': user_id
                })
            
            # Process accumulated speech if silence detected after speech
            transcription_result = None
            if not vad_result['has_speech'] and len(self.audio_buffer) > 0:
                transcription_result = await self._process_speech_segment()
            
            return {
                'status': 'processed',
                'quality': quality_metrics,
                'voice_activity': vad_result,
                'transcription': transcription_result,
                'buffer_size': len(self.audio_buffer),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            raise AudioProcessingError(f"Audio processing failed: {str(e)}")
    
    def _assess_audio_quality(self, audio_array: np.ndarray) -> Dict[str, Any]:
        """
        Assess the quality of audio data
        
        Args:
            audio_array: Audio data as numpy array
            
        Returns:
            Dictionary containing quality metrics
        """
        try:
            # Calculate volume (RMS)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            volume_db = 20 * np.log10(max(rms, 1e-10))
            
            # Calculate signal-to-noise ratio estimate
            # Use spectral analysis for noise estimation
            fft = np.fft.fft(audio_array)
            magnitude = np.abs(fft)
            
            # Estimate noise floor (bottom 10% of frequency bins)
            sorted_magnitude = np.sort(magnitude)
            noise_floor = np.mean(sorted_magnitude[:len(sorted_magnitude)//10])
            signal_power = np.mean(sorted_magnitude[-len(sorted_magnitude)//10:])
            
            snr = 10 * np.log10(max(signal_power / max(noise_floor, 1e-10), 1e-10))
            
            # Detect clipping
            max_value = np.max(np.abs(audio_array))
            clipping_ratio = np.sum(np.abs(audio_array) > 0.95 * 32767) / len(audio_array)
            
            # Overall quality assessment
            quality_score = self._calculate_quality_score(volume_db, snr, clipping_ratio)
            
            return {
                'volume_db': float(volume_db),
                'snr_db': float(snr),
                'clipping_ratio': float(clipping_ratio),
                'quality_score': quality_score,
                'quality_level': self._get_quality_level(quality_score),
                'is_acceptable': quality_score > 0.5
            }
            
        except Exception as e:
            logger.error(f"Error assessing audio quality: {e}")
            return {
                'volume_db': -60.0,
                'snr_db': 0.0,
                'clipping_ratio': 0.0,
                'quality_score': 0.0,
                'quality_level': AudioQuality.POOR,
                'is_acceptable': False
            }
    
    def _calculate_quality_score(self, volume_db: float, snr_db: float, clipping_ratio: float) -> float:
        """Calculate overall quality score (0-1)"""
        # Volume score (optimal range: -20 to -10 dB)
        if -25 <= volume_db <= -5:
            volume_score = 1.0
        elif volume_db < -40 or volume_db > 0:
            volume_score = 0.0
        else:
            volume_score = max(0, 1 - abs(volume_db + 15) / 25)
        
        # SNR score (higher is better, 20dB+ is excellent)
        snr_score = min(1.0, max(0.0, (snr_db - 5) / 20))
        
        # Clipping penalty
        clipping_score = max(0.0, 1.0 - clipping_ratio * 10)
        
        # Weighted average
        return (volume_score * 0.4 + snr_score * 0.4 + clipping_score * 0.2)
    
    def _get_quality_level(self, quality_score: float) -> AudioQuality:
        """Convert quality score to quality level"""
        if quality_score >= 0.8:
            return AudioQuality.EXCELLENT
        elif quality_score >= 0.6:
            return AudioQuality.GOOD
        elif quality_score >= 0.4:
            return AudioQuality.FAIR
        else:
            return AudioQuality.POOR
    
    def _detect_voice_activity(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Detect voice activity in audio chunk
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Dictionary containing VAD results
        """
        try:
            # WebRTC VAD requires specific chunk sizes
            if len(audio_data) != self.chunk_size * 2:  # 2 bytes per sample
                # Pad or truncate to correct size
                if len(audio_data) < self.chunk_size * 2:
                    audio_data = audio_data + b'\x00' * (self.chunk_size * 2 - len(audio_data))
                else:
                    audio_data = audio_data[:self.chunk_size * 2]
            
            # Run VAD
            has_speech = self.vad.is_speech(audio_data, self.sample_rate)
            
            # Calculate activity level
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            energy = np.sum(audio_array.astype(np.float32) ** 2) / len(audio_array)
            
            activity_level = self._get_activity_level(energy, has_speech)
            
            return {
                'has_speech': has_speech,
                'activity_level': activity_level,
                'energy': float(energy),
                'confidence': 0.8 if has_speech else 0.2  # VAD confidence estimate
            }
            
        except Exception as e:
            logger.error(f"Error in voice activity detection: {e}")
            return {
                'has_speech': False,
                'activity_level': VoiceActivityLevel.SILENT,
                'energy': 0.0,
                'confidence': 0.0
            }
    
    def _get_activity_level(self, energy: float, has_speech: bool) -> VoiceActivityLevel:
        """Determine voice activity level based on energy and VAD result"""
        if not has_speech:
            return VoiceActivityLevel.SILENT
        
        if energy > 1000000:
            return VoiceActivityLevel.HIGH
        elif energy > 100000:
            return VoiceActivityLevel.MEDIUM
        else:
            return VoiceActivityLevel.LOW
    
    async def _process_speech_segment(self) -> Optional[Dict[str, Any]]:
        """
        Process accumulated speech segment for transcription
        
        Returns:
            Transcription result or None if processing fails
        """
        if not self.audio_buffer or not self.speech_client:
            return None
        
        try:
            # Combine audio chunks
            combined_audio = b''.join([chunk['data'] for chunk in self.audio_buffer])
            
            # Check minimum duration
            duration_seconds = len(combined_audio) / (self.sample_rate * 2)
            if duration_seconds < self.min_speech_duration:
                self.audio_buffer.clear()
                return None
            
            # Prepare for Google Speech-to-Text
            audio = RecognitionAudio(content=combined_audio)
            config = RecognitionConfig(
                encoding=RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_confidence=True,
                enable_word_time_offsets=True,
                model="latest_long"  # Best for educational content
            )
            
            # Perform transcription
            response = self.speech_client.recognize(config=config, audio=audio)
            
            # Process results
            transcription_result = self._process_transcription_response(response)
            
            # Clear buffer after processing
            self.audio_buffer.clear()
            
            return transcription_result
            
        except Exception as e:
            logger.error(f"Error processing speech segment: {e}")
            self.audio_buffer.clear()
            return {
                'error': str(e),
                'transcript': '',
                'confidence': 0.0,
                'words': []
            }
    
    def _process_transcription_response(self, response) -> Dict[str, Any]:
        """
        Process Google Speech-to-Text response
        
        Args:
            response: Google Speech-to-Text response
            
        Returns:
            Processed transcription result
        """
        if not response.results:
            return {
                'transcript': '',
                'confidence': 0.0,
                'words': [],
                'alternatives': []
            }
        
        # Get best result
        result = response.results[0]
        alternative = result.alternatives[0]
        
        # Extract word-level information
        words = []
        if hasattr(alternative, 'words'):
            for word_info in alternative.words:
                words.append({
                    'word': word_info.word,
                    'confidence': word_info.confidence,
                    'start_time': word_info.start_time.total_seconds(),
                    'end_time': word_info.end_time.total_seconds()
                })
        
        # Get alternative transcriptions
        alternatives = []
        for alt in result.alternatives[1:3]:  # Top 3 alternatives
            alternatives.append({
                'transcript': alt.transcript,
                'confidence': alt.confidence
            })
        
        return {
            'transcript': alternative.transcript,
            'confidence': alternative.confidence,
            'words': words,
            'alternatives': alternatives,
            'language_code': 'en-US'
        }
    
    async def validate_audio_setup(self) -> Dict[str, Any]:
        """
        Validate audio processing setup and dependencies
        
        Returns:
            Validation results
        """
        validation_results = {
            'speech_client': self.speech_client is not None,
            'vad_available': True,
            'sample_rate': self.sample_rate,
            'chunk_size': self.chunk_size,
            'errors': []
        }
        
        # Test Google Speech client
        if not self.speech_client:
            validation_results['errors'].append(
                "Google Speech-to-Text client not initialized. Check credentials."
            )
        
        # Test VAD
        try:
            test_audio = b'\x00' * (self.chunk_size * 2)
            self.vad.is_speech(test_audio, self.sample_rate)
        except Exception as e:
            validation_results['vad_available'] = False
            validation_results['errors'].append(f"VAD test failed: {e}")
        
        validation_results['is_ready'] = (
            validation_results['speech_client'] and 
            validation_results['vad_available'] and 
            len(validation_results['errors']) == 0
        )
        
        return validation_results

# Global audio processor instance
audio_processor = AudioProcessor()