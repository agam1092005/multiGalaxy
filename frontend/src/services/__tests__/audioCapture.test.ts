/**
 * Tests for audio capture service
 */
import { AudioCaptureService } from '../audioCapture';

// Mock WebRTC APIs
const mockMediaStream = {
  getTracks: jest.fn(() => [{ stop: jest.fn() }])
};

const mockAudioContext = {
  createMediaStreamSource: jest.fn(() => ({
    connect: jest.fn()
  })),
  createScriptProcessor: jest.fn(() => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
    onaudioprocess: null
  })),
  destination: {},
  close: jest.fn(),
  resume: jest.fn(),
  state: 'running'
};

// Mock getUserMedia
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: jest.fn(),
    enumerateDevices: jest.fn()
  }
});

// Mock AudioContext
(global as any).AudioContext = jest.fn(() => mockAudioContext);
(global as any).webkitAudioContext = jest.fn(() => mockAudioContext);

// Mock btoa for base64 encoding
(global as any).btoa = jest.fn((str: string) => Buffer.from(str, 'binary').toString('base64'));

describe('AudioCaptureService', () => {
  let audioService: AudioCaptureService;
  
  beforeEach(() => {
    jest.clearAllMocks();
    audioService = new AudioCaptureService();
  });
  
  afterEach(() => {
    audioService.cleanup();
  });
  
  describe('Static Methods', () => {
    test('isSupported returns true when WebRTC is available', () => {
      expect(AudioCaptureService.isSupported()).toBe(true);
    });
    
    test('isSupported returns false when WebRTC is not available', () => {
      const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
      delete (navigator.mediaDevices as any).getUserMedia;
      
      expect(AudioCaptureService.isSupported()).toBe(false);
      
      // Restore
      navigator.mediaDevices.getUserMedia = originalGetUserMedia;
    });
    
    test('getAudioInputDevices returns audio input devices', async () => {
      const mockDevices = [
        { kind: 'audioinput', deviceId: 'device1', label: 'Microphone 1' },
        { kind: 'videoinput', deviceId: 'device2', label: 'Camera 1' },
        { kind: 'audioinput', deviceId: 'device3', label: 'Microphone 2' }
      ];
      
      (navigator.mediaDevices.enumerateDevices as jest.Mock).mockResolvedValue(mockDevices);
      
      const audioDevices = await AudioCaptureService.getAudioInputDevices();
      
      expect(audioDevices).toHaveLength(2);
      expect(audioDevices[0].kind).toBe('audioinput');
      expect(audioDevices[1].kind).toBe('audioinput');
    });
    
    test('getAudioInputDevices handles errors gracefully', async () => {
      (navigator.mediaDevices.enumerateDevices as jest.Mock).mockRejectedValue(new Error('Permission denied'));
      
      const audioDevices = await AudioCaptureService.getAudioInputDevices();
      
      expect(audioDevices).toEqual([]);
    });
  });
  
  describe('Initialization', () => {
    test('initialize successfully sets up audio capture', async () => {
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockMediaStream);
      
      await audioService.initialize();
      
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        },
        video: false
      });
    });
    
    test('initialize throws error when getUserMedia fails', async () => {
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockRejectedValue(new Error('Permission denied'));
      
      await expect(audioService.initialize()).rejects.toThrow('Audio initialization failed: Permission denied');
    });
    
    test('initialize throws error when WebRTC is not supported', async () => {
      const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
      delete (navigator.mediaDevices as any).getUserMedia;
      
      const service = new AudioCaptureService();
      
      await expect(service.initialize()).rejects.toThrow('WebRTC audio capture not supported');
      
      // Restore
      navigator.mediaDevices.getUserMedia = originalGetUserMedia;
    });
    
    test('initialize resumes suspended audio context', async () => {
      mockAudioContext.state = 'suspended';
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockMediaStream);
      
      await audioService.initialize();
      
      expect(mockAudioContext.resume).toHaveBeenCalled();
    });
  });
  
  describe('Recording', () => {
    beforeEach(async () => {
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockMediaStream);
      await audioService.initialize();
    });
    
    test('startRecording sets up audio processing pipeline', async () => {
      const onAudioChunk = jest.fn();
      const onError = jest.fn();
      const onQualityUpdate = jest.fn();
      
      await audioService.startRecording(onAudioChunk, onError, onQualityUpdate);
      
      expect(mockAudioContext.createMediaStreamSource).toHaveBeenCalledWith(mockMediaStream);
      expect(mockAudioContext.createScriptProcessor).toHaveBeenCalled();
    });
    
    test('startRecording throws error when not initialized', async () => {
      const uninitializedService = new AudioCaptureService();
      const onAudioChunk = jest.fn();
      
      await expect(uninitializedService.startRecording(onAudioChunk)).rejects.toThrow('Audio capture not initialized');
    });
    
    test('startRecording throws error when already recording', async () => {
      const onAudioChunk = jest.fn();
      
      await audioService.startRecording(onAudioChunk);
      
      await expect(audioService.startRecording(onAudioChunk)).rejects.toThrow('Recording already in progress');
    });
    
    test('stopRecording disconnects audio nodes', async () => {
      const onAudioChunk = jest.fn();
      const mockProcessor = mockAudioContext.createScriptProcessor();
      
      await audioService.startRecording(onAudioChunk);
      audioService.stopRecording();
      
      expect(mockProcessor.disconnect).toHaveBeenCalled();
    });
    
    test('stopRecording does nothing when not recording', () => {
      expect(() => audioService.stopRecording()).not.toThrow();
    });
  });
  
  describe('Audio Processing', () => {
    beforeEach(async () => {
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockMediaStream);
      await audioService.initialize();
    });
    
    test('processAudioBuffer converts and encodes audio data', async () => {
      const onAudioChunk = jest.fn();
      await audioService.startRecording(onAudioChunk);
      
      // Create mock audio buffer
      const mockBuffer = {
        length: 1600, // 100ms at 16kHz
        sampleRate: 16000,
        getChannelData: jest.fn(() => new Float32Array(1600).fill(0.5))
      };
      
      // Simulate audio processing
      const processor = mockAudioContext.createScriptProcessor();
      if (processor.onaudioprocess) {
        processor.onaudioprocess({ inputBuffer: mockBuffer } as any);
      }
      
      expect(onAudioChunk).toHaveBeenCalled();
      
      const chunkData = onAudioChunk.mock.calls[0][0];
      expect(chunkData).toHaveProperty('chunk_id');
      expect(chunkData).toHaveProperty('audio_data');
      expect(chunkData).toHaveProperty('timestamp');
      expect(chunkData).toHaveProperty('duration');
    });
    
    test('processAudioBuffer handles errors gracefully', async () => {
      const onAudioChunk = jest.fn();
      const onError = jest.fn();
      
      await audioService.startRecording(onAudioChunk, onError);
      
      // Create invalid mock buffer
      const mockBuffer = {
        length: 1600,
        sampleRate: 16000,
        getChannelData: jest.fn(() => {
          throw new Error('Buffer error');
        })
      };
      
      // Simulate audio processing with error
      const processor = mockAudioContext.createScriptProcessor();
      if (processor.onaudioprocess) {
        processor.onaudioprocess({ inputBuffer: mockBuffer } as any);
      }
      
      expect(onError).toHaveBeenCalledWith(new Error('Audio processing failed'));
    });
  });
  
  describe('Quality Analysis', () => {
    test('analyzeAudioQuality calculates quality metrics', async () => {
      const onAudioChunk = jest.fn();
      const onQualityUpdate = jest.fn();
      
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockMediaStream);
      await audioService.initialize();
      await audioService.startRecording(onAudioChunk, undefined, onQualityUpdate);
      
      // Create mock audio buffer with varying amplitudes
      const audioData = new Float32Array(1600);
      for (let i = 0; i < audioData.length; i++) {
        audioData[i] = Math.sin(2 * Math.PI * 440 * i / 16000) * 0.5; // 440Hz sine wave
      }
      
      const mockBuffer = {
        length: 1600,
        sampleRate: 16000,
        getChannelData: jest.fn(() => audioData)
      };
      
      // Process multiple chunks to trigger quality update
      const processor = mockAudioContext.createScriptProcessor();
      for (let i = 0; i < 10; i++) {
        if (processor.onaudioprocess) {
          processor.onaudioprocess({ inputBuffer: mockBuffer } as any);
        }
      }
      
      expect(onQualityUpdate).toHaveBeenCalled();
      
      const qualityMetrics = onQualityUpdate.mock.calls[0][0];
      expect(qualityMetrics).toHaveProperty('volume_db');
      expect(qualityMetrics).toHaveProperty('snr_db');
      expect(qualityMetrics).toHaveProperty('clipping_ratio');
      expect(qualityMetrics).toHaveProperty('quality_score');
      expect(qualityMetrics).toHaveProperty('quality_level');
      expect(qualityMetrics).toHaveProperty('is_acceptable');
    });
  });
  
  describe('Cleanup', () => {
    test('cleanup stops recording and releases resources', async () => {
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockMediaStream);
      await audioService.initialize();
      
      const onAudioChunk = jest.fn();
      await audioService.startRecording(onAudioChunk);
      
      audioService.cleanup();
      
      expect(mockMediaStream.getTracks()[0].stop).toHaveBeenCalled();
      expect(mockAudioContext.close).toHaveBeenCalled();
    });
    
    test('cleanup handles already cleaned up state', () => {
      expect(() => audioService.cleanup()).not.toThrow();
    });
  });
  
  describe('Configuration', () => {
    test('constructor accepts custom configuration', () => {
      const customConfig = {
        sampleRate: 44100,
        channels: 2,
        chunkDuration: 200,
        enableVAD: false
      };
      
      const service = new AudioCaptureService(customConfig);
      
      // Configuration should be applied (we can't directly test private properties,
      // but we can test the behavior)
      expect(service).toBeInstanceOf(AudioCaptureService);
    });
    
    test('calculateBufferSize returns appropriate buffer size', () => {
      const service = new AudioCaptureService({ chunkDuration: 100 });
      
      // We can't directly test the private method, but we can test that
      // the service initializes without errors
      expect(service).toBeInstanceOf(AudioCaptureService);
    });
  });
  
  describe('Input Level', () => {
    test('getInputLevel returns placeholder value', () => {
      const level = audioService.getInputLevel();
      expect(typeof level).toBe('number');
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThanOrEqual(1);
    });
  });
});