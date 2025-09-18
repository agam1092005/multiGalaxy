"""
Mock WebRTC VAD for testing when webrtcvad is not available
"""

class Vad:
    """Mock VAD class for testing"""
    
    def __init__(self, aggressiveness=2):
        self.aggressiveness = aggressiveness
    
    def is_speech(self, audio_data: bytes, sample_rate: int) -> bool:
        """Mock speech detection - returns True if audio has non-zero data"""
        # Simple heuristic: if there's significant audio data, consider it speech
        if len(audio_data) == 0:
            return False
        
        # Convert bytes to check for non-zero content
        audio_sum = sum(audio_data)
        return audio_sum > len(audio_data) * 10  # Arbitrary threshold