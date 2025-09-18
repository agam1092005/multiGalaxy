/**
 * Tests for ComputerVisionPanel component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ComputerVisionPanel } from '../ComputerVisionPanel';
import { useComputerVision } from '../../../hooks/useComputerVision';
import { computerVisionService } from '../../../services/computerVision';

// Mock the hooks and services
jest.mock('../../../hooks/useComputerVision');
jest.mock('../../../services/computerVision');

const mockUseComputerVision = useComputerVision as jest.MockedFunction<typeof useComputerVision>;
const mockComputerVisionService = computerVisionService as jest.Mocked<typeof computerVisionService>;

describe('ComputerVisionPanel', () => {
  const mockComputerVisionHook = {
    isAnalyzing: false,
    lastAnalysis: null,
    detectedObjects: [],
    error: null,
    analyzeCanvas: jest.fn(),
    recognizeEquations: jest.fn(),
    recognizeHandwriting: jest.fn(),
    detectObjects: jest.fn(),
    clearError: jest.fn(),
    analyzeDiagrams: jest.fn(),
    uploadAndAnalyzeImage: jest.fn(),
    clearHistory: jest.fn(),
    startRealTimeAnalysis: jest.fn(),
    stopRealTimeAnalysis: jest.fn(),
    analysisHistory: []
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseComputerVision.mockReturnValue(mockComputerVisionHook);
    mockComputerVisionService.extractFabricCanvasImage.mockReturnValue('data:image/png;base64,test-data');
  });

  it('should render computer vision panel', () => {
    render(<ComputerVisionPanel />);

    expect(screen.getByText('Computer Vision Analysis')).toBeInTheDocument();
    expect(screen.getByText('Analyze Canvas')).toBeInTheDocument();
    expect(screen.getByText('Detect Objects')).toBeInTheDocument();
    expect(screen.getByText('Find Equations')).toBeInTheDocument();
    expect(screen.getByText('Read Handwriting')).toBeInTheDocument();
  });

  it('should disable buttons when no canvas is provided', () => {
    render(<ComputerVisionPanel />);

    expect(screen.getByText('Analyze Canvas')).toBeDisabled();
    expect(screen.getByText('Detect Objects')).toBeDisabled();
    expect(screen.getByText('Find Equations')).toBeDisabled();
    expect(screen.getByText('Read Handwriting')).toBeDisabled();
  });

  it('should enable buttons when canvas is provided', () => {
    const mockCanvas = document.createElement('canvas');
    render(<ComputerVisionPanel canvas={mockCanvas} />);

    expect(screen.getByText('Analyze Canvas')).not.toBeDisabled();
    expect(screen.getByText('Detect Objects')).not.toBeDisabled();
    expect(screen.getByText('Find Equations')).not.toBeDisabled();
    expect(screen.getByText('Read Handwriting')).not.toBeDisabled();
  });

  it('should disable buttons when analyzing', () => {
    const mockCanvas = document.createElement('canvas');
    mockUseComputerVision.mockReturnValue({
      ...mockComputerVisionHook,
      isAnalyzing: true
    });

    render(<ComputerVisionPanel canvas={mockCanvas} />);

    expect(screen.getByRole('button', { name: /analyzing/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /analyzing/i })).toBeDisabled();
  });

  it('should handle canvas analysis', async () => {
    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = jest.fn().mockReturnValue('data:image/png;base64,test-data');
    
    const mockAnalysisResult = {
      text_content: ['Hello World'],
      mathematical_equations: ['x + 2 = 5'],
      diagrams: [],
      handwriting_text: '',
      confidence_scores: { text_detection: 0.9 },
      processing_time_ms: 150
    };

    mockComputerVisionHook.analyzeCanvas.mockResolvedValue(mockAnalysisResult);

    const onAnalysisComplete = jest.fn();
    render(
      <ComputerVisionPanel 
        canvas={mockCanvas} 
        sessionId="test-session"
        subject="math"
        onAnalysisComplete={onAnalysisComplete}
      />
    );

    fireEvent.click(screen.getByText('Analyze Canvas'));

    await waitFor(() => {
      expect(mockComputerVisionHook.analyzeCanvas).toHaveBeenCalledWith(
        'data:image/png;base64,test-data',
        'test-session',
        'math'
      );
      expect(onAnalysisComplete).toHaveBeenCalledWith(mockAnalysisResult);
    });
  });

  it('should handle Fabric.js canvas analysis', async () => {
    const mockFabricCanvas = {
      // Fabric.js canvas doesn't have toDataURL directly
    };

    mockComputerVisionHook.analyzeCanvas.mockResolvedValue({
      text_content: ['Fabric text'],
      mathematical_equations: [],
      diagrams: [],
      handwriting_text: '',
      confidence_scores: {},
      processing_time_ms: 100
    });

    render(<ComputerVisionPanel canvas={mockFabricCanvas} />);

    fireEvent.click(screen.getByText('Analyze Canvas'));

    await waitFor(() => {
      expect(mockComputerVisionService.extractFabricCanvasImage).toHaveBeenCalledWith(mockFabricCanvas);
      expect(mockComputerVisionHook.analyzeCanvas).toHaveBeenCalledWith('data:image/png;base64,test-data', undefined, undefined);
    });
  });

  it('should handle equation recognition', async () => {
    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = jest.fn().mockReturnValue('data:image/png;base64,test-data');

    render(<ComputerVisionPanel canvas={mockCanvas} />);

    fireEvent.click(screen.getByText('Find Equations'));

    await waitFor(() => {
      expect(mockComputerVisionHook.recognizeEquations).toHaveBeenCalledWith('data:image/png;base64,test-data');
    });
  });

  it('should handle handwriting recognition', async () => {
    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = jest.fn().mockReturnValue('data:image/png;base64,test-data');

    render(<ComputerVisionPanel canvas={mockCanvas} />);

    fireEvent.click(screen.getByText('Read Handwriting'));

    await waitFor(() => {
      expect(mockComputerVisionHook.recognizeHandwriting).toHaveBeenCalledWith('data:image/png;base64,test-data');
    });
  });

  it('should handle object detection', async () => {
    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = jest.fn().mockReturnValue('data:image/png;base64,test-data');

    render(<ComputerVisionPanel canvas={mockCanvas} />);

    fireEvent.click(screen.getByText('Detect Objects'));

    await waitFor(() => {
      expect(mockComputerVisionHook.detectObjects).toHaveBeenCalledWith('data:image/png;base64,test-data');
    });
  });

  it('should display analysis results', () => {
    const mockAnalysis = {
      text_content: ['Hello World', 'Sample text'],
      mathematical_equations: ['x + 2 = 5', 'y = mx + b'],
      diagrams: [
        {
          type: 'rectangle',
          description: 'Red rectangle',
          elements: ['border']
        }
      ],
      handwriting_text: 'Handwritten note',
      confidence_scores: {
        text_detection: 0.95,
        equation_recognition: 0.90,
        diagram_analysis: 0.85,
        handwriting_recognition: 0.88
      },
      processing_time_ms: 150
    };

    mockUseComputerVision.mockReturnValue({
      ...mockComputerVisionHook,
      lastAnalysis: mockAnalysis
    });

    render(<ComputerVisionPanel />);

    // Check text content
    expect(screen.getByText('Text Content')).toBeInTheDocument();
    expect(screen.getByText('Hello World')).toBeInTheDocument();
    expect(screen.getByText('Sample text')).toBeInTheDocument();

    // Check mathematical equations
    expect(screen.getByText('Mathematical Equations')).toBeInTheDocument();
    expect(screen.getByText('x + 2 = 5')).toBeInTheDocument();
    expect(screen.getByText('y = mx + b')).toBeInTheDocument();

    // Check handwriting
    expect(screen.getByText('Handwritten Text')).toBeInTheDocument();
    expect(screen.getByText('Handwritten note')).toBeInTheDocument();

    // Check diagrams
    expect(screen.getByText('Diagrams & Drawings')).toBeInTheDocument();
    expect(screen.getByText('rectangle')).toBeInTheDocument();
    expect(screen.getByText('Red rectangle')).toBeInTheDocument();

    // Check processing time
    expect(screen.getByText('Analysis completed in 150ms')).toBeInTheDocument();
  });

  it('should display detected objects', () => {
    const mockObjects = [
      {
        type: 'text' as const,
        content: 'Hello World',
        bounding_box: { x: 10, y: 20, width: 100, height: 30 },
        confidence: 0.9
      },
      {
        type: 'equation' as const,
        content: 'x + 2 = 5',
        bounding_box: { x: 50, y: 100, width: 80, height: 25 },
        confidence: 0.85
      }
    ];

    mockUseComputerVision.mockReturnValue({
      ...mockComputerVisionHook,
      detectedObjects: mockObjects
    });

    render(<ComputerVisionPanel />);

    // Switch to objects tab
    fireEvent.click(screen.getByText('Objects'));

    expect(screen.getByText('text')).toBeInTheDocument();
    expect(screen.getByText('Hello World')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('Position: (10, 20) Size: 100×30')).toBeInTheDocument();

    expect(screen.getByText('equation')).toBeInTheDocument();
    expect(screen.getByText('x + 2 = 5')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('should display confidence scores when enabled', () => {
    const mockAnalysis = {
      text_content: ['Hello World'],
      mathematical_equations: [],
      diagrams: [],
      handwriting_text: '',
      confidence_scores: {
        text_detection: 0.95
      },
      processing_time_ms: 100
    };

    mockUseComputerVision.mockReturnValue({
      ...mockComputerVisionHook,
      lastAnalysis: mockAnalysis
    });

    render(<ComputerVisionPanel />);

    // Enable confidence display
    fireEvent.click(screen.getByText('Show Confidence'));

    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText('Hide Confidence')).toBeInTheDocument();
  });

  it('should display error message', () => {
    const errorMessage = 'Analysis failed';
    mockUseComputerVision.mockReturnValue({
      ...mockComputerVisionHook,
      error: errorMessage
    });

    render(<ComputerVisionPanel />);

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByText('✕')).toBeInTheDocument();
  });

  it('should clear error when close button is clicked', () => {
    const errorMessage = 'Analysis failed';
    mockUseComputerVision.mockReturnValue({
      ...mockComputerVisionHook,
      error: errorMessage
    });

    render(<ComputerVisionPanel />);

    fireEvent.click(screen.getByText('✕'));

    expect(mockComputerVisionHook.clearError).toHaveBeenCalled();
  });

  it('should show loading indicator when analyzing', () => {
    mockUseComputerVision.mockReturnValue({
      ...mockComputerVisionHook,
      isAnalyzing: true
    });

    render(<ComputerVisionPanel />);

    expect(screen.getAllByText('Analyzing...')).toHaveLength(2); // Button and loading indicator
    expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
  });

  it('should show empty state when no analysis results', () => {
    render(<ComputerVisionPanel />);

    expect(screen.getByText('No analysis results yet. Click "Analyze Canvas" to start.')).toBeInTheDocument();
  });

  it('should show empty state when no objects detected', () => {
    render(<ComputerVisionPanel />);

    // Switch to objects tab
    fireEvent.click(screen.getByText('Objects'));

    expect(screen.getByText('No objects detected. Click "Detect Objects" to start.')).toBeInTheDocument();
  });

  it('should handle canvas analysis without canvas', async () => {
    render(<ComputerVisionPanel />);

    // The button should be disabled when no canvas is provided
    expect(screen.getByText('Analyze Canvas')).toBeDisabled();
  });

  it('should apply custom className', () => {
    const { container } = render(<ComputerVisionPanel className="custom-class" />);

    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('should switch between tabs', () => {
    render(<ComputerVisionPanel />);

    // Initially on Analysis tab
    expect(screen.getByText('No analysis results yet. Click "Analyze Canvas" to start.')).toBeInTheDocument();

    // Switch to Objects tab
    fireEvent.click(screen.getByText('Objects'));
    expect(screen.getByText('No objects detected. Click "Detect Objects" to start.')).toBeInTheDocument();

    // Switch back to Analysis tab
    fireEvent.click(screen.getByText('Analysis'));
    expect(screen.getByText('No analysis results yet. Click "Analyze Canvas" to start.')).toBeInTheDocument();
  });
});