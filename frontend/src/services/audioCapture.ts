/**
 * Audio capture service using WebRTC for real-time audio processing
 */

export interface AudioConfig {
  sampleRate: number;
  channels: number;
  chunkDuration: number; // milliseconds
  enableVAD: boolean;
}

export interface AudioQualityMetrics {
  volume_db: number;
  snr_db: number;
  clipping_ratio: number;
  quality_score: number;
  quality_level: 'excellent' | 'good' | 'fair' | 'poor';
  is_acceptable: boolean;
}

export interface VoiceActivityResult {
  has_speech: boolean;
  activity_level: 'silent' | 'low' | 'medium' | 'high';
  energy: number;
  confidence: number;
}

export interface AudioChunkData {
  chunk_id: string;
  audio_data: string; // base64 encoded
  timestamp: number;
  duration: number;
}

export class AudioCaptureService {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private isRecording: boolean = false;
  private chunkCounter: number = 0;
  
  private config: AudioConfig = {
    sampleRate: 16000,
    channels: 1,
    chunkDuration: 100, // 100ms chunks
    enableVAD: true
  };
  
  private onAudioChunk?: (chunk: AudioChunkData) => void;
  private onError?: (error: Error) => void;
  private onQualityUpdate?: (quality: AudioQualityMetrics) => void;
  
  constructor(config?: Partial<AudioConfig>) {
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }
  
  /**
   * Initialize audio capture with microphone access
   */
  async initialize(): Promise<void> {
    try {
      // Check browser support
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('WebRTC audio capture not supported in this browser');
      }
      
      // Request microphone access
      const constraints: MediaStreamConstraints = {
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        },
        video: false
      };
      
      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      
      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.sampleRate
      });
      
      // Resume audio context if suspended (required by some browsers)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
      
      console.log('Audio capture initialized successfully');
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to initialize audio capture:', errorMsg);
      throw new Error(`Audio initialization failed: ${errorMsg}`);
    }
  }
  
  /**
   * Start audio recording and processing
   */
  async startRecording(
    onAudioChunk: (chunk: AudioChunkData) => void,
    onError?: (error: Error) => void,
    onQualityUpdate?: (quality: AudioQualityMetrics) => void
  ): Promise<void> {
    if (!this.mediaStream || !this.audioContext) {
      throw new Error('Audio capture not initialized');
    }
    
    if (this.isRecording) {
      throw new Error('Recording already in progress');
    }
    
    try {
      this.onAudioChunk = onAudioChunk;
      this.onError = onError;
      this.onQualityUpdate = onQualityUpdate;
      
      // Create audio source from media stream
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      
      // Create script processor for audio processing
      const bufferSize = this.calculateBufferSize();
      this.processor = this.audioContext.createScriptProcessor(bufferSize, this.config.channels, this.config.channels);
      
      // Set up audio processing
      this.processor.onaudioprocess = (event) => {
        this.processAudioBuffer(event.inputBuffer);
      };
      
      // Connect audio nodes
      source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      
      this.isRecording = true;
      this.chunkCounter = 0;
      
      console.log('Audio recording started');
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to start recording:', errorMsg);
      if (this.onError) {
        this.onError(new Error(`Recording start failed: ${errorMsg}`));
      }
      throw error;
    }
  }
  
  /**
   * Stop audio recording
   */
  stopRecording(): void {
    if (!this.isRecording) {
      return;
    }
    
    try {
      // Disconnect and clean up audio nodes
      if (this.processor) {
        this.processor.disconnect();
        this.processor = null;
      }
      
      this.isRecording = false;
      console.log('Audio recording stopped');
      
    } catch (error) {
      console.error('Error stopping recording:', error);
    }
  }
  
  /**
   * Clean up resources
   */
  cleanup(): void {
    this.stopRecording();
    
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    console.log('Audio capture cleaned up');
  }
  
  /**
   * Get current audio input level (for UI feedback)
   */
  getInputLevel(): number {
    // This would require additional audio analysis
    // For now, return a placeholder value
    return 0.5;
  }
  
  /**
   * Check if audio capture is supported
   */
  static isSupported(): boolean {
    return !!(
      navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia &&
      (window.AudioContext || (window as any).webkitAudioContext)
    );
  }
  
  /**
   * Get available audio input devices
   */
  static async getAudioInputDevices(): Promise<MediaDeviceInfo[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter(device => device.kind === 'audioinput');
    } catch (error) {
      console.error('Failed to enumerate audio devices:', error);
      return [];
    }
  }
  
  private calculateBufferSize(): number {
    // Calculate buffer size based on chunk duration
    const samplesPerChunk = (this.config.sampleRate * this.config.chunkDuration) / 1000;
    
    // Round to nearest power of 2 for optimal performance
    let bufferSize = 256;
    while (bufferSize < samplesPerChunk && bufferSize < 16384) {
      bufferSize *= 2;
    }
    
    return bufferSize;
  }
  
  private processAudioBuffer(buffer: AudioBuffer): void {
    try {
      // Get audio data from the first channel
      const audioData = buffer.getChannelData(0);
      
      // Convert float32 to int16 for transmission
      const int16Array = new Int16Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        // Clamp and convert to 16-bit integer
        const sample = Math.max(-1, Math.min(1, audioData[i]));
        int16Array[i] = sample * 0x7FFF;
      }
      
      // Convert to base64 for transmission
      const audioBytes = new Uint8Array(int16Array.buffer);
      const base64Audio = this.arrayBufferToBase64(audioBytes);
      
      // Create chunk data
      const chunkData: AudioChunkData = {
        chunk_id: `chunk_${this.chunkCounter++}`,
        audio_data: base64Audio,
        timestamp: Date.now(),
        duration: (buffer.length / buffer.sampleRate) * 1000 // duration in ms
      };
      
      // Send chunk to callback
      if (this.onAudioChunk) {
        this.onAudioChunk(chunkData);
      }
      
      // Perform basic quality analysis
      this.analyzeAudioQuality(audioData);
      
    } catch (error) {
      console.error('Error processing audio buffer:', error);
      if (this.onError) {
        this.onError(new Error('Audio processing failed'));
      }
    }
  }
  
  private analyzeAudioQuality(audioData: Float32Array): void {
    try {
      // Calculate RMS (volume)
      let sum = 0;
      for (let i = 0; i < audioData.length; i++) {
        sum += audioData[i] * audioData[i];
      }
      const rms = Math.sqrt(sum / audioData.length);
      const volumeDb = 20 * Math.log10(Math.max(rms, 1e-10));
      
      // Detect clipping
      let clippedSamples = 0;
      for (let i = 0; i < audioData.length; i++) {
        if (Math.abs(audioData[i]) > 0.95) {
          clippedSamples++;
        }
      }
      const clippingRatio = clippedSamples / audioData.length;
      
      // Simple SNR estimation (placeholder)
      const snrDb = Math.max(0, volumeDb + 40); // Rough estimate
      
      // Calculate quality score
      const qualityScore = this.calculateQualityScore(volumeDb, snrDb, clippingRatio);
      
      const qualityMetrics: AudioQualityMetrics = {
        volume_db: volumeDb,
        snr_db: snrDb,
        clipping_ratio: clippingRatio,
        quality_score: qualityScore,
        quality_level: this.getQualityLevel(qualityScore),
        is_acceptable: qualityScore > 0.5
      };
      
      // Send quality update periodically (every 10 chunks)
      if (this.chunkCounter % 10 === 0 && this.onQualityUpdate) {
        this.onQualityUpdate(qualityMetrics);
      }
      
    } catch (error) {
      console.error('Error analyzing audio quality:', error);
    }
  }
  
  private calculateQualityScore(volumeDb: number, snrDb: number, clippingRatio: number): number {
    // Volume score (optimal range: -20 to -10 dB)
    let volumeScore = 1.0;
    if (volumeDb < -40 || volumeDb > 0) {
      volumeScore = 0.0;
    } else if (volumeDb < -25 || volumeDb > -5) {
      volumeScore = Math.max(0, 1 - Math.abs(volumeDb + 15) / 25);
    }
    
    // SNR score
    const snrScore = Math.min(1.0, Math.max(0.0, (snrDb - 5) / 20));
    
    // Clipping penalty
    const clippingScore = Math.max(0.0, 1.0 - clippingRatio * 10);
    
    // Weighted average
    return volumeScore * 0.4 + snrScore * 0.4 + clippingScore * 0.2;
  }
  
  private getQualityLevel(qualityScore: number): 'excellent' | 'good' | 'fair' | 'poor' {
    if (qualityScore >= 0.8) return 'excellent';
    if (qualityScore >= 0.6) return 'good';
    if (qualityScore >= 0.4) return 'fair';
    return 'poor';
  }
  
  private arrayBufferToBase64(buffer: Uint8Array): string {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  }
}

export default AudioCaptureService;