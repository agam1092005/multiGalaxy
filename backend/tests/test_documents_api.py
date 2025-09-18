"""
Tests for document API endpoints.
"""

import pytest
import io
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile

from main import app
from app.models.user import User


class TestDocumentsAPI:
    """Test cases for document API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        user = Mock(spec=User)
        user.id = "test_user_id"
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers."""
        return {"Authorization": "Bearer test_token"}
    
    def test_upload_document_success(self, client, mock_user, auth_headers):
        """Test successful document upload."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.process_document') as mock_process:
            
            mock_process.return_value = {
                "document_id": "doc123",
                "filename": "test.txt",
                "content_type": "text/plain",
                "text_content": "Test content",
                "chunk_count": 1,
                "file_path": "uploads/doc123.txt",
                "status": "processed"
            }
            
            # Create test file
            test_file = io.BytesIO(b"Test file content")
            
            response = client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", test_file, "text/plain")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["document_id"] == "doc123"
            assert data["data"]["filename"] == "test.txt"
    
    def test_upload_document_too_large(self, client, mock_user, auth_headers):
        """Test upload of file that exceeds size limit."""
        with patch('app.api.documents.get_current_user', return_value=mock_user):
            
            # Create large file (>10MB)
            large_content = b"x" * (11 * 1024 * 1024)
            test_file = io.BytesIO(large_content)
            
            response = client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("large.txt", test_file, "text/plain")}
            )
            
            assert response.status_code == 413
            data = response.json()
            assert "File size exceeds 10MB limit" in data["detail"]
    
    def test_upload_document_unsupported_type(self, client, mock_user, auth_headers):
        """Test upload of unsupported file type."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.process_document', 
                   side_effect=ValueError("Unsupported file type")):
            
            test_file = io.BytesIO(b"Test content")
            
            response = client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("test.xyz", test_file, "application/unknown")}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "Unsupported file type" in data["detail"]
    
    def test_upload_document_no_auth(self, client):
        """Test upload without authentication."""
        test_file = io.BytesIO(b"Test content")
        
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        
        assert response.status_code == 401
    
    def test_get_user_documents_success(self, client, mock_user, auth_headers):
        """Test successful retrieval of user documents."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.get_user_documents') as mock_get:
            
            mock_get.return_value = [
                {
                    "document_id": "doc1",
                    "filename": "test1.txt",
                    "content_type": "text/plain",
                    "chunk_count": 1
                },
                {
                    "document_id": "doc2",
                    "filename": "test2.pdf",
                    "content_type": "application/pdf",
                    "chunk_count": 3
                }
            ]
            
            response = client.get("/api/documents/", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 2
            assert data["data"][0]["document_id"] == "doc1"
    
    def test_get_user_documents_no_auth(self, client):
        """Test document retrieval without authentication."""
        response = client.get("/api/documents/")
        
        assert response.status_code == 401
    
    def test_search_documents_success(self, client, mock_user, auth_headers):
        """Test successful document search."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.search_documents') as mock_search:
            
            mock_search.return_value = [
                {
                    "document_id": "doc1",
                    "filename": "test.txt",
                    "content": "This is relevant content",
                    "similarity_score": 0.85,
                    "chunk_index": 0
                }
            ]
            
            response = client.get(
                "/api/documents/search?query=test&limit=5",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["query"] == "test"
            assert len(data["data"]) == 1
            assert data["data"][0]["similarity_score"] == 0.85
    
    def test_search_documents_missing_query(self, client, mock_user, auth_headers):
        """Test search without query parameter."""
        with patch('app.api.documents.get_current_user', return_value=mock_user):
            
            response = client.get("/api/documents/search", headers=auth_headers)
            
            assert response.status_code == 422  # Validation error
    
    def test_search_documents_no_auth(self, client):
        """Test search without authentication."""
        response = client.get("/api/documents/search?query=test")
        
        assert response.status_code == 401
    
    def test_delete_document_success(self, client, mock_user, auth_headers):
        """Test successful document deletion."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.delete_document', return_value=True) as mock_delete:
            
            response = client.delete("/api/documents/doc123", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "deleted successfully" in data["message"]
            mock_delete.assert_called_once_with("doc123", "test_user_id")
    
    def test_delete_document_not_found(self, client, mock_user, auth_headers):
        """Test deletion of non-existent document."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.delete_document', return_value=False):
            
            response = client.delete("/api/documents/nonexistent", headers=auth_headers)
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]
    
    def test_delete_document_no_auth(self, client):
        """Test deletion without authentication."""
        response = client.delete("/api/documents/doc123")
        
        assert response.status_code == 401
    
    def test_get_supported_file_types(self, client):
        """Test getting supported file types."""
        response = client.get("/api/documents/supported-types")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "supported_types" in data["data"]
        assert "max_file_size" in data["data"]
        assert "features" in data["data"]
        
        # Check that common file types are supported
        supported_types = data["data"]["supported_types"]
        mime_types = [ft["mime_type"] for ft in supported_types]
        assert "application/pdf" in mime_types
        assert "text/plain" in mime_types
        assert "image/jpeg" in mime_types
    
    def test_upload_document_processing_error(self, client, mock_user, auth_headers):
        """Test handling of document processing errors."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.process_document', 
                   side_effect=Exception("Processing failed")):
            
            test_file = io.BytesIO(b"Test content")
            
            response = client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", test_file, "text/plain")}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]
    
    def test_search_documents_error(self, client, mock_user, auth_headers):
        """Test handling of search errors."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.search_documents', 
                   side_effect=Exception("Search failed")):
            
            response = client.get(
                "/api/documents/search?query=test",
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]
    
    def test_get_documents_error(self, client, mock_user, auth_headers):
        """Test handling of document retrieval errors."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.get_user_documents', 
                   side_effect=Exception("Database error")):
            
            response = client.get("/api/documents/", headers=auth_headers)
            
            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]
    
    def test_delete_document_error(self, client, mock_user, auth_headers):
        """Test handling of document deletion errors."""
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.api.documents.document_processor.delete_document', 
                   side_effect=Exception("Deletion failed")):
            
            response = client.delete("/api/documents/doc123", headers=auth_headers)
            
            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]