import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface DocumentUploadProps {
  onUploadSuccess?: (document: any) => void;
  onUploadError?: (error: string) => void;
}

interface UploadProgress {
  fileName: string;
  progress: number;
  status: 'uploading' | 'processing' | 'success' | 'error';
  error?: string;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadSuccess,
  onUploadError
}) => {
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const supportedTypes = {
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/tiff': ['.tiff', '.tif'],
    'text/plain': ['.txt']
  };

  const uploadFile = async (file: File): Promise<void> => {
    const uploadId = `${file.name}-${Date.now()}`;
    
    // Add to upload progress
    setUploads(prev => [...prev, {
      fileName: file.name,
      progress: 0,
      status: 'uploading'
    }]);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      // Update progress to processing
      setUploads(prev => prev.map(upload => 
        upload.fileName === file.name 
          ? { ...upload, progress: 50, status: 'processing' }
          : upload
      ));

      const result = await response.json();

      // Update to success
      setUploads(prev => prev.map(upload => 
        upload.fileName === file.name 
          ? { ...upload, progress: 100, status: 'success' }
          : upload
      ));

      onUploadSuccess?.(result.data);

      // Remove from progress after 3 seconds
      setTimeout(() => {
        setUploads(prev => prev.filter(upload => upload.fileName !== file.name));
      }, 3000);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      
      // Update to error
      setUploads(prev => prev.map(upload => 
        upload.fileName === file.name 
          ? { ...upload, status: 'error', error: errorMessage }
          : upload
      ));

      onUploadError?.(errorMessage);

      // Remove from progress after 5 seconds
      setTimeout(() => {
        setUploads(prev => prev.filter(upload => upload.fileName !== file.name));
      }, 5000);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setIsUploading(true);

    try {
      // Upload files sequentially to avoid overwhelming the server
      for (const file of acceptedFiles) {
        await uploadFile(file);
      }
    } finally {
      setIsUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: supportedTypes,
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  });

  const getStatusIcon = (status: UploadProgress['status']) => {
    switch (status) {
      case 'uploading':
      case 'processing':
        return (
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
        );
      case 'success':
        return (
          <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
    }
  };

  const getStatusColor = (status: UploadProgress['status']) => {
    switch (status) {
      case 'uploading':
      case 'processing':
        return 'bg-blue-200';
      case 'success':
        return 'bg-green-200';
      case 'error':
        return 'bg-red-200';
    }
  };

  return (
    <div className="w-full">
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
          ${isUploading ? 'pointer-events-none opacity-50' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="space-y-4">
          <div className="mx-auto w-12 h-12 text-gray-400">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          
          <div>
            <p className="text-lg font-medium text-gray-900">
              {isDragActive ? 'Drop files here' : 'Upload documents'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Drag and drop files here, or click to select
            </p>
          </div>
          
          <div className="text-xs text-gray-400">
            <p>Supported: PDF, DOCX, PPTX, Images (JPG, PNG, TIFF), TXT</p>
            <p>Maximum file size: 10MB</p>
          </div>
        </div>
      </div>

      {/* File Rejections */}
      {fileRejections.length > 0 && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <h4 className="text-sm font-medium text-red-800">Some files were rejected:</h4>
          <ul className="mt-1 text-sm text-red-700">
            {fileRejections.map(({ file, errors }) => (
              <li key={file.name}>
                {file.name}: {errors.map(e => e.message).join(', ')}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Upload Progress */}
      {uploads.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-900">Upload Progress</h4>
          {uploads.map((upload, index) => (
            <div key={index} className={`p-3 rounded-md ${getStatusColor(upload.status)}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(upload.status)}
                  <span className="text-sm font-medium truncate">{upload.fileName}</span>
                </div>
                <span className="text-xs text-gray-600">
                  {upload.status === 'uploading' && 'Uploading...'}
                  {upload.status === 'processing' && 'Processing...'}
                  {upload.status === 'success' && 'Complete'}
                  {upload.status === 'error' && 'Failed'}
                </span>
              </div>
              
              {upload.status === 'error' && upload.error && (
                <p className="text-xs text-red-600 mt-1">{upload.error}</p>
              )}
              
              {(upload.status === 'uploading' || upload.status === 'processing') && (
                <div className="mt-2 w-full bg-white rounded-full h-1">
                  <div 
                    className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                    style={{ width: `${upload.progress}%` }}
                  ></div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;