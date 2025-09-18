/**
 * Audio capture component with WebSocket integration
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAudioCapture } from '../../hooks/useAudioCapture';
import { AudioChunkData, AudioQualityMetrics } from '../../services/audioCapture';
import { Socket } from 'socket.io-client';

interface AudioCaptureProps {
  socket: Socket | null;
  sessionId: string | null;
  isEnabled: boolean;
  onTranscription?: (transcription: string) => void;
  onError?: (error: string) => void;
}

interface TranscriptionResult {
  transcript: string;
  confidence: number;
  words: Array<{
    word: string;
    confidence: number;
    start_time: number;
    end_time: number;
  }>;
}

const AudioCapture: React.FC<AudioCaptureProps> = ({
  socket,
  sessionId,
  isEnabled,
  onTranscription,
  onError
}) => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [transcription, setTranscription] = useState<string>('');
  const [qualitySuggestion, setQualitySuggestion] = useState<string>('');
  
  // Audio capture hook
  const [audioState, audioControls] = useAudioCapture({
    config: {
      sampleRate: 16000,
      channels: 1,
      chunkDuration: 100,
      enableVAD: true
    },
    onAudioChunk: handleAudioChunk,
    onQualityUpdate: handleQualityUpdate,
    onError: handleAudioError,
    autoInitialize: true
  });
  
  // Handle audio chunk from capture service
  function handleAudioChunk(chunk: AudioChunkData) {
    if (socket && sessionId && isStreaming) {
      socket.emit('audio_chunk', {
        chunk_id: chunk.chunk_id,
        audio_data: chunk.audio_data,
        timestamp: chunk.timestamp,
        duration: chunk.duration
      });
    }
  }
  
  // Handle quality updates
  function handleQualityUpdate(quality: AudioQualityMetrics) {
    // Update UI based on quality metrics
    if (!quality.is_acceptable) {
      let suggestion = 'Audio quality needs improvement: ';
      if (quality.volume_db < -30) {
        suggestion += 'Please speak louder. ';
      }
      if (quality.volume_db > -5) {
        suggestion += 'Please speak softer. ';
      }
      if (quality.clipping_ratio > 0.1) {
        suggestion += 'Reduce microphone volume. ';
      }
      setQualitySuggestion(suggestion);
    } else {
      setQualitySuggestion('');
    }
  }
  
  // Handle audio errors
  function handleAudioError(error: Error) {
    console.error('Audio capture error:', error);
    if (onError) {
      onError(error.message);
    }
    setIsStreaming(false);
  }
  
  // Start audio streaming
  const startStreaming = useCallback(async () => {
    if (!socket || !sessionId || !audioState.isInitialized) {
      if (onError) {
        onError('Cannot start audio: missing socket, session, or audio not initialized');
      }
      return;
    }
    
    try {
      // Start audio stream on server
      socket.emit('start_audio_stream', {
        session_id: sessionId,
        sample_rate: 16000,
        channels: 1
      });
      
      // Start local audio capture
      await audioControls.startRecording();
      setIsStreaming(true);
      
    } catch (error) {
      console.error('Failed to start audio streaming:', error);
      if (onError) {
        onError(error instanceof Error ? error.message : 'Failed to start audio streaming');
      }
    }
  }, [socket, sessionId, audioState.isInitialized, audioControls, onError]);
  
  // Stop audio streaming
  const stopStreaming = useCallback(() => {
    if (socket && sessionId) {
      socket.emit('stop_audio_stream', {
        session_id: sessionId
      });
    }
    
    audioControls.stopRecording();
    setIsStreaming(false);
    setTranscription('');
    setQualitySuggestion('');
  }, [socket, sessionId, audioControls]);
  
  // Toggle streaming
  const toggleStreaming = useCallback(() => {
    if (isStreaming) {
      stopStreaming();
    } else {
      startStreaming();
    }
  }, [isStreaming, startStreaming, stopStreaming]);
  
  // Set up WebSocket event listeners
  useEffect(() => {
    if (!socket) return;
    
    const handleAudioStreamStarted = (data: any) => {
      console.log('Audio stream started:', data);
    };
    
    const handleAudioStreamStopped = (data: any) => {
      console.log('Audio stream stopped:', data);
      setIsStreaming(false);
    };
    
    const handleAudioChunkProcessed = (data: any) => {
      // Handle chunk processing acknowledgment
      console.log('Audio chunk processed:', data);
    };
    
    const handleAudioTranscription = (data: { transcription: TranscriptionResult }) => {
      const { transcription: result } = data;
      setTranscription(result.transcript);
      
      if (onTranscription) {
        onTranscription(result.transcript);
      }
    };
    
    const handleAudioQualityUpdate = (data: { quality: AudioQualityMetrics; suggestion: string }) => {
      setQualitySuggestion(data.suggestion);
    };
    
    const handleError = (data: { error: string }) => {
      console.error('WebSocket audio error:', data.error);
      if (onError) {
        onError(data.error);
      }
      setIsStreaming(false);
    };
    
    // Register event listeners
    socket.on('audio_stream_started', handleAudioStreamStarted);
    socket.on('audio_stream_stopped', handleAudioStreamStopped);
    socket.on('audio_chunk_processed', handleAudioChunkProcessed);
    socket.on('audio_transcription', handleAudioTranscription);
    socket.on('audio_quality_update', handleAudioQualityUpdate);
    socket.on('error', handleError);
    
    // Cleanup listeners
    return () => {
      socket.off('audio_stream_started', handleAudioStreamStarted);
      socket.off('audio_stream_stopped', handleAudioStreamStopped);
      socket.off('audio_chunk_processed', handleAudioChunkProcessed);
      socket.off('audio_transcription', handleAudioTranscription);
      socket.off('audio_quality_update', handleAudioQualityUpdate);
      socket.off('error', handleError);
    };
  }, [socket, onTranscription, onError]);
  
  // Auto-stop when disabled
  useEffect(() => {
    if (!isEnabled && isStreaming) {
      stopStreaming();
    }
  }, [isEnabled, isStreaming, stopStreaming]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isStreaming) {
        stopStreaming();
      }
    };
  }, [isStreaming, stopStreaming]);
  
  // Get quality indicator color
  const getQualityColor = () => {
    if (!audioState.quality) return 'bg-gray-300';
    
    switch (audioState.quality.quality_level) {
      case 'excellent': return 'bg-green-500';
      case 'good': return 'bg-green-400';
      case 'fair': return 'bg-yellow-400';
      case 'poor': return 'bg-red-500';
      default: return 'bg-gray-300';
    }
  };
  
  // Get input level bar width
  const getInputLevelWidth = () => {
    return `${Math.min(100, audioState.inputLevel * 100)}%`;
  };
  
  if (!audioState.isSupported) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800 text-sm">
          Audio capture is not supported in this browser. Please use a modern browser with WebRTC support.
        </p>
      </div>
    );
  }
  
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Audio Capture</h3>
        
        {/* Audio quality indicator */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">Quality:</span>
          <div className={`w-3 h-3 rounded-full ${getQualityColor()}`} />
          {audioState.quality && (
            <span className="text-sm text-gray-600 capitalize">
              {audioState.quality.quality_level}
            </span>
          )}
        </div>
      </div>
      
      {/* Error display */}
      {audioState.error && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-red-800 text-sm">{audioState.error}</p>
        </div>
      )}
      
      {/* Quality suggestion */}
      {qualitySuggestion && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
          <p className="text-yellow-800 text-sm">{qualitySuggestion}</p>
        </div>
      )}
      
      {/* Input level meter */}
      {audioState.isRecording && (
        <div className="space-y-2">
          <label className="text-sm text-gray-600">Input Level:</label>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-100"
              style={{ width: getInputLevelWidth() }}
            />
          </div>
        </div>
      )}
      
      {/* Controls */}
      <div className="flex items-center space-x-4">
        <button
          onClick={toggleStreaming}
          disabled={!audioState.isInitialized || !isEnabled || !socket || !sessionId}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            isStreaming
              ? 'bg-red-500 hover:bg-red-600 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-300 disabled:cursor-not-allowed'
          }`}
        >
          {isStreaming ? 'Stop Recording' : 'Start Recording'}
        </button>
        
        {!audioState.isInitialized && (
          <button
            onClick={audioControls.initialize}
            className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
          >
            Initialize Audio
          </button>
        )}
      </div>
      
      {/* Status indicators */}
      <div className="flex items-center space-x-4 text-sm text-gray-600">
        <div className="flex items-center space-x-1">
          <div className={`w-2 h-2 rounded-full ${audioState.isInitialized ? 'bg-green-500' : 'bg-gray-300'}`} />
          <span>Initialized</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-green-500' : 'bg-gray-300'}`} />
          <span>Streaming</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className={`w-2 h-2 rounded-full ${socket?.connected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span>Connected</span>
        </div>
      </div>
      
      {/* Live transcription display */}
      {transcription && (
        <div className="bg-gray-50 border border-gray-200 rounded p-3">
          <label className="text-sm font-medium text-gray-700 block mb-2">Live Transcription:</label>
          <p className="text-gray-900 text-sm">{transcription}</p>
        </div>
      )}
    </div>
  );
};

export default AudioCapture;