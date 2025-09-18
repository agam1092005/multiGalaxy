/**
 * Computer Vision Service for Multi-Galaxy-Note Frontend
 * 
 * Handles canvas content extraction, image processing, and communication
 * with the backend computer vision API.
 */

import { apiService } from './api';

// Types for computer vision responses
export interface CanvasAnalysisResult {
  text_content: string[];
  mathematical_equations: string[];
  diagrams: DiagramAnalysis[];
  handwriting_text: string;
  confidence_scores: ConfidenceScores;
  processing_time_ms: number;
}

export interface DiagramAnalysis {
  type: string;
  description: string;
  elements: string[];
  educational_concept?: string;
  complexity?: 'simple' | 'medium' | 'complex';
}

export interface ConfidenceScores {
  text_detection?: number;
  equation_recognition?: number;
  diagram_analysis?: number;
  handwriting_recognition?: number;
}

export interface DetectedObject {
  type: 'text' | 'equation' | 'diagram' | 'drawing';
  content: string;
  bounding_box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence: number;
}

export interface ObjectDetectionResult {
  objects: DetectedObject[];
  total_objects: number;
  processing_time_ms: number;
}

export interface MathEquationResult {
  equations: string[];
  count: number;
  processing_time_ms: number;
}

export interface HandwritingResult {
  text: string;
  character_count: number;
  processing_time_ms: number;
}

export interface DiagramAnalysisResult {
  diagrams: DiagramAnalysis[];
  count: number;
  processing_time_ms: number;
}

class ComputerVisionService {
  private readonly baseUrl = '/api/computer-vision';

  /**
   * Extract canvas content as base64 image data
   */
  extractCanvasImage(canvas: HTMLCanvasElement): string {
    try {
      // Convert canvas to base64 image data
      return canvas.toDataURL('image/png');
    } catch (error) {
      console.error('Error extracting canvas image:', error);
      throw new Error('Failed to extract canvas content');
    }
  }

  /**
   * Extract canvas content from Fabric.js canvas
   */
  extractFabricCanvasImage(fabricCanvas: any): string {
    try {
      // Use Fabric.js toDataURL method
      return fabricCanvas.toDataURL({
        format: 'png',
        quality: 1.0,
        multiplier: 1
      });
    } catch (error) {
      console.error('Error extracting Fabric canvas image:', error);
      throw new Error('Failed to extract Fabric canvas content');
    }
  }

  /**
   * Analyze complete canvas content
   */
  async analyzeCanvas(
    canvasData: string,
    sessionId?: string,
    subject?: string
  ): Promise<CanvasAnalysisResult> {
    try {
      const response = await apiService.post<CanvasAnalysisResult>(
        `${this.baseUrl}/analyze-canvas`,
        {
          canvas_data: canvasData,
          session_id: sessionId,
          subject: subject
        }
      );

      return response;
    } catch (error) {
      console.error('Error analyzing canvas:', error);
      throw new Error('Failed to analyze canvas content');
    }
  }

  /**
   * Recognize mathematical equations specifically
   */
  async recognizeEquations(imageData: string): Promise<MathEquationResult> {
    try {
      const response = await apiService.post<MathEquationResult>(
        `${this.baseUrl}/recognize-equations`,
        {
          image_data: imageData
        }
      );

      return response;
    } catch (error) {
      console.error('Error recognizing equations:', error);
      throw new Error('Failed to recognize mathematical equations');
    }
  }

  /**
   * Recognize handwritten text
   */
  async recognizeHandwriting(imageData: string): Promise<HandwritingResult> {
    try {
      const response = await apiService.post<HandwritingResult>(
        `${this.baseUrl}/recognize-handwriting`,
        {
          image_data: imageData
        }
      );

      return response;
    } catch (error) {
      console.error('Error recognizing handwriting:', error);
      throw new Error('Failed to recognize handwriting');
    }
  }

  /**
   * Analyze diagrams and drawings
   */
  async analyzeDiagrams(imageData: string): Promise<DiagramAnalysisResult> {
    try {
      const response = await apiService.post<DiagramAnalysisResult>(
        `${this.baseUrl}/analyze-diagrams`,
        {
          image_data: imageData
        }
      );

      return response;
    } catch (error) {
      console.error('Error analyzing diagrams:', error);
      throw new Error('Failed to analyze diagrams');
    }
  }

  /**
   * Detect objects with bounding boxes
   */
  async detectObjects(canvasData: string): Promise<ObjectDetectionResult> {
    try {
      const response = await apiService.post<ObjectDetectionResult>(
        `${this.baseUrl}/detect-objects`,
        {
          canvas_data: canvasData
        }
      );

      return response;
    } catch (error) {
      console.error('Error detecting objects:', error);
      throw new Error('Failed to detect objects');
    }
  }

  /**
   * Upload and analyze an image file
   */
  async uploadAndAnalyzeImage(file: File): Promise<any> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${this.baseUrl}/upload-image`, {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading and analyzing image:', error);
      throw new Error('Failed to upload and analyze image');
    }
  }

  /**
   * Process canvas region for specific analysis
   */
  async analyzeCanvasRegion(
    canvas: HTMLCanvasElement,
    region: { x: number; y: number; width: number; height: number }
  ): Promise<CanvasAnalysisResult> {
    try {
      // Create a temporary canvas for the region
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = region.width;
      tempCanvas.height = region.height;
      
      const tempCtx = tempCanvas.getContext('2d');
      if (!tempCtx) {
        throw new Error('Failed to get canvas context');
      }

      // Draw the region onto the temporary canvas
      tempCtx.drawImage(
        canvas,
        region.x, region.y, region.width, region.height,
        0, 0, region.width, region.height
      );

      // Extract and analyze the region
      const regionImageData = tempCanvas.toDataURL('image/png');
      return await this.analyzeCanvas(regionImageData);
    } catch (error) {
      console.error('Error analyzing canvas region:', error);
      throw new Error('Failed to analyze canvas region');
    }
  }

  /**
   * Batch process multiple canvas snapshots
   */
  async batchAnalyzeCanvasSnapshots(
    snapshots: string[]
  ): Promise<CanvasAnalysisResult[]> {
    try {
      const results = await Promise.all(
        snapshots.map(snapshot => this.analyzeCanvas(snapshot))
      );
      return results;
    } catch (error) {
      console.error('Error in batch analysis:', error);
      throw new Error('Failed to batch analyze canvas snapshots');
    }
  }

  /**
   * Get real-time analysis with debouncing
   */
  private analysisTimeout: NodeJS.Timeout | null = null;

  async analyzeCanvasDebounced(
    canvasData: string,
    callback: (result: CanvasAnalysisResult) => void,
    delay: number = 1000
  ): Promise<void> {
    // Clear existing timeout
    if (this.analysisTimeout) {
      clearTimeout(this.analysisTimeout);
    }

    // Set new timeout
    this.analysisTimeout = setTimeout(async () => {
      try {
        const result = await this.analyzeCanvas(canvasData);
        callback(result);
      } catch (error) {
        console.error('Error in debounced analysis:', error);
      }
    }, delay);
  }

  /**
   * Check service health
   */
  async checkHealth(): Promise<any> {
    try {
      const response = await apiService.get(`${this.baseUrl}/health`);
      return response;
    } catch (error) {
      console.error('Error checking computer vision service health:', error);
      throw new Error('Computer vision service is unavailable');
    }
  }

  /**
   * Convert analysis results to user-friendly format
   */
  formatAnalysisResults(result: CanvasAnalysisResult): string {
    const sections: string[] = [];

    if (result.text_content.length > 0) {
      sections.push(`**Text Content:**\n${result.text_content.join('\n')}`);
    }

    if (result.mathematical_equations.length > 0) {
      sections.push(`**Mathematical Equations:**\n${result.mathematical_equations.join('\n')}`);
    }

    if (result.handwriting_text) {
      sections.push(`**Handwritten Text:**\n${result.handwriting_text}`);
    }

    if (result.diagrams.length > 0) {
      const diagramDescriptions = result.diagrams.map(
        (diagram, index) => `${index + 1}. ${diagram.type}: ${diagram.description}`
      );
      sections.push(`**Diagrams:**\n${diagramDescriptions.join('\n')}`);
    }

    return sections.join('\n\n') || 'No content detected on the canvas.';
  }

  /**
   * Get confidence level description
   */
  getConfidenceDescription(confidence: number): string {
    if (confidence >= 0.9) return 'Very High';
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.7) return 'Medium';
    if (confidence >= 0.6) return 'Low';
    return 'Very Low';
  }
}

// Export singleton instance
export const computerVisionService = new ComputerVisionService();