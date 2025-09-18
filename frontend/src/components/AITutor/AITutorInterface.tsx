/**
 * AI Tutor Interface Component
 * 
 * Integrates TTS and whiteboard interactions for synchronized voice and visual explanations
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Canvas } from 'fabric';
import { textToSpeechService, AudioPlayer, EducationalTTSResponse } from '../../services/textToSpeech';
import { whiteboardInteractionService, WhiteboardAction, VisualDemonstration } from '../../services/whiteboardInteraction';
import { Whiteboard } from '../Whiteboard/Whiteboard';

export interface AIResponse {
  text_response: string;
  feedback_type: string;
  confidence_score: number;
  whiteboard_actions: WhiteboardAction[];
  audio_url?: string;
  audio_duration?: number;
  visual_demonstration_id?: string;
  synchronized_text: Array<{
    text: string;
    start_time_ms: number;
    end_time_ms: number;
    step_index: number;
    emphasis: string;
  }>;
}

export interface AITutorInterfaceProps {
  sessionId: string;
  userId: string;
  onResponse?: (response: AIResponse) => void;
  className?: string;
}

export const AITutorInterface: React.FC<AITutorInterfaceProps> = ({
  sessionId,
  userId,
  onResponse,
  className = ''
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentAudioPlayer, setCurrentAudioPlayer] = useState<AudioPlayer | null>(null);
  const [currentDemonstration, setCurrentDemonstration] = useState<VisualDemonstration | null>(null);
  const [highlightedText, setHighlightedText] = useState<string>('');
  const [currentStep, setCurrentStep] = useState<number>(-1);
  const [isExecutingActions, setIsExecutingActions] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [visualEnabled, setVisualEnabled] = useState(true);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  
  const canvasRef = useRef<Canvas | null>(null);
  const whiteboardRef = useRef<HTMLDivElement>(null);

  /**
   * Handle AI response with TTS and whiteboard integration
   */
  const handleAIResponse = useCallback(async (response: AIResponse) => {
    try {
      // Stop any current playback
      await stopCurrentPlayback();

      // Generate TTS audio if not provided and audio is enabled
      let audioPlayer: AudioPlayer | null = null;
      if (audioEnabled && !response.audio_url) {
        const ttsResponse = await textToSpeechService.synthesizeEducationalResponse(
          response.text_response,
          response.feedback_type,
          sessionId
        );
        response.audio_url = ttsResponse.audio_url;
        response.audio_duration = ttsResponse.duration_seconds;
      }

      // Create audio player if audio URL is available
      if (audioEnabled && response.audio_url) {
        if (response.synchronized_text.length > 0) {
          // Create synchronized playback
          audioPlayer = textToSpeechService.createSynchronizedPlayback(
            response.audio_url,
            response.synchronized_text,
            (text, stepIndex) => {
              setHighlightedText(text);
              setCurrentStep(stepIndex);
            }
          );
        } else {
          // Create regular audio player
          audioPlayer = textToSpeechService.createAudioPlayer(response.audio_url);
        }

        // Set up audio event handlers
        audioPlayer.onEnded(() => {
          setIsPlaying(false);
          setHighlightedText('');
          setCurrentStep(-1);
        });

        setCurrentAudioPlayer(audioPlayer);
      }

      // Execute whiteboard actions if visual is enabled
      if (visualEnabled && response.whiteboard_actions.length > 0 && canvasRef.current) {
        setIsExecutingActions(true);
        
        await whiteboardInteractionService.executeActions(
          canvasRef.current,
          response.whiteboard_actions,
          (action, index) => {
            console.log(`Completed action ${index + 1}/${response.whiteboard_actions.length}`);
          },
          () => {
            setIsExecutingActions(false);
            console.log('All whiteboard actions completed');
          }
        );
      }

      // Get visual demonstration if available
      if (response.visual_demonstration_id) {
        try {
          const demonstrationActions = await whiteboardInteractionService.getDemonstrationActions(
            response.visual_demonstration_id
          );
          
          const demonstration = whiteboardInteractionService.getCachedDemonstration(
            response.visual_demonstration_id
          );
          
          if (demonstration) {
            setCurrentDemonstration(demonstration);
          }
        } catch (error) {
          console.error('Error loading visual demonstration:', error);
        }
      }

      // Notify parent component
      if (onResponse) {
        onResponse(response);
      }

    } catch (error) {
      console.error('Error handling AI response:', error);
    }
  }, [sessionId, audioEnabled, visualEnabled, onResponse]);

  /**
   * Start synchronized playback of audio and visual demonstration
   */
  const startSynchronizedPlayback = useCallback(async () => {
    if (!currentAudioPlayer) return;

    try {
      setIsPlaying(true);
      await currentAudioPlayer.play();
    } catch (error) {
      console.error('Error starting playback:', error);
      setIsPlaying(false);
    }
  }, [currentAudioPlayer]);

  /**
   * Pause current playback
   */
  const pausePlayback = useCallback(() => {
    if (currentAudioPlayer) {
      currentAudioPlayer.pause();
      setIsPlaying(false);
    }
  }, [currentAudioPlayer]);

  /**
   * Stop current playback and reset state
   */
  const stopCurrentPlayback = useCallback(async () => {
    if (currentAudioPlayer) {
      currentAudioPlayer.stop();
      setCurrentAudioPlayer(null);
    }
    
    setIsPlaying(false);
    setHighlightedText('');
    setCurrentStep(-1);
    setIsExecutingActions(false);
    
    // Stop whiteboard animations
    whiteboardInteractionService.stopAllAnimations();
  }, [currentAudioPlayer]);

  /**
   * Handle canvas reference from Whiteboard component
   */
  const handleCanvasReady = useCallback((canvas: Canvas) => {
    canvasRef.current = canvas;
  }, []);

  /**
   * Create error correction visualization
   */
  const createErrorCorrection = useCallback(async (
    errorLocation: [number, number],
    correctionText: string
  ) => {
    if (!canvasRef.current) return;

    try {
      const correction = await whiteboardInteractionService.createErrorCorrection({
        error_location: errorLocation,
        correction_text: correctionText,
        canvas_width: 800,
        canvas_height: 600
      });

      await whiteboardInteractionService.executeActions(
        canvasRef.current,
        correction.actions
      );
    } catch (error) {
      console.error('Error creating error correction:', error);
    }
  }, []);

  /**
   * Create AI feedback annotation
   */
  const createAnnotation = useCallback(async (
    text: string,
    position: [number, number],
    feedbackType: string = 'explanation'
  ) => {
    if (!canvasRef.current) return;

    try {
      const annotation = await whiteboardInteractionService.createAnnotation({
        text,
        position,
        feedback_type: feedbackType
      });

      await whiteboardInteractionService.executeActions(
        canvasRef.current,
        [annotation.action]
      );
    } catch (error) {
      console.error('Error creating annotation:', error);
    }
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      stopCurrentPlayback();
    };
  }, [stopCurrentPlayback]);

  return (
    <div className={`ai-tutor-interface ${className}`}>
      {/* Control Panel */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">AI Tutor Controls</h3>
          
          <div className="flex items-center space-x-4">
            {/* Audio Toggle */}
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={audioEnabled}
                onChange={(e) => setAudioEnabled(e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">Audio</span>
            </label>
            
            {/* Visual Toggle */}
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={visualEnabled}
                onChange={(e) => setVisualEnabled(e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">Visual</span>
            </label>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center space-x-4">
          <button
            onClick={startSynchronizedPlayback}
            disabled={!currentAudioPlayer || isPlaying}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-600 transition-colors"
          >
            {isPlaying ? 'Playing...' : 'Play Response'}
          </button>
          
          <button
            onClick={pausePlayback}
            disabled={!isPlaying}
            className="px-4 py-2 bg-yellow-500 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-yellow-600 transition-colors"
          >
            Pause
          </button>
          
          <button
            onClick={stopCurrentPlayback}
            disabled={!currentAudioPlayer}
            className="px-4 py-2 bg-red-500 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-red-600 transition-colors"
          >
            Stop
          </button>

          {/* Playback Speed */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-700">Speed:</label>
            <select
              value={playbackSpeed}
              onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              <option value={0.5}>0.5x</option>
              <option value={0.75}>0.75x</option>
              <option value={1.0}>1.0x</option>
              <option value={1.25}>1.25x</option>
              <option value={1.5}>1.5x</option>
            </select>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex items-center space-x-4 mt-4 text-sm text-gray-600">
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-green-500' : 'bg-gray-300'}`} />
            <span>Audio: {isPlaying ? 'Playing' : 'Stopped'}</span>
          </div>
          
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${isExecutingActions ? 'bg-blue-500' : 'bg-gray-300'}`} />
            <span>Visual: {isExecutingActions ? 'Animating' : 'Ready'}</span>
          </div>
          
          {currentStep >= 0 && (
            <div className="flex items-center space-x-1">
              <span>Step: {currentStep + 1}</span>
            </div>
          )}
        </div>
      </div>

      {/* Highlighted Text Display */}
      {highlightedText && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <h4 className="text-sm font-medium text-blue-800 mb-2">Current Explanation:</h4>
          <p className="text-blue-700">{highlightedText}</p>
        </div>
      )}

      {/* Whiteboard Container */}
      <div ref={whiteboardRef} className="whiteboard-container">
        <Whiteboard
          width={800}
          height={600}
          sessionId={sessionId}
          userId={userId}
          enableRealTimeSync={true}
          enableComputerVision={true}
          onCanvasReady={handleCanvasReady}
          className="border border-gray-300 rounded-lg"
        />
      </div>

      {/* Demonstration Info */}
      {currentDemonstration && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-4">
          <h4 className="text-sm font-medium text-gray-800 mb-2">Visual Demonstration:</h4>
          <p className="text-sm text-gray-600 mb-2">{currentDemonstration.title}</p>
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <span>Actions: {currentDemonstration.actions_count}</span>
            <span>Duration: {Math.round(currentDemonstration.total_duration_ms / 1000)}s</span>
            <span>Steps: {currentDemonstration.synchronized_text.length}</span>
          </div>
        </div>
      )}
    </div>
  );
};

// Extended Whiteboard component with canvas ready callback
interface ExtendedWhiteboardProps {
  width: number;
  height: number;
  sessionId: string;
  userId: string;
  enableRealTimeSync: boolean;
  enableComputerVision: boolean;
  onCanvasReady?: (canvas: Canvas) => void;
  className?: string;
}

const ExtendedWhiteboard: React.FC<ExtendedWhiteboardProps> = (props) => {
  const { onCanvasReady, ...whiteboardProps } = props;
  
  const handleCanvasInit = useCallback((canvas: Canvas) => {
    if (onCanvasReady) {
      onCanvasReady(canvas);
    }
  }, [onCanvasReady]);

  return (
    <Whiteboard
      {...whiteboardProps}
      // Note: You would need to modify the Whiteboard component to accept onCanvasReady
      // This is a placeholder for the integration
    />
  );
};