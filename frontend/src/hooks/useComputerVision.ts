/**
 * React Hook for Computer Vision functionality
 * 
 * Provides easy-to-use computer vision capabilities for React components
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  computerVisionService,
  CanvasAnalysisResult,
  DetectedObject,
  MathEquationResult,
  HandwritingResult,
  DiagramAnalysisResult
} from '../services/computerVision';

export interface UseComputerVisionOptions {
  autoAnalyze?: boolean;
  debounceDelay?: number;
  enableRealTimeAnalysis?: boolean;
}

export interface ComputerVisionState {
  isAnalyzing: boolean;
  lastAnalysis: CanvasAnalysisResult | null;
  detectedObjects: DetectedObject[];
  error: string | null;
  analysisHistory: CanvasAnalysisResult[];
}

export interface ComputerVisionActions {
  analyzeCanvas: (canvasData: string, sessionId?: string, subject?: string) => Promise<CanvasAnalysisResult>;
  recognizeEquations: (imageData: string) => Promise<MathEquationResult>;
  recognizeHandwriting: (imageData: string) => Promise<HandwritingResult>;
  analyzeDiagrams: (imageData: string) => Promise<DiagramAnalysisResult>;
  detectObjects: (canvasData: string) => Promise<DetectedObject[]>;
  uploadAndAnalyzeImage: (file: File) => Promise<any>;
  clearError: () => void;
  clearHistory: () => void;
  startRealTimeAnalysis: (canvas: HTMLCanvasElement | any) => void;
  stopRealTimeAnalysis: () => void;
}

export function useComputerVision(
  options: UseComputerVisionOptions = {}
): ComputerVisionState & ComputerVisionActions {
  const {
    autoAnalyze = false,
    debounceDelay = 1000,
    enableRealTimeAnalysis = false
  } = options;

  // State
  const [state, setState] = useState<ComputerVisionState>({
    isAnalyzing: false,
    lastAnalysis: null,
    detectedObjects: [],
    error: null,
    analysisHistory: []
  });

  // Refs for real-time analysis
  const realTimeIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | any>(null);

  // Update state helper
  const updateState = useCallback((updates: Partial<ComputerVisionState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    updateState({ error: null });
  }, [updateState]);

  // Clear history
  const clearHistory = useCallback(() => {
    updateState({ analysisHistory: [] });
  }, [updateState]);

  // Analyze canvas
  const analyzeCanvas = useCallback(async (
    canvasData: string,
    sessionId?: string,
    subject?: string
  ): Promise<CanvasAnalysisResult> => {
    try {
      updateState({ isAnalyzing: true, error: null });

      const result = await computerVisionService.analyzeCanvas(
        canvasData,
        sessionId,
        subject
      );

      updateState({
        isAnalyzing: false,
        lastAnalysis: result,
        analysisHistory: prev => [...prev.analysisHistory, result]
      });

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Analysis failed';
      updateState({
        isAnalyzing: false,
        error: errorMessage
      });
      throw error;
    }
  }, [updateState]);

  // Recognize equations
  const recognizeEquations = useCallback(async (
    imageData: string
  ): Promise<MathEquationResult> => {
    try {
      updateState({ isAnalyzing: true, error: null });

      const result = await computerVisionService.recognizeEquations(imageData);

      updateState({ isAnalyzing: false });
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Equation recognition failed';
      updateState({
        isAnalyzing: false,
        error: errorMessage
      });
      throw error;
    }
  }, [updateState]);

  // Recognize handwriting
  const recognizeHandwriting = useCallback(async (
    imageData: string
  ): Promise<HandwritingResult> => {
    try {
      updateState({ isAnalyzing: true, error: null });

      const result = await computerVisionService.recognizeHandwriting(imageData);

      updateState({ isAnalyzing: false });
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Handwriting recognition failed';
      updateState({
        isAnalyzing: false,
        error: errorMessage
      });
      throw error;
    }
  }, [updateState]);

  // Analyze diagrams
  const analyzeDiagrams = useCallback(async (
    imageData: string
  ): Promise<DiagramAnalysisResult> => {
    try {
      updateState({ isAnalyzing: true, error: null });

      const result = await computerVisionService.analyzeDiagrams(imageData);

      updateState({ isAnalyzing: false });
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Diagram analysis failed';
      updateState({
        isAnalyzing: false,
        error: errorMessage
      });
      throw error;
    }
  }, [updateState]);

  // Detect objects
  const detectObjects = useCallback(async (
    canvasData: string
  ): Promise<DetectedObject[]> => {
    try {
      updateState({ isAnalyzing: true, error: null });

      const result = await computerVisionService.detectObjects(canvasData);

      updateState({
        isAnalyzing: false,
        detectedObjects: result.objects
      });

      return result.objects;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Object detection failed';
      updateState({
        isAnalyzing: false,
        error: errorMessage
      });
      throw error;
    }
  }, [updateState]);

  // Upload and analyze image
  const uploadAndAnalyzeImage = useCallback(async (file: File): Promise<any> => {
    try {
      updateState({ isAnalyzing: true, error: null });

      const result = await computerVisionService.uploadAndAnalyzeImage(file);

      updateState({ isAnalyzing: false });
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Image upload and analysis failed';
      updateState({
        isAnalyzing: false,
        error: errorMessage
      });
      throw error;
    }
  }, [updateState]);

  // Start real-time analysis
  const startRealTimeAnalysis = useCallback((canvas: HTMLCanvasElement | any) => {
    if (!enableRealTimeAnalysis) return;

    canvasRef.current = canvas;

    // Clear existing interval
    if (realTimeIntervalRef.current) {
      clearInterval(realTimeIntervalRef.current);
    }

    // Start new interval
    realTimeIntervalRef.current = setInterval(async () => {
      if (!canvasRef.current) return;

      try {
        let canvasData: string;
        
        // Handle different canvas types
        if (canvasRef.current.toDataURL) {
          // HTML Canvas
          canvasData = canvasRef.current.toDataURL('image/png');
        } else if (canvasRef.current.toDataURL) {
          // Fabric.js Canvas
          canvasData = computerVisionService.extractFabricCanvasImage(canvasRef.current);
        } else {
          return;
        }

        // Analyze with debouncing
        await computerVisionService.analyzeCanvasDebounced(
          canvasData,
          (result) => {
            updateState({
              lastAnalysis: result,
              analysisHistory: prev => [...prev.analysisHistory, result]
            });
          },
          debounceDelay
        );
      } catch (error) {
        console.error('Real-time analysis error:', error);
      }
    }, debounceDelay);
  }, [enableRealTimeAnalysis, debounceDelay, updateState]);

  // Stop real-time analysis
  const stopRealTimeAnalysis = useCallback(() => {
    if (realTimeIntervalRef.current) {
      clearInterval(realTimeIntervalRef.current);
      realTimeIntervalRef.current = null;
    }
    canvasRef.current = null;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRealTimeAnalysis();
    };
  }, [stopRealTimeAnalysis]);

  return {
    // State
    ...state,
    
    // Actions
    analyzeCanvas,
    recognizeEquations,
    recognizeHandwriting,
    analyzeDiagrams,
    detectObjects,
    uploadAndAnalyzeImage,
    clearError,
    clearHistory,
    startRealTimeAnalysis,
    stopRealTimeAnalysis
  };
}

// Additional utility hooks

/**
 * Hook for analyzing canvas on demand
 */
export function useCanvasAnalysis() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<CanvasAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (canvas: HTMLCanvasElement | any) => {
    try {
      setIsAnalyzing(true);
      setError(null);

      let canvasData: string;
      if (canvas.toDataURL) {
        canvasData = canvas.toDataURL('image/png');
      } else {
        canvasData = computerVisionService.extractFabricCanvasImage(canvas);
      }

      const analysisResult = await computerVisionService.analyzeCanvas(canvasData);
      setResult(analysisResult);
      return analysisResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  return {
    analyze,
    isAnalyzing,
    result,
    error,
    clearError: () => setError(null)
  };
}

/**
 * Hook for equation recognition
 */
export function useEquationRecognition() {
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [equations, setEquations] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const recognize = useCallback(async (imageData: string) => {
    try {
      setIsRecognizing(true);
      setError(null);

      const result = await computerVisionService.recognizeEquations(imageData);
      setEquations(result.equations);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Recognition failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsRecognizing(false);
    }
  }, []);

  return {
    recognize,
    isRecognizing,
    equations,
    error,
    clearError: () => setError(null)
  };
}