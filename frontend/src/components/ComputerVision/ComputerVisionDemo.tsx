/**
 * Computer Vision Demo Component
 * 
 * A demo component to showcase computer vision functionality
 */

import React, { useState, useRef } from 'react';
import { Whiteboard } from '../Whiteboard/Whiteboard';
import { ComputerVisionPanel } from './ComputerVisionPanel';
import { CanvasAnalysisResult } from '../../services/computerVision';

export const ComputerVisionDemo: React.FC = () => {
  const [analysisResults, setAnalysisResults] = useState<CanvasAnalysisResult[]>([]);
  const [sessionId] = useState(`demo-session-${Date.now()}`);
  const whiteboardRef = useRef<any>(null);

  const handleAnalysisComplete = (result: CanvasAnalysisResult) => {
    setAnalysisResults(prev => [...prev, result]);
    console.log('Analysis completed:', result);
  };

  const clearResults = () => {
    setAnalysisResults([]);
  };

  return (
    <div className="computer-vision-demo p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Computer Vision Demo
          </h1>
          <p className="text-gray-600">
            Draw, write, or create diagrams on the whiteboard and use the computer vision panel 
            to analyze the content. The AI can recognize text, mathematical equations, diagrams, 
            and handwriting.
          </p>
        </div>

        {/* Demo Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-blue-900 mb-2">Try these examples:</h3>
          <ul className="text-blue-800 text-sm space-y-1">
            <li>• Write some text or equations like "x + 2 = 5" or "E = mc²"</li>
            <li>• Draw geometric shapes like rectangles, circles, or triangles</li>
            <li>• Create diagrams or flowcharts</li>
            <li>• Write in cursive or print handwriting</li>
            <li>• Mix different types of content together</li>
          </ul>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Whiteboard */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Interactive Whiteboard
              </h2>
              <Whiteboard
                ref={whiteboardRef}
                width={800}
                height={600}
                enableComputerVision={true}
                sessionId={sessionId}
                subject="demo"
                onAnalysisComplete={handleAnalysisComplete}
                className="w-full"
              />
            </div>
          </div>

          {/* Computer Vision Panel */}
          <div className="lg:col-span-1">
            <ComputerVisionPanel
              canvas={whiteboardRef.current}
              sessionId={sessionId}
              subject="demo"
              onAnalysisComplete={handleAnalysisComplete}
              className="sticky top-6"
            />
          </div>
        </div>

        {/* Analysis History */}
        {analysisResults.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                Analysis History ({analysisResults.length})
              </h2>
              <button
                onClick={clearResults}
                className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors"
              >
                Clear History
              </button>
            </div>
            
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {analysisResults.map((result, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">
                      Analysis #{analysisResults.length - index}
                    </span>
                    <span className="text-xs text-gray-500">
                      {result.processing_time_ms.toFixed(0)}ms
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                    {/* Text Content */}
                    <div>
                      <h4 className="font-medium text-gray-700 mb-1">Text</h4>
                      {result.text_content.length > 0 ? (
                        <ul className="text-gray-600 space-y-1">
                          {result.text_content.map((text, i) => (
                            <li key={i} className="truncate" title={text}>
                              "{text}"
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-gray-400">None detected</span>
                      )}
                    </div>

                    {/* Equations */}
                    <div>
                      <h4 className="font-medium text-gray-700 mb-1">Equations</h4>
                      {result.mathematical_equations.length > 0 ? (
                        <ul className="text-gray-600 space-y-1">
                          {result.mathematical_equations.map((eq, i) => (
                            <li key={i} className="truncate font-mono text-xs" title={eq}>
                              {eq}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-gray-400">None detected</span>
                      )}
                    </div>

                    {/* Handwriting */}
                    <div>
                      <h4 className="font-medium text-gray-700 mb-1">Handwriting</h4>
                      {result.handwriting_text ? (
                        <p className="text-gray-600 text-xs truncate" title={result.handwriting_text}>
                          "{result.handwriting_text}"
                        </p>
                      ) : (
                        <span className="text-gray-400">None detected</span>
                      )}
                    </div>

                    {/* Diagrams */}
                    <div>
                      <h4 className="font-medium text-gray-700 mb-1">Diagrams</h4>
                      {result.diagrams.length > 0 ? (
                        <ul className="text-gray-600 space-y-1">
                          {result.diagrams.map((diagram, i) => (
                            <li key={i} className="truncate text-xs" title={diagram.description}>
                              {diagram.type}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-gray-400">None detected</span>
                      )}
                    </div>
                  </div>

                  {/* Confidence Scores */}
                  {Object.keys(result.confidence_scores).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <h4 className="font-medium text-gray-700 mb-2 text-xs">Confidence Scores</h4>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(result.confidence_scores).map(([key, score]) => (
                          <span
                            key={key}
                            className={`px-2 py-1 rounded text-xs ${
                              score >= 0.8
                                ? 'bg-green-100 text-green-800'
                                : score >= 0.6
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {key.replace('_', ' ')}: {Math.round(score * 100)}%
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>
            This demo showcases the computer vision capabilities powered by Google Gemini Pro Vision API.
            <br />
            The AI can analyze multimodal content including text, equations, diagrams, and handwriting.
          </p>
        </div>
      </div>
    </div>
  );
};