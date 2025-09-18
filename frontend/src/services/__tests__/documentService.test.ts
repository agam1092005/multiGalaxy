import { documentService } from '../documentService';

// Mock fetch
global.fetch = jest.fn();

describe('DocumentService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.setItem('token', 'test-token');
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('uploadDocument', () => {
    it('uploads document successfully', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const mockResponse = {
        document_id: 'doc123',
        filename: 'test.txt',
        content_type: 'text/plain',
        text_content: 'test content',
        chunk_count: 1,
        file_path: 'uploads/doc123.txt',
        status: 'processed'
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockResponse
        })
      });

      const result = await documentService.uploadDocument(mockFile);

      expect(fetch).toHaveBeenCalledWith('/api/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer test-token'
        },
        body: expect.any(FormData)
      });

      expect(result).toEqual(mockResponse);
    });

    it('throws error when no token', async () => {
      localStorage.removeItem('token');
      const mockFile = new File(['test'], 'test.txt', { type: 'text/plain' });

      await expect(documentService.uploadDocument(mockFile)).rejects.toThrow('Authentication required');
    });

    it('handles upload error', async () => {
      const mockFile = new File(['test'], 'test.txt', { type: 'text/plain' });

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: 'Upload failed'
        })
      });

      await expect(documentService.uploadDocument(mockFile)).rejects.toThrow('Upload failed');
    });
  });

  describe('getUserDocuments', () => {
    it('fetches user documents successfully', async () => {
      const mockDocuments = [
        {
          document_id: 'doc1',
          filename: 'test1.txt',
          content_type: 'text/plain',
          chunk_count: 1
        },
        {
          document_id: 'doc2',
          filename: 'test2.pdf',
          content_type: 'application/pdf',
          chunk_count: 3
        }
      ];

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockDocuments
        })
      });

      const result = await documentService.getUserDocuments();

      expect(fetch).toHaveBeenCalledWith('/api/documents', {
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });

      expect(result).toEqual(mockDocuments);
    });

    it('handles fetch error', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false
      });

      await expect(documentService.getUserDocuments()).rejects.toThrow('Failed to fetch documents');
    });
  });

  describe('searchDocuments', () => {
    it('searches documents successfully', async () => {
      const mockResults = [
        {
          document_id: 'doc1',
          filename: 'test.txt',
          content: 'relevant content',
          similarity_score: 0.85,
          chunk_index: 0
        }
      ];

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockResults
        })
      });

      const result = await documentService.searchDocuments('test query', 5);

      expect(fetch).toHaveBeenCalledWith('/api/documents/search?query=test+query&limit=5', {
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });

      expect(result).toEqual(mockResults);
    });

    it('uses default limit when not provided', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: [] })
      });

      await documentService.searchDocuments('test');

      expect(fetch).toHaveBeenCalledWith('/api/documents/search?query=test&limit=5', {
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });
    });

    it('handles search error', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false
      });

      await expect(documentService.searchDocuments('test')).rejects.toThrow('Search failed');
    });
  });

  describe('deleteDocument', () => {
    it('deletes document successfully', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Document deleted successfully'
        })
      });

      await documentService.deleteDocument('doc123');

      expect(fetch).toHaveBeenCalledWith('/api/documents/doc123', {
        method: 'DELETE',
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });
    });

    it('handles delete error', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: 'Document not found'
        })
      });

      await expect(documentService.deleteDocument('doc123')).rejects.toThrow('Document not found');
    });
  });

  describe('getSupportedFileTypes', () => {
    it('fetches supported file types', async () => {
      const mockData = {
        supported_types: [
          {
            type: 'PDF',
            mime_type: 'application/pdf',
            extensions: ['.pdf'],
            description: 'Portable Document Format'
          }
        ],
        max_file_size: '10MB',
        features: ['Text extraction', 'OCR']
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: mockData
        })
      });

      const result = await documentService.getSupportedFileTypes();

      expect(fetch).toHaveBeenCalledWith('/api/documents/supported-types');
      expect(result).toEqual(mockData);
    });
  });

  describe('validateFile', () => {
    it('validates file size', () => {
      // File too large (>10MB)
      const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.txt', { type: 'text/plain' });
      const result = documentService.validateFile(largeFile);

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('File size exceeds 10MB limit');
    });

    it('validates file type', () => {
      const unsupportedFile = new File(['test'], 'test.xyz', { type: 'application/unknown' });
      const result = documentService.validateFile(unsupportedFile);

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Unsupported file type: application/unknown');
    });

    it('validates supported file successfully', () => {
      const validFile = new File(['test'], 'test.txt', { type: 'text/plain' });
      const result = documentService.validateFile(validFile);

      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });
  });

  describe('formatFileSize', () => {
    it('formats file sizes correctly', () => {
      expect(documentService.formatFileSize(0)).toBe('0 Bytes');
      expect(documentService.formatFileSize(1024)).toBe('1 KB');
      expect(documentService.formatFileSize(1024 * 1024)).toBe('1 MB');
      expect(documentService.formatFileSize(1536)).toBe('1.5 KB');
    });
  });

  describe('getFileTypeIcon', () => {
    it('returns correct icons for file types', () => {
      expect(documentService.getFileTypeIcon('application/pdf')).toBe('📄');
      expect(documentService.getFileTypeIcon('application/vnd.openxmlformats-officedocument.wordprocessingml.document')).toBe('📝');
      expect(documentService.getFileTypeIcon('application/vnd.openxmlformats-officedocument.presentationml.presentation')).toBe('📊');
      expect(documentService.getFileTypeIcon('image/jpeg')).toBe('🖼️');
      expect(documentService.getFileTypeIcon('text/plain')).toBe('📃');
      expect(documentService.getFileTypeIcon('application/unknown')).toBe('📁');
    });
  });
});