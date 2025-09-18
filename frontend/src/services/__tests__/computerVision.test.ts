/**
 * Tests for Computer Vision Service
 */

import { computerVisionService } from '../computerVision';
import { apiService } from '../api';

// Mock the API service
jest.mock('../api', () => ({
  apiService: {
    post: jest.fn(),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn()
  }
}));

const mockApiService = apiService as jest.Mocked<typeof apiService>;

describe('ComputerVisionService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('extractCanvasImage', () => {
    it('should extract canvas image as base64 data URL', () => {
      // Create a mock canvas
      const mockCanvas = document.createElement('canvas');
      mockCanvas.width = 100;
      mockCanvas.height = 100;
      
      // Mock toDataURL
      const mockDataURL = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==';
      jest.spyOn(mockCanvas, 'toDataURL').mockReturnValue(mockDataURL);

      const result = computerVisionService.extractCanvasImage(mockCanvas);
      
      expect(result).toBe(mockDataURL);
      expect(mockCanvas.toDataURL).toHaveBeenCalledWith('image/png');
    });

    it('should throw error when canvas extraction fails', () => {
      const mockCanvas = document.createElement('canvas');
      jest.spyOn(mockCanvas, 'toDataURL').mockImplementation(() => {
        throw new Error('Canvas extraction failed');
      });

      expect(() => {
        computerVisionService.extractCanvasImage(mockCanvas);
      }).toThrow('Failed to extract canvas content');
    });
  });

  describe('extractFabricCanvasImage', () => {
    it('should extract Fabric.js canvas image', () => {
      const mockFabricCanvas = {
        toDataURL: jest.fn().mockReturnValue('data:image/png;base64,test-data')
      };

      const result = computerVisionService.extractFabricCanvasImage(mockFabricCanvas);
      
      expect(result).toBe('data:image/png;base64,test-data');
      expect(mockFabricCanvas.toDataURL).toHaveBeenCalledWith({
        format: 'png',
        quality: 1.0,
        multiplier: 1
      });
    });

    it('should throw error when Fabric canvas extraction fails', () => {
      const mockFabricCanvas = {
        toDataURL: jest.fn().mockImplementation(() => {
          throw new Error('Fabric extraction failed');
        })
      };

      expect(() => {
        computerVisionService.extractFabricCanvasImage(mockFabricCanvas);
      }).toThrow('Failed to extract Fabric canvas content');
    });
  });

  describe('analyzeCanvas', () => {
    it('should analyze canvas content successfully', async () => {
      const mockResponse = {
        text_content: ['Hello World', 'Sample text'],
        mathematical_equations: ['x + 2 = 5'],
        diagrams: [{ type: 'rectangle', description: 'Red rectangle', elements: ['border'] }],
        handwriting_text: 'Handwritten note',
        confidence_scores: { text_detection: 0.95 },
        processing_time_ms: 150
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await computerVisionService.analyzeCanvas(
        'data:image/png;base64,test-data',
        'session-123',
        'math'
      );

      expect(result).toEqual(mockResponse);
      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/computer-vision/analyze-canvas',
        {
          canvas_data: 'data:image/png;base64,test-data',
          session_id: 'session-123',
          subject: 'math'
        }
      );
    });

    it('should handle analysis errors', async () => {
      mockApiService.post.mockRejectedValue(new Error('API Error'));

      await expect(
        computerVisionService.analyzeCanvas('invalid-data')
      ).rejects.toThrow('Failed to analyze canvas content');
    });
  });

  describe('recognizeEquations', () => {
    it('should recognize mathematical equations', async () => {
      const mockResponse = {
        equations: ['x + 2 = 5', 'y = mx + b'],
        count: 2,
        processing_time_ms: 100
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await computerVisionService.recognizeEquations('data:image/png;base64,test-data');

      expect(result).toEqual(mockResponse);
      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/computer-vision/recognize-equations',
        { image_data: 'data:image/png;base64,test-data' }
      );
    });

    it('should handle equation recognition errors', async () => {
      mockApiService.post.mockRejectedValue(new Error('Recognition failed'));

      await expect(
        computerVisionService.recognizeEquations('invalid-data')
      ).rejects.toThrow('Failed to recognize mathematical equations');
    });
  });

  describe('recognizeHandwriting', () => {
    it('should recognize handwritten text', async () => {
      const mockResponse = {
        text: 'This is handwritten text',
        character_count: 25,
        processing_time_ms: 120
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await computerVisionService.recognizeHandwriting('data:image/png;base64,test-data');

      expect(result).toEqual(mockResponse);
      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/computer-vision/recognize-handwriting',
        { image_data: 'data:image/png;base64,test-data' }
      );
    });

    it('should handle handwriting recognition errors', async () => {
      mockApiService.post.mockRejectedValue(new Error('Handwriting recognition failed'));

      await expect(
        computerVisionService.recognizeHandwriting('invalid-data')
      ).rejects.toThrow('Failed to recognize handwriting');
    });
  });

  describe('analyzeDiagrams', () => {
    it('should analyze diagrams and drawings', async () => {
      const mockResponse = {
        diagrams: [
          {
            type: 'geometric_shape',
            description: 'Rectangle with red border',
            elements: ['rectangle', 'border'],
            educational_concept: 'geometry',
            complexity: 'simple'
          }
        ],
        count: 1,
        processing_time_ms: 180
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await computerVisionService.analyzeDiagrams('data:image/png;base64,test-data');

      expect(result).toEqual(mockResponse);
      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/computer-vision/analyze-diagrams',
        { image_data: 'data:image/png;base64,test-data' }
      );
    });

    it('should handle diagram analysis errors', async () => {
      mockApiService.post.mockRejectedValue(new Error('Diagram analysis failed'));

      await expect(
        computerVisionService.analyzeDiagrams('invalid-data')
      ).rejects.toThrow('Failed to analyze diagrams');
    });
  });

  describe('detectObjects', () => {
    it('should detect objects with bounding boxes', async () => {
      const mockResponse = {
        objects: [
          {
            type: 'text',
            content: 'Hello World',
            bounding_box: { x: 10, y: 20, width: 100, height: 30 },
            confidence: 0.9
          }
        ],
        total_objects: 1,
        processing_time_ms: 200
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const result = await computerVisionService.detectObjects('data:image/png;base64,test-data');

      expect(result).toEqual(mockResponse);
      expect(mockApiService.post).toHaveBeenCalledWith(
        '/api/computer-vision/detect-objects',
        { canvas_data: 'data:image/png;base64,test-data' }
      );
    });

    it('should handle object detection errors', async () => {
      mockApiService.post.mockRejectedValue(new Error('Object detection failed'));

      await expect(
        computerVisionService.detectObjects('invalid-data')
      ).rejects.toThrow('Failed to detect objects');
    });
  });

  describe('uploadAndAnalyzeImage', () => {
    it('should upload and analyze image file', async () => {
      const mockFile = new File(['test'], 'test.png', { type: 'image/png' });
      const mockResponse = {
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

      // Mock fetch
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse)
      } as any);

      // Mock localStorage
      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: jest.fn().mockReturnValue('test-token')
        }
      });

      const result = await computerVisionService.uploadAndAnalyzeImage(mockFile);

      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        '/api/computer-vision/upload-image',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Authorization': 'Bearer test-token'
          }
        })
      );
    });

    it('should handle upload errors', async () => {
      const mockFile = new File(['test'], 'test.png', { type: 'image/png' });

      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 400
      } as any);

      await expect(
        computerVisionService.uploadAndAnalyzeImage(mockFile)
      ).rejects.toThrow('Failed to upload and analyze image');
    });
  });

  describe('analyzeCanvasRegion', () => {
    it('should analyze specific canvas region', async () => {
      const mockCanvas = document.createElement('canvas');
      mockCanvas.width = 400;
      mockCanvas.height = 300;

      // Mock canvas context
      const mockContext = {
        drawImage: jest.fn()
      };
      jest.spyOn(document, 'createElement').mockReturnValue({
        width: 0,
        height: 0,
        getContext: jest.fn().mockReturnValue(mockContext),
        toDataURL: jest.fn().mockReturnValue('data:image/png;base64,region-data')
      } as any);

      const mockResponse = {
        text_content: ['Region text'],
        mathematical_equations: [],
        diagrams: [],
        handwriting_text: '',
        confidence_scores: { text_detection: 0.85 },
        processing_time_ms: 100
      };

      mockApiService.post.mockResolvedValue(mockResponse);

      const region = { x: 50, y: 50, width: 200, height: 150 };
      const result = await computerVisionService.analyzeCanvasRegion(mockCanvas, region);

      expect(result).toEqual(mockResponse);
      expect(mockContext.drawImage).toHaveBeenCalledWith(
        mockCanvas,
        50, 50, 200, 150,
        0, 0, 200, 150
      );
    });

    it('should handle region analysis errors', async () => {
      const mockCanvas = document.createElement('canvas');
      jest.spyOn(document, 'createElement').mockReturnValue({
        getContext: jest.fn().mockReturnValue(null)
      } as any);

      const region = { x: 0, y: 0, width: 100, height: 100 };

      await expect(
        computerVisionService.analyzeCanvasRegion(mockCanvas, region)
      ).rejects.toThrow('Failed to analyze canvas region');
    });
  });

  describe('batchAnalyzeCanvasSnapshots', () => {
    it('should analyze multiple canvas snapshots', async () => {
      const snapshots = [
        'data:image/png;base64,snapshot1',
        'data:image/png;base64,snapshot2'
      ];

      const mockResponses = [
        {
          text_content: ['Snapshot 1 text'],
          mathematical_equations: [],
          diagrams: [],
          handwriting_text: '',
          confidence_scores: { text_detection: 0.9 },
          processing_time_ms: 100
        },
        {
          text_content: ['Snapshot 2 text'],
          mathematical_equations: ['x = 5'],
          diagrams: [],
          handwriting_text: '',
          confidence_scores: { text_detection: 0.85, equation_recognition: 0.9 },
          processing_time_ms: 120
        }
      ];

      mockApiService.post
        .mockResolvedValueOnce(mockResponses[0])
        .mockResolvedValueOnce(mockResponses[1]);

      const results = await computerVisionService.batchAnalyzeCanvasSnapshots(snapshots);

      expect(results).toEqual(mockResponses);
      expect(mockApiService.post).toHaveBeenCalledTimes(2);
    });

    it('should handle batch analysis errors', async () => {
      const snapshots = ['data:image/png;base64,snapshot1'];
      mockApiService.post.mockRejectedValue(new Error('Batch analysis failed'));

      await expect(
        computerVisionService.batchAnalyzeCanvasSnapshots(snapshots)
      ).rejects.toThrow('Failed to batch analyze canvas snapshots');
    });
  });

  describe('checkHealth', () => {
    it('should check service health', async () => {
      const mockResponse = {
        status: 'healthy',
        service: 'computer-vision',
        gemini_configured: true,
        models_available: ['gemini-pro-vision', 'gemini-pro']
      };

      mockApiService.get.mockResolvedValue(mockResponse);

      const result = await computerVisionService.checkHealth();

      expect(result).toEqual(mockResponse);
      expect(mockApiService.get).toHaveBeenCalledWith('/api/computer-vision/health');
    });

    it('should handle health check errors', async () => {
      mockApiService.get.mockRejectedValue(new Error('Service unavailable'));

      await expect(
        computerVisionService.checkHealth()
      ).rejects.toThrow('Computer vision service is unavailable');
    });
  });

  describe('formatAnalysisResults', () => {
    it('should format analysis results for display', () => {
      const analysisResult = {
        text_content: ['Hello World', 'Sample text'],
        mathematical_equations: ['x + 2 = 5', 'y = mx + b'],
        diagrams: [
          { type: 'rectangle', description: 'Red rectangle', elements: ['border'] }
        ],
        handwriting_text: 'Handwritten note',
        confidence_scores: { text_detection: 0.95 },
        processing_time_ms: 150
      };

      const formatted = computerVisionService.formatAnalysisResults(analysisResult);

      expect(formatted).toContain('**Text Content:**');
      expect(formatted).toContain('Hello World');
      expect(formatted).toContain('**Mathematical Equations:**');
      expect(formatted).toContain('x + 2 = 5');
      expect(formatted).toContain('**Handwritten Text:**');
      expect(formatted).toContain('Handwritten note');
      expect(formatted).toContain('**Diagrams:**');
      expect(formatted).toContain('rectangle: Red rectangle');
    });

    it('should handle empty analysis results', () => {
      const emptyResult = {
        text_content: [],
        mathematical_equations: [],
        diagrams: [],
        handwriting_text: '',
        confidence_scores: {},
        processing_time_ms: 50
      };

      const formatted = computerVisionService.formatAnalysisResults(emptyResult);

      expect(formatted).toBe('No content detected on the canvas.');
    });
  });

  describe('getConfidenceDescription', () => {
    it('should return correct confidence descriptions', () => {
      expect(computerVisionService.getConfidenceDescription(0.95)).toBe('Very High');
      expect(computerVisionService.getConfidenceDescription(0.85)).toBe('High');
      expect(computerVisionService.getConfidenceDescription(0.75)).toBe('Medium');
      expect(computerVisionService.getConfidenceDescription(0.65)).toBe('Low');
      expect(computerVisionService.getConfidenceDescription(0.55)).toBe('Very Low');
    });
  });
});