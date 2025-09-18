/**
 * Document service for handling file uploads and document management
 */

export interface Document {
  document_id: string;
  filename: string;
  content_type: string;
  chunk_count: number;
}

export interface SearchResult {
  document_id: string;
  filename: string;
  content: string;
  similarity_score: number;
  chunk_index: number;
}

export interface UploadResult {
  document_id: string;
  filename: string;
  content_type: string;
  text_content: string;
  chunk_count: number;
  file_path: string;
  status: string;
}

export interface SupportedFileType {
  type: string;
  mime_type: string;
  extensions: string[];
  description: string;
}

class DocumentService {
  private baseUrl = '/api/documents';

  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Authentication required');
    }
    return {
      'Authorization': `Bearer ${token}`
    };
  }

  /**
   * Upload a document file
   */
  async uploadDocument(file: File): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/upload`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Upload failed');
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Get all documents for the current user
   */
  async getUserDocuments(): Promise<Document[]> {
    const response = await fetch(this.baseUrl, {
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error('Failed to fetch documents');
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Search for content in user's documents
   */
  async searchDocuments(query: string, limit: number = 5): Promise<SearchResult[]> {
    const params = new URLSearchParams({
      query,
      limit: limit.toString()
    });

    const response = await fetch(`${this.baseUrl}/search?${params}`, {
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error('Search failed');
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Delete a document
   */
  async deleteDocument(documentId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/${documentId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to delete document');
    }
  }

  /**
   * Get supported file types
   */
  async getSupportedFileTypes(): Promise<{
    supported_types: SupportedFileType[];
    max_file_size: string;
    features: string[];
  }> {
    const response = await fetch(`${this.baseUrl}/supported-types`);

    if (!response.ok) {
      throw new Error('Failed to fetch supported file types');
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File): { isValid: boolean; error?: string } {
    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      return {
        isValid: false,
        error: 'File size exceeds 10MB limit'
      };
    }

    // Check file type
    const supportedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'image/jpeg',
      'image/png',
      'image/tiff',
      'text/plain'
    ];

    if (!supportedTypes.includes(file.type)) {
      return {
        isValid: false,
        error: `Unsupported file type: ${file.type}`
      };
    }

    return { isValid: true };
  }

  /**
   * Format file size for display
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Get file type icon
   */
  getFileTypeIcon(contentType: string): string {
    if (contentType.includes('pdf')) {
      return '📄';
    } else if (contentType.includes('word')) {
      return '📝';
    } else if (contentType.includes('presentation')) {
      return '📊';
    } else if (contentType.includes('image')) {
      return '🖼️';
    } else if (contentType.includes('text')) {
      return '📃';
    }
    return '📁';
  }
}

export const documentService = new DocumentService();