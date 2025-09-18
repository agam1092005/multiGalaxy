import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DocumentManager from '../DocumentManager';

// Mock DocumentUpload component
jest.mock('../DocumentUpload', () => {
  return function MockDocumentUpload({ onUploadSuccess, onUploadError }: any) {
    return (
      <div data-testid="document-upload">
        <button 
          onClick={() => onUploadSuccess?.({ document_id: 'new-doc' })}
          data-testid="mock-upload-success"
        >
          Mock Upload Success
        </button>
        <button 
          onClick={() => onUploadError?.('Upload error')}
          data-testid="mock-upload-error"
        >
          Mock Upload Error
        </button>
      </div>
    );
  };
});

// Mock fetch
global.fetch = jest.fn();

describe('DocumentManager', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.setItem('token', 'test-token');
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('renders document manager interface', async () => {
    // Mock successful documents fetch
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: []
      })
    });

    render(<DocumentManager />);
    
    expect(screen.getByText('Document Manager')).toBeInTheDocument();
    expect(screen.getByText('Upload Documents')).toBeInTheDocument();
    expect(screen.getByText('Search Documents')).toBeInTheDocument();
    expect(screen.getByText('Your Documents')).toBeInTheDocument();
    expect(screen.getByTestId('document-upload')).toBeInTheDocument();
  });

  it('loads and displays user documents', async () => {
    const mockDocuments = [
      {
        document_id: 'doc1',
        filename: 'test1.pdf',
        content_type: 'application/pdf',
        chunk_count: 3
      },
      {
        document_id: 'doc2',
        filename: 'test2.docx',
        content_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        chunk_count: 2
      }
    ];

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: mockDocuments
      })
    });

    render(<DocumentManager />);
    
    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument();
      expect(screen.getByText('test2.docx')).toBeInTheDocument();
      expect(screen.getByText('3 chunks indexed')).toBeInTheDocument();
      expect(screen.getByText('2 chunks indexed')).toBeInTheDocument();
    });
  });

  it('shows empty state when no documents', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: []
      })
    });

    render(<DocumentManager />);
    
    await waitFor(() => {
      expect(screen.getByText('No documents uploaded yet.')).toBeInTheDocument();
      expect(screen.getByText('Upload your first document above to get started.')).toBeInTheDocument();
    });
  });

  it('handles document search', async () => {
    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] })
    });

    // Mock search results
    const mockSearchResults = [
      {
        document_id: 'doc1',
        filename: 'test.pdf',
        content: 'This is relevant content about mathematics',
        similarity_score: 0.85,
        chunk_index: 0
      }
    ];

    render(<DocumentManager />);
    
    const searchInput = screen.getByPlaceholderText('Search for content in your documents...');
    const searchButton = screen.getByText('Search');
    
    fireEvent.change(searchInput, { target: { value: 'mathematics' } });
    
    // Mock search API call
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: mockSearchResults
      })
    });
    
    fireEvent.click(searchButton);
    
    await waitFor(() => {
      expect(screen.getByText('Search Results')).toBeInTheDocument();
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
      expect(screen.getByText('This is relevant content about mathematics')).toBeInTheDocument();
      expect(screen.getByText('Relevance: 85.0%')).toBeInTheDocument();
    });
  });

  it('handles search on Enter key press', async () => {
    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] })
    });

    render(<DocumentManager />);
    
    const searchInput = screen.getByPlaceholderText('Search for content in your documents...');
    
    fireEvent.change(searchInput, { target: { value: 'test query' } });
    
    // Mock search API call
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: []
      })
    });
    
    fireEvent.keyPress(searchInput, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/documents/search?query=test%20query&limit=10',
        expect.objectContaining({
          headers: { 'Authorization': 'Bearer test-token' }
        })
      );
    });
  });

  it('disables search button when no query', async () => {
    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] })
    });

    render(<DocumentManager />);
    
    const searchButton = screen.getByText('Search');
    
    expect(searchButton).toBeDisabled();
  });

  it('handles document deletion', async () => {
    const mockDocuments = [
      {
        document_id: 'doc1',
        filename: 'test.pdf',
        content_type: 'application/pdf',
        chunk_count: 1
      }
    ];

    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: mockDocuments
      })
    });

    // Mock window.confirm
    window.confirm = jest.fn(() => true);

    render(<DocumentManager />);
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });
    
    const deleteButton = screen.getByTitle('Delete document');
    
    // Mock delete API call
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        message: 'Document deleted successfully'
      })
    });
    
    // Mock refresh documents call
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: []
      })
    });
    
    fireEvent.click(deleteButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/documents/doc1', {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer test-token' }
      });
    });
  });

  it('cancels deletion when user declines confirmation', async () => {
    const mockDocuments = [
      {
        document_id: 'doc1',
        filename: 'test.pdf',
        content_type: 'application/pdf',
        chunk_count: 1
      }
    ];

    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: mockDocuments
      })
    });

    // Mock window.confirm to return false
    window.confirm = jest.fn(() => false);

    render(<DocumentManager />);
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });
    
    const deleteButton = screen.getByTitle('Delete document');
    fireEvent.click(deleteButton);
    
    // Should not make delete API call
    expect(fetch).toHaveBeenCalledTimes(1); // Only initial load
  });

  it('handles upload success callback', async () => {
    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] })
    });

    render(<DocumentManager />);
    
    // Mock refresh documents call after upload
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: [{ document_id: 'new-doc', filename: 'new.txt' }]
      })
    });
    
    const uploadSuccessButton = screen.getByTestId('mock-upload-success');
    fireEvent.click(uploadSuccessButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2); // Initial load + refresh
    });
  });

  it('handles upload error callback', async () => {
    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] })
    });

    render(<DocumentManager />);
    
    const uploadErrorButton = screen.getByTestId('mock-upload-error');
    fireEvent.click(uploadErrorButton);
    
    await waitFor(() => {
      expect(screen.getByText('Upload error')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    // Mock failed documents load
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<DocumentManager />);
    
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('shows loading state', async () => {
    // Mock slow API response
    (fetch as jest.Mock).mockImplementation(() => 
      new Promise(resolve => {
        setTimeout(() => {
          resolve({
            ok: true,
            json: async () => ({ success: true, data: [] })
          });
        }, 100);
      })
    );

    render(<DocumentManager />);
    
    expect(screen.getByText('Loading documents...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.queryByText('Loading documents...')).not.toBeInTheDocument();
    });
  });

  it('handles refresh button click', async () => {
    // Mock initial documents load
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] })
    });

    render(<DocumentManager />);
    
    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });
    
    const refreshButton = screen.getByText('Refresh');
    
    // Mock refresh API call
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] })
    });
    
    fireEvent.click(refreshButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2); // Initial + refresh
    });
  });
});