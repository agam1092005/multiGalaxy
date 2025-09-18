/**
 * Text-to-Speech service for Multi-Galaxy-Note frontend
 * 
 * Handles TTS synthesis requests and audio playback for AI responses
 */

import { apiService } from './api';

export interface VoiceSettings {
  language_code: string;
  voice_gender: 'male' | 'female' | 'neutral';
  speaking_rate: number;
  pitch: number;
  audio_format: 'mp3' | 'wav' | 'ogg';
}

export interface TTSRequest {
  text: string;
  voice_preset?: string;
  language_code?: string;
  voice_gender?: 'male' | 'female' | 'neutral';
  speaking_rate?: number;
  pitch?: number;
  audio_format?: 'mp3' | 'wav' | 'ogg';
}

export interface TTSResponse {
  audio_url: string;
  duration_seconds?: number;
  text_length: number;
  audio_format: string;
  voice_settings: VoiceSettings;
  synthesis_id: string;
  created_at: string;
}

export interface EducationalTTSResponse {
  audio_url: string;
  duration_seconds?: number;
  feedback_type: string;
  voice_preset_used: string;
  synthesis_id: string;
  created_at: string;
}

export interface AudioPlayer {
  play(): Promise<void>;
  pause(): void;
  stop(): void;
  setVolume(volume: number): void;
  getCurrentTime(): number;
  getDuration(): number;
  isPlaying(): boolean;
  onEnded(callback: () => void): void;
  onTimeUpdate(callback: (currentTime: number) => void): void;
}

class TextToSpeechService {
  private audioContext: AudioContext | null = null;
  private currentAudio: HTMLAudioElement | null = null;
  private isInitialized = false;

  constructor() {
    this.initializeAudioContext();
  }

  private async initializeAudioContext(): Promise<void> {
    try {
      // Initialize Web Audio API context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.isInitialized = true;
    } catch (error) {
      console.warn('Web Audio API not supported:', error);
      this.isInitialized = false;
    }
  }

  /**
   * Synthesize text to speech
   */
  async synthesizeText(request: TTSRequest): Promise<TTSResponse> {
    try {
      const response = await apiService.post<TTSResponse>('/tts-whiteboard/synthesize', request);
      return response;
    } catch (error) {
      console.error('Error synthesizing text:', error);
      throw new Error('Failed to synthesize text to speech');
    }
  }

  /**
   * Synthesize educational AI response with appropriate voice settings
   */
  async synthesizeEducationalResponse(
    textResponse: string,
    feedbackType: string = 'explanation',
    sessionId?: string
  ): Promise<EducationalTTSResponse> {
    try {
      const response = await apiService.post<EducationalTTSResponse>(
        '/tts-whiteboard/educational-synthesis',
        null,
        {
          params: {
            text_response: textResponse,
            feedback_type: feedbackType,
            session_id: sessionId
          }
        }
      );
      return response;
    } catch (error) {
      console.error('Error synthesizing educational response:', error);
      throw new Error('Failed to synthesize educational response');
    }
  }

  /**
   * Create audio player for TTS response
   */
  createAudioPlayer(audioUrl: string): AudioPlayer {
    const audio = new Audio(audioUrl);
    audio.preload = 'auto';

    return {
      play: async (): Promise<void> => {
        try {
          // Resume audio context if suspended (required by some browsers)
          if (this.audioContext && this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
          }
          
          // Stop current audio if playing
          if (this.currentAudio && !this.currentAudio.paused) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
          }
          
          this.currentAudio = audio;
          await audio.play();
        } catch (error) {
          console.error('Error playing audio:', error);
          throw new Error('Failed to play audio');
        }
      },

      pause: (): void => {
        audio.pause();
      },

      stop: (): void => {
        audio.pause();
        audio.currentTime = 0;
      },

      setVolume: (volume: number): void => {
        audio.volume = Math.max(0, Math.min(1, volume));
      },

      getCurrentTime: (): number => {
        return audio.currentTime;
      },

      getDuration: (): number => {
        return audio.duration || 0;
      },

      isPlaying: (): boolean => {
        return !audio.paused && !audio.ended;
      },

      onEnded: (callback: () => void): void => {
        audio.addEventListener('ended', callback);
      },

      onTimeUpdate: (callback: (currentTime: number) => void): void => {
        audio.addEventListener('timeupdate', () => {
          callback(audio.currentTime);
        });
      }
    };
  }

  /**
   * Play TTS response directly
   */
  async playTTSResponse(ttsResponse: TTSResponse | EducationalTTSResponse): Promise<AudioPlayer> {
    const player = this.createAudioPlayer(ttsResponse.audio_url);
    await player.play();
    return player;
  }

  /**
   * Get available voices for a language
   */
  async getAvailableVoices(languageCode: string = 'en-US'): Promise<{
    language_code: string;
    voices: Array<{
      name: string;
      language_codes: string[];
      gender: string;
      natural_sample_rate: number;
    }>;
    total_voices: number;
    voice_presets: string[];
  }> {
    try {
      const response = await apiService.get(`/tts-whiteboard/available-voices?language_code=${languageCode}`);
      return response;
    } catch (error) {
      console.error('Error getting available voices:', error);
      throw new Error('Failed to get available voices');
    }
  }

  /**
   * Stop all currently playing audio
   */
  stopAllAudio(): void {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
  }

  /**
   * Check if TTS is supported
   */
  isSupported(): boolean {
    return this.isInitialized && 'Audio' in window;
  }

  /**
   * Get TTS service health status
   */
  async getHealthStatus(): Promise<{
    status: string;
    tts_service: any;
    whiteboard_service: any;
  }> {
    try {
      const response = await apiService.get('/tts-whiteboard/health');
      return response;
    } catch (error) {
      console.error('Error getting TTS health status:', error);
      throw new Error('Failed to get TTS health status');
    }
  }

  /**
   * Create synchronized audio and visual playback
   */
  createSynchronizedPlayback(
    audioUrl: string,
    synchronizedText: Array<{
      text: string;
      start_time_ms: number;
      end_time_ms: number;
      step_index: number;
      emphasis: string;
    }>,
    onTextHighlight?: (text: string, stepIndex: number) => void
  ): AudioPlayer {
    const player = this.createAudioPlayer(audioUrl);
    let highlightTimeouts: NodeJS.Timeout[] = [];

    // Set up text highlighting based on audio timing
    player.onTimeUpdate((currentTime: number) => {
      const currentTimeMs = currentTime * 1000;
      
      // Find current text segment
      const currentSegment = synchronizedText.find(
        segment => currentTimeMs >= segment.start_time_ms && currentTimeMs <= segment.end_time_ms
      );
      
      if (currentSegment && onTextHighlight) {
        onTextHighlight(currentSegment.text, currentSegment.step_index);
      }
    });

    // Clean up timeouts when audio ends
    player.onEnded(() => {
      highlightTimeouts.forEach(timeout => clearTimeout(timeout));
      highlightTimeouts = [];
    });

    return player;
  }

  /**
   * Preload audio for faster playback
   */
  async preloadAudio(audioUrl: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const audio = new Audio(audioUrl);
      audio.preload = 'auto';
      
      audio.addEventListener('canplaythrough', () => resolve());
      audio.addEventListener('error', (error) => reject(error));
      
      // Start loading
      audio.load();
    });
  }

  /**
   * Create audio visualization (simple volume meter)
   */
  createAudioVisualization(audioPlayer: AudioPlayer, canvas: HTMLCanvasElement): void {
    if (!this.audioContext) {
      console.warn('Audio visualization requires Web Audio API');
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // This is a simplified visualization
    // In a full implementation, you would connect the audio to an AnalyserNode
    const drawVisualization = () => {
      if (!audioPlayer.isPlaying()) return;

      const width = canvas.width;
      const height = canvas.height;
      
      // Clear canvas
      ctx.clearRect(0, 0, width, height);
      
      // Draw simple progress bar
      const progress = audioPlayer.getCurrentTime() / audioPlayer.getDuration();
      const progressWidth = width * progress;
      
      ctx.fillStyle = '#3b82f6';
      ctx.fillRect(0, height - 10, progressWidth, 10);
      
      ctx.strokeStyle = '#e5e7eb';
      ctx.strokeRect(0, height - 10, width, 10);
      
      requestAnimationFrame(drawVisualization);
    };

    drawVisualization();
  }
}

export const textToSpeechService = new TextToSpeechService();