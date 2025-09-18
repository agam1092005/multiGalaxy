import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DocumentUpload from '../DocumentUpload';

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: jest.fn()
}));

// Mock fetch
global.fetch = jest.fn();

describe('DocumentUpload', () => {
  const mockUseDropzone = require('react-dropzone').useDropzone;
  
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.setItem('token', 'test-token');
    
    // Default mock implementation
    mockUseDropzone.mockReturnValue({
      getRootProps: () => ({ 'data-testid': 'dropzone' }),
      getInputProps: () => ({ 'data-testid': 'file-input' }),
      isDragActive: false,
      fileRejections: []
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('renders upload area correctly', () => {
    render(<DocumentUpload />);
    
    expect(screen.getByTestId('dropzone')).toBeInTheDocument();
    expect(screen.getByText('Upload documents')).toBeInTheDocument();
    expect(screen.getByText('Drag and drop files here, or click to select')).toBeInTheDocument();
    expect(screen.getByText('Supported: PDF, DOCX, PPTX, Images (JPG, PNG, TIFF), TXT')).toBeInTheDocument();
    expect(screen.getByText('Maximum file size: 10MB')).toBeInTheDocument();
  });

  it('shows drag active state', () => {
    mockUseDropzone.mockReturnValue({
      getRootProps: () => ({ 'data-testid': 'dropzone' }),
      getInputProps: () => ({ 'data-testid': 'file-input' }),
      isDragActive: true,
      fileRejections: []
    });

    render(<DocumentUpload />);
    
    expect(screen.getByText('Drop files here')).toBeInTheDocument();
  });

  it('displays file rejections', () => {
    const fileRejections = [
      {
        file: { name: 'large-file.txt' },
        errors: [{ message: 'File too large' }]
      },
      {
        file: { name: 'invalid-type.xyz' },
        errors: [{ message: 'File type not accepted' }]
      }
    ];

    mockUseDropzone.mockReturnValue({
      getRootProps: () => ({ 'data-testid': 'dropzone' }),
      getInputProps: () => ({ 'data-testid': 'file-input' }),
      isDragActive: false,
      fileRejections
    });

    render(<DocumentUpload />);
    
    expect(screen.getByText('Some files were rejected:')).toBeInTheDocument();
    expect(screen.getByText('large-file.txt: File too large')).toBeInTheDocument();
    expect(screen.getByText('invalid-type.xyz: File type not accepted')).toBeInTheDocument();
  });

  it('handles successful file upload', async () => {
    const mockOnUploadSuccess = jest.fn();
    const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock successful upload response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: {
          document_id: 'doc123',
          filename: 'test.txt',
          content_type: 'text/plain'
        }
      })
    });

    let onDropCallback: (files: File[]) => void;
    mockUseDropzone.mockImplementation(({ onDrop }: { onDrop: (files: File[]) => void }) => {
      onDropCallback = onDrop;
      return {
        getRootProps: () => ({ 'data-testid': 'dropzone' }),
        getInputProps: () => ({ 'data-testid': 'file-input' }),
        isDragActive: false,
        fileRejections: []
      };
    });

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);
    
    // Simulate file drop
    onDropCallback!([mockFile]);

    // Wait for upload to complete
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer test-token'
        },
        body: expect.any(FormData)
      });
    });

    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalledWith({
        document_id: 'doc123',
        filename: 'test.txt',
        content_type: 'text/plain'
      });
    });
  });

  it('handles upload error', async () => {
    const mockOnUploadError = jest.fn();
    const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock error response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        detail: 'Upload failed'
      })
    });

    let onDropCallback: (files: File[]) => void;
    mockUseDropzone.mockImplementation(({ onDrop }: { onDrop: (files: File[]) => void }) => {
      onDropCallback = onDrop;
      return {
        getRootProps: () => ({ 'data-testid': 'dropzone' }),
        getInputProps: () => ({ 'data-testid': 'file-input' }),
        isDragActive: false,
        fileRejections: []
      };
    });

    render(<DocumentUpload onUploadError={mockOnUploadError} />);
    
    // Simulate file drop
    onDropCallback!([mockFile]);

    await waitFor(() => {
      expect(mockOnUploadError).toHaveBeenCalledWith('Upload failed');
    });
  });

  it('handles authentication error', async () => {
    localStorage.removeItem('token');
    
    const mockOnUploadError = jest.fn();
    const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });

    let onDropCallback: (files: File[]) => void;
    mockUseDropzone.mockImplementation(({ onDrop }: { onDrop: (files: File[]) => void }) => {
      onDropCallback = onDrop;
      return {
        getRootProps: () => ({ 'data-testid': 'dropzone' }),
        getInputProps: () => ({ 'data-testid': 'file-input' }),
        isDragActive: false,
        fileRejections: []
      };
    });

    render(<DocumentUpload onUploadError={mockOnUploadError} />);
    
    // Simulate file drop
    onDropCallback!([mockFile]);

    await waitFor(() => {
      expect(mockOnUploadError).toHaveBeenCalledWith('Authentication required');
    });
  });

  it('shows upload progress', async () => {
    const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock slow upload response
    (fetch as jest.Mock).mockImplementation(() => 
      new Promise(resolve => {
        setTimeout(() => {
          resolve({
            ok: true,
            json: async () => ({
              success: true,
              data: { document_id: 'doc123' }
            })
          });
        }, 100);
      })
    );

    let onDropCallback: (files: File[]) => void;
    mockUseDropzone.mockImplementation(({ onDrop }: { onDrop: (files: File[]) => void }) => {
      onDropCallback = onDrop;
      return {
        getRootProps: () => ({ 'data-testid': 'dropzone' }),
        getInputProps: () => ({ 'data-testid': 'file-input' }),
        isDragActive: false,
        fileRejections: []
      };
    });

    render(<DocumentUpload />);
    
    // Simulate file drop
    onDropCallback!([mockFile]);

    // Check that progress is shown
    await waitFor(() => {
      expect(screen.getByText('Upload Progress')).toBeInTheDocument();
      expect(screen.getByText('test.txt')).toBeInTheDocument();
      expect(screen.getByText('Uploading...')).toBeInTheDocument();
    });
  });

  it('disables upload area when uploading', async () => {
    const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
    
    // Mock slow upload
    (fetch as jest.Mock).mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 1000))
    );

    let onDropCallback: (files: File[]) => void;
    mockUseDropzone.mockImplementation(({ onDrop }: { onDrop: (files: File[]) => void }) => {
      onDropCallback = onDrop;
      return {
        getRootProps: () => ({ 'data-testid': 'dropzone' }),
        getInputProps: () => ({ 'data-testid': 'file-input' }),
        isDragActive: false,
        fileRejections: []
      };
    });

    render(<DocumentUpload />);
    
    const dropzone = screen.getByTestId('dropzone');
    
    // Simulate file drop
    onDropCallback!([mockFile]);

    await waitFor(() => {
      expect(dropzone).toHaveClass('pointer-events-none', 'opacity-50');
    });
  });

  it('handles multiple file uploads sequentially', async () => {
    const mockFiles = [
      new File(['content1'], 'test1.txt', { type: 'text/plain' }),
      new File(['content2'], 'test2.txt', { type: 'text/plain' })
    ];
    
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        data: { document_id: 'doc123' }
      })
    });

    let onDropCallback: (files: File[]) => void;
    mockUseDropzone.mockImplementation(({ onDrop }: { onDrop: (files: File[]) => void }) => {
      onDropCallback = onDrop;
      return {
        getRootProps: () => ({ 'data-testid': 'dropzone' }),
        getInputProps: () => ({ 'data-testid': 'file-input' }),
        isDragActive: false,
        fileRejections: []
      };
    });

    render(<DocumentUpload />);
    
    // Simulate multiple file drop
    onDropCallback!(mockFiles);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2);
    });
  });
});