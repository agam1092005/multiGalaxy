/**
 * Computer Vision Panel Component
 * 
 * Provides a UI panel for computer vision analysis results and controls
 */

import React, { useState, useCallback } from 'react';
import { useComputerVision } from '../../hooks/useComputerVision';
import {
  CanvasAnalysisResult,
  DetectedObject,
  computerVisionService
} from '../../services/computerVision';

interface ComputerVisionPanelProps {
  canvas?: HTMLCanvasElement | any;
  sessionId?: string;
  subject?: string;
  onAnalysisComplete?: (result: CanvasAnalysisResult) => void;
  className?: string;
}

export const ComputerVisionPanel: React.FC<ComputerVisionPanelProps> = ({
  canvas,
  sessionId,
  subject,
  onAnalysisComplete,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState<'analysis' | 'objects' | 'equations' | 'handwriting'>('analysis');
  const [showConfidence, setShowConfidence] = useState(false);

  const {
    isAnalyzing,
    lastAnalysis,
    detectedObjects,
    error,
    analyzeCanvas,
    recognizeEquations,
    recognizeHandwriting,
    detectObjects,
    clearError
  } = useComputerVision();



  // Handle canvas analysis
  const handleAnalyzeCanvas = useCallback(async () => {
    if (!canvas) {
      alert('No canvas available for analysis');
      return;
    }

    try {
      let canvasData: string;
      
      if (canvas.toDataURL) {
        canvasData = canvas.toDataURL('image/png');
      } else {
        canvasData = computerVisionService.extractFabricCanvasImage(canvas);
      }

      const result = await analyzeCanvas(canvasData, sessionId, subject);
      
      if (onAnalysisComplete) {
        onAnalysisComplete(result);
      }
    } catch (error) {
      console.error('Analysis failed:', error);
    }
  }, [canvas, sessionId, subject, analyzeCanvas, onAnalysisComplete]);

  // Handle equation recognition
  const handleRecognizeEquations = useCallback(async () => {
    if (!canvas) return;

    try {
      let canvasData: string;
      
      if (canvas.toDataURL) {
        canvasData = canvas.toDataURL('image/png');
      } else {
        canvasData = computerVisionService.extractFabricCanvasImage(canvas);
      }

      await recognizeEquations(canvasData);
    } catch (error) {
      console.error('Equation recognition failed:', error);
    }
  }, [canvas, recognizeEquations]);

  // Handle handwriting recognition
  const handleRecognizeHandwriting = useCallback(async () => {
    if (!canvas) return;

    try {
      let canvasData: string;
      
      if (canvas.toDataURL) {
        canvasData = canvas.toDataURL('image/png');
      } else {
        canvasData = computerVisionService.extractFabricCanvasImage(canvas);
      }

      await recognizeHandwriting(canvasData);
    } catch (error) {
      console.error('Handwriting recognition failed:', error);
    }
  }, [canvas, recognizeHandwriting]);

  // Handle object detection
  const handleDetectObjects = useCallback(async () => {
    if (!canvas) return;

    try {
      let canvasData: string;
      
      if (canvas.toDataURL) {
        canvasData = canvas.toDataURL('image/png');
      } else {
        canvasData = computerVisionService.extractFabricCanvasImage(canvas);
      }

      await detectObjects(canvasData);
    } catch (error) {
      console.error('Object detection failed:', error);
    }
  }, [canvas, detectObjects]);

  // Render confidence score
  const renderConfidenceScore = (score: number) => {
    const percentage = Math.round(score * 100);
    const color = score >= 0.8 ? 'text-green-600' : score >= 0.6 ? 'text-yellow-600' : 'text-red-600';
    
    return (
      <span className={`text-sm ${color} font-medium`}>
        {percentage}%
      </span>
    );
  };

  // Render analysis results
  const renderAnalysisResults = () => {
    if (!lastAnalysis) {
      return (
        <div className="text-gray-500 text-center py-8">
          No analysis results yet. Click "Analyze Canvas" to start.
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Text Content */}
        {lastAnalysis.text_content.length > 0 && (
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-medium text-blue-900">Text Content</h4>
              {showConfidence && lastAnalysis.confidence_scores.text_detection && (
                renderConfidenceScore(lastAnalysis.confidence_scores.text_detection)
              )}
            </div>
            <ul className="space-y-1">
              {lastAnalysis.text_content.map((text, index) => (
                <li key={index} className="text-sm text-blue-800 bg-white p-2 rounded">
                  {text}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Mathematical Equations */}
        {lastAnalysis.mathematical_equations.length > 0 && (
          <div className="bg-green-50 p-3 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-medium text-green-900">Mathematical Equations</h4>
              {showConfidence && lastAnalysis.confidence_scores.equation_recognition && (
                renderConfidenceScore(lastAnalysis.confidence_scores.equation_recognition)
              )}
            </div>
            <ul className="space-y-1">
              {lastAnalysis.mathematical_equations.map((equation, index) => (
                <li key={index} className="text-sm text-green-800 bg-white p-2 rounded font-mono">
                  {equation}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Handwriting */}
        {lastAnalysis.handwriting_text && (
          <div className="bg-purple-50 p-3 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-medium text-purple-900">Handwritten Text</h4>
              {showConfidence && lastAnalysis.confidence_scores.handwriting_recognition && (
                renderConfidenceScore(lastAnalysis.confidence_scores.handwriting_recognition)
              )}
            </div>
            <div className="text-sm text-purple-800 bg-white p-2 rounded">
              {lastAnalysis.handwriting_text}
            </div>
          </div>
        )}

        {/* Diagrams */}
        {lastAnalysis.diagrams.length > 0 && (
          <div className="bg-orange-50 p-3 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-medium text-orange-900">Diagrams & Drawings</h4>
              {showConfidence && lastAnalysis.confidence_scores.diagram_analysis && (
                renderConfidenceScore(lastAnalysis.confidence_scores.diagram_analysis)
              )}
            </div>
            <ul className="space-y-2">
              {lastAnalysis.diagrams.map((diagram, index) => (
                <li key={index} className="text-sm text-orange-800 bg-white p-2 rounded">
                  <div className="font-medium">{diagram.type}</div>
                  <div className="text-xs text-gray-600 mt-1">{diagram.description}</div>
                  {diagram.elements && diagram.elements.length > 0 && (
                    <div className="text-xs text-gray-500 mt-1">
                      Elements: {diagram.elements.join(', ')}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Processing Time */}
        <div className="text-xs text-gray-500 text-center">
          Analysis completed in {lastAnalysis.processing_time_ms.toFixed(0)}ms
        </div>
      </div>
    );
  };

  // Render detected objects
  const renderDetectedObjects = () => {
    if (detectedObjects.length === 0) {
      return (
        <div className="text-gray-500 text-center py-8">
          No objects detected. Click "Detect Objects" to start.
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {detectedObjects.map((obj, index) => (
          <div key={index} className="bg-gray-50 p-3 rounded-lg">
            <div className="flex justify-between items-start mb-2">
              <span className="font-medium text-gray-900 capitalize">{obj.type}</span>
              <span className="text-sm text-gray-600">
                {Math.round(obj.confidence * 100)}%
              </span>
            </div>
            <div className="text-sm text-gray-700 mb-2">{obj.content}</div>
            <div className="text-xs text-gray-500">
              Position: ({obj.bounding_box.x}, {obj.bounding_box.y}) 
              Size: {obj.bounding_box.width}×{obj.bounding_box.height}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className={`computer-vision-panel bg-white border border-gray-300 rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Computer Vision Analysis</h3>
          <button
            onClick={() => setShowConfidence(!showConfidence)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showConfidence ? 'Hide' : 'Show'} Confidence
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 border-b border-gray-200">
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleAnalyzeCanvas}
            disabled={isAnalyzing || !canvas}
            className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze Canvas'}
          </button>
          <button
            onClick={handleDetectObjects}
            disabled={isAnalyzing || !canvas}
            className="px-3 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
          >
            Detect Objects
          </button>
          <button
            onClick={handleRecognizeEquations}
            disabled={isAnalyzing || !canvas}
            className="px-3 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
          >
            Find Equations
          </button>
          <button
            onClick={handleRecognizeHandwriting}
            disabled={isAnalyzing || !canvas}
            className="px-3 py-2 bg-orange-500 text-white rounded-md hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
          >
            Read Handwriting
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-red-800 text-sm">{error}</span>
            <button
              onClick={clearError}
              className="text-red-600 hover:text-red-800 text-sm"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 px-4">
          {[
            { id: 'analysis', label: 'Analysis' },
            { id: 'objects', label: 'Objects' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="p-4 max-h-96 overflow-y-auto">
        {activeTab === 'analysis' && renderAnalysisResults()}
        {activeTab === 'objects' && renderDetectedObjects()}
      </div>

      {/* Loading Indicator */}
      {isAnalyzing && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center">
          <div className="flex items-center space-x-2" role="status">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
            <span className="text-gray-700">Analyzing...</span>
          </div>
        </div>
      )}
    </div>
  );
};