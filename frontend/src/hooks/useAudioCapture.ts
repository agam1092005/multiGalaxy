/**
 * React hook for audio capture functionality
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { AudioCaptureService, AudioConfig, AudioQualityMetrics, AudioChunkData } from '../services/audioCapture';

export interface AudioCaptureState {
  isInitialized: boolean;
  isRecording: boolean;
  isSupported: boolean;
  error: string | null;
  quality: AudioQualityMetrics | null;
  inputLevel: number;
}

export interface AudioCaptureControls {
  initialize: () => Promise<void>;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  cleanup: () => void;
}

export interface UseAudioCaptureOptions {
  config?: Partial<AudioConfig>;
  onAudioChunk?: (chunk: AudioChunkData) => void;
  onQualityUpdate?: (quality: AudioQualityMetrics) => void;
  onError?: (error: Error) => void;
  autoInitialize?: boolean;
}

export const useAudioCapture = (options: UseAudioCaptureOptions = {}): [AudioCaptureState, AudioCaptureControls] => {
  const {
    config,
    onAudioChunk,
    onQualityUpdate,
    onError,
    autoInitialize = false
  } = options;
  
  const [state, setState] = useState<AudioCaptureState>({
    isInitialized: false,
    isRecording: false,
    isSupported: AudioCaptureService.isSupported(),
    error: null,
    quality: null,
    inputLevel: 0
  });
  
  const audioServiceRef = useRef<AudioCaptureService | null>(null);
  const inputLevelIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Initialize audio service
  const initialize = useCallback(async () => {
    if (!state.isSupported) {
      const error = new Error('Audio capture not supported in this browser');
      setState(prev => ({ ...prev, error: error.message }));
      if (onError) onError(error);
      return;
    }
    
    try {
      setState(prev => ({ ...prev, error: null }));
      
      // Create new audio service instance
      audioServiceRef.current = new AudioCaptureService(config);
      
      // Initialize the service
      await audioServiceRef.current.initialize();
      
      setState(prev => ({ ...prev, isInitialized: true }));
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({ 
        ...prev, 
        isInitialized: false, 
        error: errorMessage 
      }));
      
      if (onError) {
        onError(error instanceof Error ? error : new Error(errorMessage));
      }
    }
  }, [config, state.isSupported, onError]);
  
  // Start recording
  const startRecording = useCallback(async () => {
    if (!audioServiceRef.current || !state.isInitialized) {
      const error = new Error('Audio service not initialized');
      setState(prev => ({ ...prev, error: error.message }));
      if (onError) onError(error);
      return;
    }
    
    if (state.isRecording) {
      return; // Already recording
    }
    
    try {
      setState(prev => ({ ...prev, error: null }));
      
      await audioServiceRef.current.startRecording(
        (chunk: AudioChunkData) => {
          if (onAudioChunk) {
            onAudioChunk(chunk);
          }
        },
        (error: Error) => {
          setState(prev => ({ 
            ...prev, 
            isRecording: false, 
            error: error.message 
          }));
          if (onError) onError(error);
        },
        (quality: AudioQualityMetrics) => {
          setState(prev => ({ ...prev, quality }));
          if (onQualityUpdate) onQualityUpdate(quality);
        }
      );
      
      setState(prev => ({ ...prev, isRecording: true }));
      
      // Start input level monitoring
      inputLevelIntervalRef.current = setInterval(() => {
        if (audioServiceRef.current) {
          const level = audioServiceRef.current.getInputLevel();
          setState(prev => ({ ...prev, inputLevel: level }));
        }
      }, 100); // Update every 100ms
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({ 
        ...prev, 
        isRecording: false, 
        error: errorMessage 
      }));
      
      if (onError) {
        onError(error instanceof Error ? error : new Error(errorMessage));
      }
    }
  }, [state.isInitialized, state.isRecording, onAudioChunk, onQualityUpdate, onError]);
  
  // Stop recording
  const stopRecording = useCallback(() => {
    if (!audioServiceRef.current || !state.isRecording) {
      return;
    }
    
    try {
      audioServiceRef.current.stopRecording();
      setState(prev => ({ ...prev, isRecording: false, inputLevel: 0 }));
      
      // Clear input level monitoring
      if (inputLevelIntervalRef.current) {
        clearInterval(inputLevelIntervalRef.current);
        inputLevelIntervalRef.current = null;
      }
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({ ...prev, error: errorMessage }));
      
      if (onError) {
        onError(error instanceof Error ? error : new Error(errorMessage));
      }
    }
  }, [state.isRecording, onError]);
  
  // Cleanup
  const cleanup = useCallback(() => {
    if (inputLevelIntervalRef.current) {
      clearInterval(inputLevelIntervalRef.current);
      inputLevelIntervalRef.current = null;
    }
    
    if (audioServiceRef.current) {
      audioServiceRef.current.cleanup();
      audioServiceRef.current = null;
    }
    
    setState({
      isInitialized: false,
      isRecording: false,
      isSupported: AudioCaptureService.isSupported(),
      error: null,
      quality: null,
      inputLevel: 0
    });
  }, []);
  
  // Auto-initialize if requested
  useEffect(() => {
    if (autoInitialize && state.isSupported && !state.isInitialized) {
      initialize();
    }
  }, [autoInitialize, state.isSupported, state.isInitialized, initialize]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);
  
  const controls: AudioCaptureControls = {
    initialize,
    startRecording,
    stopRecording,
    cleanup
  };
  
  return [state, controls];
};

export default useAudioCapture;