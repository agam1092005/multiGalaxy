/**
 * Demo component to showcase audio capture functionality
 */
import React, { useState } from 'react';
import { io, Socket } from 'socket.io-client';
import AudioCapture from './AudioCapture';

const AudioDemo: React.FC = () => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [sessionId] = useState<string>('demo-session-123');
  const [isConnected, setIsConnected] = useState(false);
  const [transcriptions, setTranscriptions] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  const connectToServer = () => {
    try {
      const newSocket = io('http://localhost:8000', {
        transports: ['websocket'],
        autoConnect: true
      });

      newSocket.on('connect', () => {
        console.log('Connected to server');
        setIsConnected(true);
        
        // Join the demo session
        newSocket.emit('join_session', {
          session_id: sessionId,
          user_id: 'demo-user'
        });
      });

      newSocket.on('disconnect', () => {
        console.log('Disconnected from server');
        setIsConnected(false);
      });

      newSocket.on('error', (error: any) => {
        console.error('Socket error:', error);
        setErrors(prev => [...prev, `Socket error: ${error.error || error}`]);
      });

      setSocket(newSocket);
    } catch (error) {
      console.error('Failed to connect:', error);
      setErrors(prev => [...prev, `Connection failed: ${error}`]);
    }
  };

  const disconnect = () => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
      setIsConnected(false);
    }
  };

  const handleTranscription = (transcription: string) => {
    console.log('Received transcription:', transcription);
    setTranscriptions(prev => [...prev, transcription]);
  };

  const handleError = (error: string) => {
    console.error('Audio error:', error);
    setErrors(prev => [...prev, error]);
  };

  const clearLogs = () => {
    setTranscriptions([]);
    setErrors([]);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Audio Capture Demo
        </h1>
        
        <p className="text-gray-600 mb-6">
          This demo showcases the audio capture and processing functionality. 
          Connect to the WebSocket server and start recording to see real-time 
          speech-to-text transcription.
        </p>

        {/* Connection Controls */}
        <div className="flex items-center space-x-4 mb-6">
          {!isConnected ? (
            <button
              onClick={connectToServer}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
            >
              Connect to Server
            </button>
          ) : (
            <button
              onClick={disconnect}
              className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium transition-colors"
            >
              Disconnect
            </button>
          )}
          
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          <span className="text-sm text-gray-500">
            Session: {sessionId}
          </span>
        </div>

        {/* Audio Capture Component */}
        <AudioCapture
          socket={socket}
          sessionId={sessionId}
          isEnabled={isConnected}
          onTranscription={handleTranscription}
          onError={handleError}
        />
      </div>

      {/* Transcription Log */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Live Transcriptions
          </h2>
          <button
            onClick={clearLogs}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
          >
            Clear
          </button>
        </div>
        
        <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
          {transcriptions.length === 0 ? (
            <p className="text-gray-500 text-sm italic">
              No transcriptions yet. Start recording to see results here.
            </p>
          ) : (
            <div className="space-y-2">
              {transcriptions.map((transcription, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <span className="text-xs text-gray-400 mt-1">
                    {new Date().toLocaleTimeString()}
                  </span>
                  <p className="text-sm text-gray-900 flex-1">
                    {transcription}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error Log */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-red-900 mb-4">
            Errors
          </h2>
          <div className="space-y-2">
            {errors.map((error, index) => (
              <p key={index} className="text-sm text-red-800">
                {error}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-blue-900 mb-4">
          Instructions
        </h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
          <li>Make sure the backend server is running on localhost:8000</li>
          <li>Click "Connect to Server" to establish WebSocket connection</li>
          <li>Click "Initialize Audio" if audio capture is not ready</li>
          <li>Click "Start Recording" to begin audio capture</li>
          <li>Speak into your microphone - transcriptions will appear above</li>
          <li>Monitor audio quality indicators for optimal performance</li>
          <li>Click "Stop Recording" when finished</li>
        </ol>
      </div>
    </div>
  );
};

export default AudioDemo;