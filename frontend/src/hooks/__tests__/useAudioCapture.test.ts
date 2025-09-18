/**
 * Tests for useAudioCapture hook
 */
import { renderHook, act } from '@testing-library/react';
import { useAudioCapture } from '../useAudioCapture';
import { AudioCaptureService } from '../../services/audioCapture';

// Mock the AudioCaptureService
jest.mock('../../services/audioCapture');

const MockedAudioCaptureService = AudioCaptureService as jest.MockedClass<typeof AudioCaptureService>;

describe('useAudioCapture', () => {
  let mockAudioService: jest.Mocked<AudioCaptureService>;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Create mock instance
    mockAudioService = {
      initialize: jest.fn(),
      startRecording: jest.fn(),
      stopRecording: jest.fn(),
      cleanup: jest.fn(),
      getInputLevel: jest.fn(() => 0.5)
    } as any;
    
    // Mock constructor to return our mock instance
    MockedAudioCaptureService.mockImplementation(() => mockAudioService);
    
    // Mock static methods
    MockedAudioCaptureService.isSupported = jest.fn(() => true);
  });
  
  test('initializes with correct default state', () => {
    const { result } = renderHook(() => useAudioCapture());
    
    const [state] = result.current;
    
    expect(state.isInitialized).toBe(false);
    expect(state.isRecording).toBe(false);
    expect(state.isSupported).toBe(true);
    expect(state.error).toBe(null);
    expect(state.quality).toBe(null);
    expect(state.inputLevel).toBe(0);
  });
  
  test('initializes with unsupported browser', () => {
    MockedAudioCaptureService.isSupported.mockReturnValue(false);
    
    const { result } = renderHook(() => useAudioCapture());
    
    const [state] = result.current;
    
    expect(state.isSupported).toBe(false);
  });
  
  test('auto-initializes when autoInitialize is true', async () => {
    mockAudioService.initialize.mockResolvedValue();
    
    const { result } = renderHook(() => 
      useAudioCapture({ autoInitialize: true })
    );
    
    // Wait for initialization
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    expect(mockAudioService.initialize).toHaveBeenCalled();
  });
  
  test('initialize function works correctly', async () => {
    mockAudioService.initialize.mockResolvedValue();
    
    const { result } = renderHook(() => useAudioCapture());
    
    const [, controls] = result.current;
    
    await act(async () => {
      await controls.initialize();
    });
    
    expect(mockAudioService.initialize).toHaveBeenCalled();
    expect(result.current[0].isInitialized).toBe(true);
    expect(result.current[0].error).toBe(null);
  });
  
  test('initialize handles errors', async () => {
    const error = new Error('Initialization failed');
    mockAudioService.initialize.mockRejectedValue(error);
    
    const onError = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onError }));
    
    const [, controls] = result.current;
    
    await act(async () => {
      await controls.initialize();
    });
    
    expect(result.current[0].isInitialized).toBe(false);
    expect(result.current[0].error).toBe('Initialization failed');
    expect(onError).toHaveBeenCalledWith(error);
  });
  
  test('initialize fails when not supported', async () => {
    MockedAudioCaptureService.isSupported.mockReturnValue(false);
    
    const onError = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onError }));
    
    const [, controls] = result.current;
    
    await act(async () => {
      await controls.initialize();
    });
    
    expect(result.current[0].error).toBe('Audio capture not supported in this browser');
    expect(onError).toHaveBeenCalled();
  });
  
  test('startRecording works correctly', async () => {
    mockAudioService.initialize.mockResolvedValue();
    mockAudioService.startRecording.mockResolvedValue();
    
    const onAudioChunk = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onAudioChunk }));
    
    const [, controls] = result.current;
    
    // Initialize first
    await act(async () => {
      await controls.initialize();
    });
    
    // Start recording
    await act(async () => {
      await controls.startRecording();
    });
    
    expect(mockAudioService.startRecording).toHaveBeenCalled();
    expect(result.current[0].isRecording).toBe(true);
  });
  
  test('startRecording fails when not initialized', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onError }));
    
    const [, controls] = result.current;
    
    await act(async () => {
      await controls.startRecording();
    });
    
    expect(result.current[0].error).toBe('Audio service not initialized');
    expect(onError).toHaveBeenCalled();
  });
  
  test('startRecording handles service errors', async () => {
    mockAudioService.initialize.mockResolvedValue();
    const error = new Error('Recording failed');
    mockAudioService.startRecording.mockRejectedValue(error);
    
    const onError = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onError }));
    
    const [, controls] = result.current;
    
    // Initialize first
    await act(async () => {
      await controls.initialize();
    });
    
    // Try to start recording
    await act(async () => {
      await controls.startRecording();
    });
    
    expect(result.current[0].isRecording).toBe(false);
    expect(result.current[0].error).toBe('Recording failed');
    expect(onError).toHaveBeenCalledWith(error);
  });
  
  test('stopRecording works correctly', async () => {
    mockAudioService.initialize.mockResolvedValue();
    mockAudioService.startRecording.mockResolvedValue();
    
    const { result } = renderHook(() => useAudioCapture());
    
    const [, controls] = result.current;
    
    // Initialize and start recording
    await act(async () => {
      await controls.initialize();
      await controls.startRecording();
    });
    
    // Stop recording
    act(() => {
      controls.stopRecording();
    });
    
    expect(mockAudioService.stopRecording).toHaveBeenCalled();
    expect(result.current[0].isRecording).toBe(false);
    expect(result.current[0].inputLevel).toBe(0);
  });
  
  test('stopRecording handles errors', () => {
    mockAudioService.stopRecording.mockImplementation(() => {
      throw new Error('Stop failed');
    });
    
    const onError = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onError }));
    
    const [, controls] = result.current;
    
    act(() => {
      controls.stopRecording();
    });
    
    expect(result.current[0].error).toBe('Stop failed');
    expect(onError).toHaveBeenCalled();
  });
  
  test('cleanup works correctly', () => {
    const { result } = renderHook(() => useAudioCapture());
    
    const [, controls] = result.current;
    
    act(() => {
      controls.cleanup();
    });
    
    expect(mockAudioService.cleanup).toHaveBeenCalled();
    
    const [state] = result.current;
    expect(state.isInitialized).toBe(false);
    expect(state.isRecording).toBe(false);
    expect(state.error).toBe(null);
    expect(state.quality).toBe(null);
    expect(state.inputLevel).toBe(0);
  });
  
  test('input level monitoring works during recording', async () => {
    mockAudioService.initialize.mockResolvedValue();
    mockAudioService.startRecording.mockResolvedValue();
    mockAudioService.getInputLevel.mockReturnValue(0.7);
    
    const { result } = renderHook(() => useAudioCapture());
    
    const [, controls] = result.current;
    
    // Initialize and start recording
    await act(async () => {
      await controls.initialize();
      await controls.startRecording();
    });
    
    // Wait for input level update
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    expect(result.current[0].inputLevel).toBe(0.7);
  });
  
  test('quality updates are handled correctly', async () => {
    mockAudioService.initialize.mockResolvedValue();
    
    const onQualityUpdate = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onQualityUpdate }));
    
    const [, controls] = result.current;
    
    await act(async () => {
      await controls.initialize();
    });
    
    // Simulate quality update callback
    const mockQuality = {
      volume_db: -15,
      snr_db: 20,
      clipping_ratio: 0.0,
      quality_score: 0.8,
      quality_level: 'good' as const,
      is_acceptable: true
    };
    
    await act(async () => {
      await controls.startRecording();
      
      // Get the quality callback from the startRecording call
      const startRecordingCall = mockAudioService.startRecording.mock.calls[0];
      const qualityCallback = startRecordingCall[2]; // Third argument
      
      if (qualityCallback) {
        qualityCallback(mockQuality);
      }
    });
    
    expect(result.current[0].quality).toEqual(mockQuality);
    expect(onQualityUpdate).toHaveBeenCalledWith(mockQuality);
  });
  
  test('audio chunk callbacks are handled correctly', async () => {
    mockAudioService.initialize.mockResolvedValue();
    
    const onAudioChunk = jest.fn();
    const { result } = renderHook(() => useAudioCapture({ onAudioChunk }));
    
    const [, controls] = result.current;
    
    await act(async () => {
      await controls.initialize();
      await controls.startRecording();
    });
    
    // Simulate audio chunk callback
    const mockChunk = {
      chunk_id: 'test_chunk',
      audio_data: 'base64data',
      timestamp: Date.now(),
      duration: 100
    };
    
    // Get the chunk callback from the startRecording call
    const startRecordingCall = mockAudioService.startRecording.mock.calls[0];
    const chunkCallback = startRecordingCall[0]; // First argument
    
    act(() => {
      if (chunkCallback) {
        chunkCallback(mockChunk);
      }
    });
    
    expect(onAudioChunk).toHaveBeenCalledWith(mockChunk);
  });
  
  test('cleanup is called on unmount', () => {
    const { unmount } = renderHook(() => useAudioCapture());
    
    unmount();
    
    expect(mockAudioService.cleanup).toHaveBeenCalled();
  });
  
  test('does not start recording when already recording', async () => {
    mockAudioService.initialize.mockResolvedValue();
    mockAudioService.startRecording.mockResolvedValue();
    
    const { result } = renderHook(() => useAudioCapture());
    
    const [, controls] = result.current;
    
    await act(async () => {
      await controls.initialize();
      await controls.startRecording();
    });
    
    // Try to start recording again
    await act(async () => {
      await controls.startRecording();
    });
    
    // Should only be called once
    expect(mockAudioService.startRecording).toHaveBeenCalledTimes(1);
  });
  
  test('does not stop recording when not recording', () => {
    const { result } = renderHook(() => useAudioCapture());
    
    const [, controls] = result.current;
    
    act(() => {
      controls.stopRecording();
    });
    
    // Should not call stopRecording on service
    expect(mockAudioService.stopRecording).not.toHaveBeenCalled();
  });
});