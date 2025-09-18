/**
 * Tests for useComputerVision hook
 */

import { renderHook, act } from '@testing-library/react';
import { useComputerVision, useCanvasAnalysis, useEquationRecognition } from '../useComputerVision';
import { computerVisionService } from '../../services/computerVision';

// Mock the computer vision service
jest.mock('../../services/computerVision');
const mockComputerVisionService = computerVisionService as jest.Mocked<typeof computerVisionService>;

describe('useComputerVision', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useComputerVision());

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.lastAnalysis).toBe(null);
    expect(result.current.detectedObjects).toEqual([]);
    expect(result.current.error).toBe(null);
    expect(result.current.analysisHistory).toEqual([]);
  });

  it('should analyze canvas successfully', async () => {
    const mockAnalysisResult = {
      text_content: ['Hello World'],
      mathematical_equations: ['x + 2 = 5'],
      diagrams: [],
      handwriting_text: '',
      confidence_scores: { text_detection: 0.9 },
      processing_time_ms: 150
    };

    mockComputerVisionService.analyzeCanvas.mockResolvedValue(mockAnalysisResult);

    const { result } = renderHook(() => useComputerVision());

    await act(async () => {
      const analysisResult = await result.current.analyzeCanvas(
        'data:image/png;base64,test-data',
        'session-123',
        'math'
      );
      expect(analysisResult).toEqual(mockAnalysisResult);
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.lastAnalysis).toEqual(mockAnalysisResult);
    expect(result.current.analysisHistory).toHaveLength(1);
    expect(result.current.error).toBe(null);
  });

  it('should handle analysis errors', async () => {
    const errorMessage = 'Analysis failed';
    mockComputerVisionService.analyzeCanvas.mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useComputerVision());

    await act(async () => {
      try {
        await result.current.analyzeCanvas('invalid-data');
      } catch (error) {
        // Expected to throw
      }
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.error).toBe(errorMessage);
    expect(result.current.lastAnalysis).toBe(null);
  });

  it('should recognize equations successfully', async () => {
    const mockEquationResult = {
      equations: ['x + 2 = 5', 'y = mx + b'],
      count: 2,
      processing_time_ms: 100
    };

    mockComputerVisionService.recognizeEquations.mockResolvedValue(mockEquationResult);

    const { result } = renderHook(() => useComputerVision());

    await act(async () => {
      const equationResult = await result.current.recognizeEquations('data:image/png;base64,test-data');
      expect(equationResult).toEqual(mockEquationResult);
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should recognize handwriting successfully', async () => {
    const mockHandwritingResult = {
      text: 'This is handwritten text',
      character_count: 25,
      processing_time_ms: 120
    };

    mockComputerVisionService.recognizeHandwriting.mockResolvedValue(mockHandwritingResult);

    const { result } = renderHook(() => useComputerVision());

    await act(async () => {
      const handwritingResult = await result.current.recognizeHandwriting('data:image/png;base64,test-data');
      expect(handwritingResult).toEqual(mockHandwritingResult);
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should analyze diagrams successfully', async () => {
    const mockDiagramResult = {
      diagrams: [
        {
          type: 'rectangle',
          description: 'Red rectangle',
          elements: ['border'],
          educational_concept: 'geometry',
          complexity: 'simple' as const
        }
      ],
      count: 1,
      processing_time_ms: 180
    };

    mockComputerVisionService.analyzeDiagrams.mockResolvedValue(mockDiagramResult);

    const { result } = renderHook(() => useComputerVision());

    await act(async () => {
      const diagramResult = await result.current.analyzeDiagrams('data:image/png;base64,test-data');
      expect(diagramResult).toEqual(mockDiagramResult);
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should detect objects successfully', async () => {
    const mockObjectResult = {
      objects: [
        {
          type: 'text' as const,
          content: 'Hello World',
          bounding_box: { x: 10, y: 20, width: 100, height: 30 },
          confidence: 0.9
        }
      ],
      total_objects: 1,
      processing_time_ms: 200
    };

    mockComputerVisionService.detectObjects.mockResolvedValue(mockObjectResult);

    const { result } = renderHook(() => useComputerVision());

    await act(async () => {
      const objects = await result.current.detectObjects('data:image/png;base64,test-data');
      expect(objects).toEqual(mockObjectResult.objects);
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.detectedObjects).toEqual(mockObjectResult.objects);
    expect(result.current.error).toBe(null);
  });

  it('should upload and analyze image successfully', async () => {
    const mockFile = new File(['test'], 'test.png', { type: 'image/png' });
    const mockUploadResult = {
      filename: 'test.png',
      analysis: {
        text_content: ['Uploaded text'],
        mathematical_equations: [],
        diagrams: [],
        handwriting_text: '',
        confidence_scores: { text_detection: 0.8 }
      },
      processing_time_ms: 250
    };

    mockComputerVisionService.uploadAndAnalyzeImage.mockResolvedValue(mockUploadResult);

    const { result } = renderHook(() => useComputerVision());

    await act(async () => {
      const uploadResult = await result.current.uploadAndAnalyzeImage(mockFile);
      expect(uploadResult).toEqual(mockUploadResult);
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should clear error', () => {
    const { result } = renderHook(() => useComputerVision());

    act(() => {
      // Set an error first
      result.current.analyzeCanvas('invalid-data').catch(() => {});
    });

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBe(null);
  });

  it('should clear history', async () => {
    const mockAnalysisResult = {
      text_content: ['Test'],
      mathematical_equations: [],
      diagrams: [],
      handwriting_text: '',
      confidence_scores: {},
      processing_time_ms: 100
    };

    mockComputerVisionService.analyzeCanvas.mockResolvedValue(mockAnalysisResult);

    const { result } = renderHook(() => useComputerVision());

    // Add some history
    await act(async () => {
      await result.current.analyzeCanvas('data:image/png;base64,test-data');
    });

    expect(result.current.analysisHistory).toHaveLength(1);

    act(() => {
      result.current.clearHistory();
    });

    expect(result.current.analysisHistory).toHaveLength(0);
  });

  it('should handle real-time analysis', () => {
    const { result } = renderHook(() => 
      useComputerVision({ enableRealTimeAnalysis: true, debounceDelay: 100 })
    );

    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = jest.fn().mockReturnValue('data:image/png;base64,test-data');

    act(() => {
      result.current.startRealTimeAnalysis(mockCanvas);
    });

    // Real-time analysis should be started
    expect(mockCanvas.toDataURL).not.toHaveBeenCalled(); // Not called immediately due to interval

    act(() => {
      result.current.stopRealTimeAnalysis();
    });

    // Should stop without errors
  });
});

describe('useCanvasAnalysis', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should analyze canvas on demand', async () => {
    const mockAnalysisResult = {
      text_content: ['Canvas text'],
      mathematical_equations: [],
      diagrams: [],
      handwriting_text: '',
      confidence_scores: { text_detection: 0.85 },
      processing_time_ms: 120
    };

    mockComputerVisionService.analyzeCanvas.mockResolvedValue(mockAnalysisResult);

    const { result } = renderHook(() => useCanvasAnalysis());

    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = jest.fn().mockReturnValue('data:image/png;base64,test-data');

    await act(async () => {
      const analysisResult = await result.current.analyze(mockCanvas);
      expect(analysisResult).toEqual(mockAnalysisResult);
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.result).toEqual(mockAnalysisResult);
    expect(result.current.error).toBe(null);
  });

  it('should handle Fabric.js canvas', async () => {
    const mockAnalysisResult = {
      text_content: ['Fabric canvas text'],
      mathematical_equations: [],
      diagrams: [],
      handwriting_text: '',
      confidence_scores: { text_detection: 0.9 },
      processing_time_ms: 100
    };

    mockComputerVisionService.analyzeCanvas.mockResolvedValue(mockAnalysisResult);
    mockComputerVisionService.extractFabricCanvasImage.mockReturnValue('data:image/png;base64,fabric-data');

    const { result } = renderHook(() => useCanvasAnalysis());

    const mockFabricCanvas = {
      // No toDataURL method to simulate Fabric.js canvas
    };

    await act(async () => {
      const analysisResult = await result.current.analyze(mockFabricCanvas);
      expect(analysisResult).toEqual(mockAnalysisResult);
    });

    expect(mockComputerVisionService.extractFabricCanvasImage).toHaveBeenCalledWith(mockFabricCanvas);
    expect(result.current.result).toEqual(mockAnalysisResult);
  });

  it('should handle analysis errors', async () => {
    const errorMessage = 'Canvas analysis failed';
    mockComputerVisionService.analyzeCanvas.mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useCanvasAnalysis());

    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = jest.fn().mockReturnValue('data:image/png;base64,test-data');

    await act(async () => {
      try {
        await result.current.analyze(mockCanvas);
      } catch (error) {
        // Expected to throw
      }
    });

    expect(result.current.isAnalyzing).toBe(false);
    expect(result.current.error).toBe(errorMessage);
    expect(result.current.result).toBe(null);
  });

  it('should clear error', () => {
    const { result } = renderHook(() => useCanvasAnalysis());

    act(() => {
      // Simulate setting an error
      result.current.analyze({} as any).catch(() => {});
    });

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBe(null);
  });
});

describe('useEquationRecognition', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should recognize equations successfully', async () => {
    const mockEquationResult = {
      equations: ['x^2 + 2x + 1 = 0', '\\frac{dy}{dx} = 2x'],
      count: 2,
      processing_time_ms: 150
    };

    mockComputerVisionService.recognizeEquations.mockResolvedValue(mockEquationResult);

    const { result } = renderHook(() => useEquationRecognition());

    await act(async () => {
      const equationResult = await result.current.recognize('data:image/png;base64,equation-data');
      expect(equationResult).toEqual(mockEquationResult);
    });

    expect(result.current.isRecognizing).toBe(false);
    expect(result.current.equations).toEqual(mockEquationResult.equations);
    expect(result.current.error).toBe(null);
  });

  it('should handle recognition errors', async () => {
    const errorMessage = 'Equation recognition failed';
    mockComputerVisionService.recognizeEquations.mockRejectedValue(new Error(errorMessage));

    const { result } = renderHook(() => useEquationRecognition());

    await act(async () => {
      try {
        await result.current.recognize('invalid-data');
      } catch (error) {
        // Expected to throw
      }
    });

    expect(result.current.isRecognizing).toBe(false);
    expect(result.current.error).toBe(errorMessage);
    expect(result.current.equations).toEqual([]);
  });

  it('should clear error', () => {
    const { result } = renderHook(() => useEquationRecognition());

    act(() => {
      // Simulate setting an error
      result.current.recognize('invalid-data').catch(() => {});
    });

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBe(null);
  });
});