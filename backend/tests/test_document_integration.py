"""
Integration tests for document upload and processing system.
"""

import pytest
import io
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from main import app
from app.models.user import User


class TestDocumentIntegration:
    """Integration tests for the complete document processing pipeline."""
    
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
    
    def test_complete_document_workflow(self, client, mock_user, auth_headers):
        """Test the complete document upload, processing, and retrieval workflow."""
        
        with patch('app.api.documents.get_current_user', return_value=mock_user), \
             patch('app.services.document_processor.SentenceTransformer'), \
             patch('app.services.document_processor.chromadb.Client') as mock_chroma:
            
            # Mock ChromaDB collection
            mock_collection = Mock()
            mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
            
            # Test 1: Upload a text document
            test_content = "This is a test document with important information about machine learning."
            test_file = io.BytesIO(test_content.encode())
            
            upload_response = client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", test_file, "text/plain")}
            )
            
            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            assert upload_data["success"] is True
            assert "document_id" in upload_data["data"]
            document_id = upload_data["data"]["document_id"]
            
            # Verify document was processed and stored
            assert upload_data["data"]["filename"] == "test.txt"
            assert upload_data["data"]["content_type"] == "text/plain"
            assert upload_data["data"]["text_content"] == test_content
            assert upload_data["data"]["status"] == "processed"
            
            # Test 2: Get user documents
            mock_collection.get.return_value = {
                'metadatas': [{
                    'document_id': document_id,
                    'filename': 'test.txt',
                    'content_type': 'text/plain'
                }]
            }
            
            documents_response = client.get("/api/documents/", headers=auth_headers)
            assert documents_response.status_code == 200
            documents_data = documents_response.json()
            assert documents_data["success"] is True
            assert len(documents_data["data"]) == 1
            assert documents_data["data"][0]["document_id"] == document_id
            
            # Test 3: Search documents
            mock_collection.query.return_value = {
                'documents': [['This is a test document with important information']],
                'metadatas': [[{
                    'document_id': document_id,
                    'filename': 'test.txt',
                    'chunk_index': 0
                }]],
                'distances': [[0.1]]
            }
            
            search_response = client.get(
                "/api/documents/search?query=machine learning",
                headers=auth_headers
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            assert search_data["success"] is True
            assert len(search_data["data"]) == 1
            assert search_data["data"][0]["document_id"] == document_id
            assert search_data["data"][0]["similarity_score"] == 0.9  # 1 - 0.1
            
            # Test 4: Delete document
            mock_collection.get.return_value = {
                'ids': [f'{document_id}_0']
            }
            
            delete_response = client.delete(f"/api/documents/{document_id}", headers=auth_headers)
            assert delete_response.status_code == 200
            delete_data = delete_response.json()
            assert delete_data["success"] is True
            assert "deleted successfully" in delete_data["message"]
    
    def test_unsupported_file_type_workflow(self, client, mock_user, auth_headers):
        """Test handling of unsupported file types."""
        
        with patch('app.api.documents.get_current_user', return_value=mock_user):
            
            # Try to upload unsupported file type
            test_file = io.BytesIO(b"binary content")
            
            upload_response = client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("test.bin", test_file, "application/octet-stream")}
            )
            
            assert upload_response.status_code == 400
            error_data = upload_response.json()
            assert "Unsupported file type" in error_data["detail"]
    
    def test_large_file_workflow(self, client, mock_user, auth_headers):
        """Test handling of files that exceed size limit."""
        
        with patch('app.api.documents.get_current_user', return_value=mock_user):
            
            # Create file larger than 10MB
            large_content = b"x" * (11 * 1024 * 1024)
            test_file = io.BytesIO(large_content)
            
            upload_response = client.post(
                "/api/documents/upload",
                headers=auth_headers,
                files={"file": ("large.txt", test_file, "text/plain")}
            )
            
            assert upload_response.status_code == 413
            error_data = upload_response.json()
            assert "File size exceeds 10MB limit" in error_data["detail"]
    
    def test_authentication_required_workflow(self, client):
        """Test that all endpoints require authentication."""
        
        test_file = io.BytesIO(b"test content")
        
        # Test upload without auth
        upload_response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        assert upload_response.status_code == 401
        
        # Test get documents without auth
        documents_response = client.get("/api/documents/")
        assert documents_response.status_code == 401
        
        # Test search without auth
        search_response = client.get("/api/documents/search?query=test")
        assert search_response.status_code == 401
        
        # Test delete without auth
        delete_response = client.delete("/api/documents/doc123")
        assert delete_response.status_code == 401
    
    def test_supported_file_types_endpoint(self, client):
        """Test the supported file types endpoint (no auth required)."""
        
        response = client.get("/api/documents/supported-types")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "supported_types" in data["data"]
        assert "max_file_size" in data["data"]
        assert "features" in data["data"]
        
        # Verify expected file types are supported
        supported_types = data["data"]["supported_types"]
        mime_types = [ft["mime_type"] for ft in supported_types]
        
        expected_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "image/jpeg",
            "image/png",
            "image/tiff",
            "text/plain"
        ]
        
        for expected_type in expected_types:
            assert expected_type in mime_types