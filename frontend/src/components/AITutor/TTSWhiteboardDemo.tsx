/**
 * Demo component for TTS and Whiteboard integration
 * 
 * Demonstrates the synchronized voice and visual explanations functionality
 */

import React, { useState, useCallback } from 'react';
import { textToSpeechService, AudioPlayer } from '../../services/textToSpeech';
import { whiteboardInteractionService, VisualDemonstration } from '../../services/whiteboardInteraction';

export const TTSWhiteboardDemo: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [currentAudio, setCurrentAudio] = useState<AudioPlayer | null>(null);
  const [currentDemo, setCurrentDemo] = useState<VisualDemonstration | null>(null);
  const [status, setStatus] = useState<string>('Ready');
  const [error, setError] = useState<string>('');

  /**
   * Test TTS synthesis
   */
  const testTTS = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setStatus('Synthesizing speech...');

    try {
      const response = await textToSpeechService.synthesizeEducationalResponse(
        "Great job! Let me show you how to solve this equation step by step.",
        "encouragement"
      );

      const player = textToSpeechService.createAudioPlayer(response.audio_url);
      setCurrentAudio(player);
      setStatus('Speech synthesized successfully');

      // Auto-play the audio
      await player.play();
      setStatus('Playing audio...');

      player.onEnded(() => {
        setStatus('Audio playback completed');
      });

    } catch (err) {
      setError(`TTS Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatus('TTS failed');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Test visual demonstration creation
   */
  const testVisualDemo = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setStatus('Creating visual demonstration...');

    try {
      const demo = await whiteboardInteractionService.createVisualDemonstration({
        problem_description: "Solve the equation 2x + 3 = 7",
        solution_steps: [
          "Subtract 3 from both sides: 2x + 3 - 3 = 7 - 3",
          "Simplify: 2x = 4",
          "Divide both sides by 2: x = 2"
        ],
        subject_area: "mathematics",
        canvas_width: 800,
        canvas_height: 600
      });

      setCurrentDemo(demo);
      setStatus(`Visual demonstration created with ${demo.actions_count} actions`);

    } catch (err) {
      setError(`Demo Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatus('Demo creation failed');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Test step-by-step solution
   */
  const testStepBySolution = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setStatus('Creating step-by-step solution...');

    try {
      const demo = await whiteboardInteractionService.createStepBySolution({
        equation: "3x - 6 = 9",
        solution_steps: [
          {
            equation: "3x - 6 + 6 = 9 + 6",
            explanation: "Add 6 to both sides",
            narration: "First, we add 6 to both sides of the equation"
          },
          {
            equation: "3x = 15",
            explanation: "Simplify both sides",
            narration: "Now we have 3x equals 15"
          },
          {
            equation: "x = 5",
            explanation: "Divide both sides by 3",
            narration: "Finally, divide both sides by 3 to get x equals 5"
          }
        ],
        canvas_width: 800,
        canvas_height: 600
      });

      setCurrentDemo(demo);
      setStatus(`Step-by-step solution created with ${demo.actions_count} actions`);

    } catch (err) {
      setError(`Solution Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatus('Solution creation failed');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Test synchronized playback
   */
  const testSynchronizedPlayback = useCallback(async () => {
    if (!currentDemo) {
      setError('No demonstration available. Create a demo first.');
      return;
    }

    setIsLoading(true);
    setError('');
    setStatus('Starting synchronized playback...');

    try {
      // First synthesize the narration
      const narrationText = currentDemo.synchronized_text
        .map(item => item.text)
        .join(' ');

      const ttsResponse = await textToSpeechService.synthesizeEducationalResponse(
        narrationText,
        "explanation"
      );

      // Create synchronized player
      const player = textToSpeechService.createSynchronizedPlayback(
        ttsResponse.audio_url,
        currentDemo.synchronized_text,
        (text, stepIndex) => {
          setStatus(`Playing step ${stepIndex + 1}: ${text.substring(0, 50)}...`);
        }
      );

      setCurrentAudio(player);
      await player.play();

      player.onEnded(() => {
        setStatus('Synchronized playback completed');
      });

    } catch (err) {
      setError(`Playback Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setStatus('Synchronized playback failed');
    } finally {
      setIsLoading(false);
    }
  }, [currentDemo]);

  /**
   * Stop current audio
   */
  const stopAudio = useCallback(() => {
    if (currentAudio) {
      currentAudio.stop();
      setCurrentAudio(null);
      setStatus('Audio stopped');
    }
  }, [currentAudio]);

  /**
   * Clear current demo
   */
  const clearDemo = useCallback(async () => {
    if (currentDemo) {
      try {
        await whiteboardInteractionService.clearDemonstration(currentDemo.demonstration_id);
        setCurrentDemo(null);
        setStatus('Demonstration cleared');
      } catch (err) {
        setError(`Clear Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }
  }, [currentDemo]);

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        TTS & Whiteboard Integration Demo
      </h2>

      {/* Status Display */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Status:</span>
          <span className={`text-sm ${isLoading ? 'text-blue-600' : 'text-green-600'}`}>
            {status}
          </span>
        </div>
        
        {error && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Control Buttons */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <button
          onClick={testTTS}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          Test TTS
        </button>

        <button
          onClick={testVisualDemo}
          disabled={isLoading}
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          Create Demo
        </button>

        <button
          onClick={testStepBySolution}
          disabled={isLoading}
          className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          Step Solution
        </button>

        <button
          onClick={testSynchronizedPlayback}
          disabled={isLoading || !currentDemo}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          Sync Play
        </button>
      </div>

      {/* Audio Controls */}
      {currentAudio && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="text-lg font-medium text-blue-900 mb-2">Audio Controls</h3>
          <div className="flex items-center space-x-4">
            <button
              onClick={stopAudio}
              className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
            >
              Stop Audio
            </button>
            <span className="text-sm text-blue-700">
              Audio player active
            </span>
          </div>
        </div>
      )}

      {/* Demo Information */}
      {currentDemo && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <h3 className="text-lg font-medium text-green-900 mb-2">Current Demonstration</h3>
          <div className="space-y-2 text-sm text-green-800">
            <div><strong>Title:</strong> {currentDemo.title}</div>
            <div><strong>Description:</strong> {currentDemo.description}</div>
            <div><strong>Actions:</strong> {currentDemo.actions_count}</div>
            <div><strong>Duration:</strong> {Math.round(currentDemo.total_duration_ms / 1000)}s</div>
            <div><strong>Steps:</strong> {currentDemo.synchronized_text.length}</div>
          </div>
          <button
            onClick={clearDemo}
            className="mt-2 px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
          >
            Clear Demo
          </button>
        </div>
      )}

      {/* Service Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-gray-50 rounded-lg">
          <h3 className="text-lg font-medium text-gray-900 mb-2">TTS Service</h3>
          <div className="space-y-1 text-sm text-gray-600">
            <div>Supported: {textToSpeechService.isSupported() ? '✅' : '❌'}</div>
            <div>Voice Presets: Available</div>
            <div>Audio Formats: MP3, WAV, OGG</div>
          </div>
        </div>

        <div className="p-4 bg-gray-50 rounded-lg">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Whiteboard Service</h3>
          <div className="space-y-1 text-sm text-gray-600">
            <div>Drawing Actions: Available</div>
            <div>Animations: Supported</div>
            <div>Templates: Mathematics, Science</div>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <h3 className="text-lg font-medium text-yellow-900 mb-2">Instructions</h3>
        <ol className="list-decimal list-inside space-y-1 text-sm text-yellow-800">
          <li>Click "Test TTS" to synthesize and play educational speech</li>
          <li>Click "Create Demo" to generate a visual demonstration</li>
          <li>Click "Step Solution" to create a step-by-step equation solution</li>
          <li>Click "Sync Play" to test synchronized audio and visual playback</li>
        </ol>
      </div>
    </div>
  );
};