"""
Tests for document processing service.
"""

import pytest
import asyncio
import io
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from app.services.document_processor import DocumentProcessor
from app.services.rag_system import RAGSystem


class TestDocumentProcessor:
    """Test cases for DocumentProcessor service."""
    
    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing."""
        with patch('app.services.document_processor.RAGSystem') as mock_rag:
            mock_rag_instance = Mock()
            mock_rag_instance.add_document = AsyncMock(return_value={
                'status': 'success',
                'chunks_created': 3,
                'subject': 'math',
                'collections': ['documents', 'math']
            })
            mock_rag_instance.search = AsyncMock(return_value=[])
            mock_rag_instance.delete_document = AsyncMock(return_value=True)
            mock_rag_instance.get_context_for_query = AsyncMock(return_value={
                'context': 'test context',
                'sources': [],
                'total_chunks': 0,
                'subjects_covered': []
            })
            mock_rag.return_value = mock_rag_instance
            
            processor = DocumentProcessor()
            processor.rag_system = mock_rag_instance
            return processor
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing."""
        # This would be actual PDF bytes in a real test
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    
    @pytest.fixture
    def sample_text_content(self):
        """Sample text content for testing."""
        return b"This is a sample text document for testing purposes."
    
    @pytest.fixture
    def sample_image_content(self):
        """Sample image content for testing."""
        # This would be actual image bytes in a real test
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    
    @pytest.mark.asyncio
    async def test_process_text_document(self, processor, sample_text_content):
        """Test processing a plain text document."""
        with patch.object(processor, '_save_file', return_value='test_path'):
            
            result = await processor.process_document(
                file_content=sample_text_content,
                filename="test.txt",
                content_type="text/plain",
                user_id="test_user"
            )
            
            assert result['filename'] == "test.txt"
            assert result['content_type'] == "text/plain"
            assert result['status'] == "processed"
            assert 'document_id' in result
            assert result['text_content'] == "This is a sample text document for testing purposes."
            assert result['subject'] == 'math'  # From mock RAG system
            assert result['chunk_count'] == 3
            processor.rag_system.add_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_pdf_document(self, processor, sample_pdf_content):
        """Test processing a PDF document."""
        with patch('app.services.document_processor.PyPDF2.PdfReader') as mock_reader, \
             patch.object(processor, '_save_file', return_value='test_path'):
            
            # Mock PDF reader
            mock_page = Mock()
            mock_page.extract_text.return_value = "Sample PDF content"
            mock_reader.return_value.pages = [mock_page]
            
            result = await processor.process_document(
                file_content=sample_pdf_content,
                filename="test.pdf",
                content_type="application/pdf",
                user_id="test_user"
            )
            
            assert result['filename'] == "test.pdf"
            assert result['content_type'] == "application/pdf"
            assert result['status'] == "processed"
            assert result['text_content'] == "Sample PDF content\n"
            assert result['subject'] == 'math'
            processor.rag_system.add_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_image_with_ocr(self, processor, sample_image_content):
        """Test processing an image with OCR."""
        with patch('app.services.document_processor.pytesseract.image_to_string', return_value="OCR extracted text"), \
             patch('app.services.document_processor.Image.open'), \
             patch.object(processor, '_save_file', return_value='test_path'):
            
            result = await processor.process_document(
                file_content=sample_image_content,
                filename="test.png",
                content_type="image/png",
                user_id="test_user"
            )
            
            assert result['filename'] == "test.png"
            assert result['content_type'] == "image/png"
            assert result['status'] == "processed"
            assert result['text_content'] == "OCR extracted text"
            assert result['subject'] == 'math'
            processor.rag_system.add_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, processor):
        """Test handling of unsupported file types."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            await processor.process_document(
                file_content=b"test content",
                filename="test.xyz",
                content_type="application/unknown",
                user_id="test_user"
            )
    
    @pytest.mark.asyncio
    async def test_empty_document(self, processor):
        """Test handling of documents with no extractable text."""
        with patch.object(processor, '_extract_text_file', return_value=""), \
             pytest.raises(ValueError, match="No text content could be extracted"):
            
            await processor.process_document(
                file_content=b"",
                filename="empty.txt",
                content_type="text/plain",
                user_id="test_user"
            )
    
    def test_create_text_chunks(self, processor):
        """Test text chunking functionality."""
        text = "This is a long text. " * 100  # Create long text
        chunks = processor._create_text_chunks(text, chunk_size=100, overlap=20)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 120 for chunk in chunks)  # Allow for overlap
        
        # Test short text
        short_text = "Short text"
        short_chunks = processor._create_text_chunks(short_text, chunk_size=100)
        assert len(short_chunks) == 1
        assert short_chunks[0] == short_text
    
    @pytest.mark.asyncio
    async def test_search_documents(self, processor):
        """Test document search functionality."""
        # Mock RAG system search results
        processor.rag_system.search.return_value = [
            {
                'document_id': 'doc1',
                'content': 'Sample document content',
                'similarity_score': 0.8,
                'metadata': {'filename': 'test.txt', 'chunk_index': 0}
            }
        ]
        
        results = await processor.search_documents(
            query="test query",
            user_id="test_user",
            limit=5
        )
        
        assert len(results) == 1
        assert results[0]['document_id'] == 'doc1'
        assert results[0]['content'] == 'Sample document content'
        assert results[0]['similarity_score'] == 0.8
        processor.rag_system.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_documents(self, processor):
        """Test getting user documents."""
        # Mock RAG system search results
        processor.rag_system.search.return_value = [
            {
                'metadata': {
                    'document_id': 'doc1',
                    'filename': 'test1.txt',
                    'content_type': 'text/plain',
                    'subject': 'math'
                }
            },
            {
                'metadata': {
                    'document_id': 'doc1',
                    'filename': 'test1.txt',
                    'content_type': 'text/plain',
                    'subject': 'math'
                }
            },
            {
                'metadata': {
                    'document_id': 'doc2',
                    'filename': 'test2.pdf',
                    'content_type': 'application/pdf',
                    'subject': 'science'
                }
            }
        ]
        
        documents = await processor.get_user_documents("test_user")
        
        assert len(documents) == 2
        assert documents[0]['document_id'] == 'doc1'
        assert documents[0]['chunk_count'] == 2
        assert documents[0]['subject'] == 'math'
        assert documents[1]['document_id'] == 'doc2'
        assert documents[1]['chunk_count'] == 1
        assert documents[1]['subject'] == 'science'
    
    @pytest.mark.asyncio
    async def test_delete_document(self, processor):
        """Test document deletion."""
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            mock_glob.return_value = [Path('uploads/doc1.txt')]
            processor.rag_system.delete_document.return_value = True
            
            result = await processor.delete_document("doc1", "test_user")
            
            assert result is True
            processor.rag_system.delete_document.assert_called_once_with("doc1", "test_user")
            mock_unlink.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, processor):
        """Test deletion of non-existent document."""
        processor.rag_system.delete_document.return_value = False
        
        result = await processor.delete_document("nonexistent", "test_user")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_docx_extraction(self, processor):
        """Test DOCX text extraction."""
        with patch('app.services.document_processor.DocxDocument') as mock_docx:
            # Mock document structure
            mock_paragraph = Mock()
            mock_paragraph.text = "Paragraph text"
            
            mock_cell = Mock()
            mock_cell.text = "Cell text"
            mock_row = Mock()
            mock_row.cells = [mock_cell]
            mock_table = Mock()
            mock_table.rows = [mock_row]
            
            mock_doc = Mock()
            mock_doc.paragraphs = [mock_paragraph]
            mock_doc.tables = [mock_table]
            mock_docx.return_value = mock_doc
            
            result = await processor._extract_docx_text(b"docx content")
            
            assert "Paragraph text" in result
            assert "Cell text" in result
    
    @pytest.mark.asyncio
    async def test_pptx_extraction(self, processor):
        """Test PPTX text extraction."""
        with patch('app.services.document_processor.Presentation') as mock_pptx:
            # Mock presentation structure
            mock_shape = Mock()
            mock_shape.text = "Slide text"
            mock_slide = Mock()
            mock_slide.shapes = [mock_shape]
            
            mock_prs = Mock()
            mock_prs.slides = [mock_slide]
            mock_pptx.return_value = mock_prs
            
            result = await processor._extract_pptx_text(b"pptx content")
            
            assert "Slide text" in result
    
    @pytest.mark.asyncio
    async def test_pdf_ocr_fallback(self, processor):
        """Test PDF OCR fallback when direct text extraction fails."""
        with patch('app.services.document_processor.PyPDF2.PdfReader') as mock_reader, \
             patch('app.services.document_processor.convert_from_bytes') as mock_convert, \
             patch('app.services.document_processor.pytesseract.image_to_string', return_value="OCR text"):
            
            # Mock PDF reader that returns empty text
            mock_page = Mock()
            mock_page.extract_text.return_value = ""
            mock_reader.return_value.pages = [mock_page]
            
            # Mock image conversion
            mock_image = Mock()
            mock_convert.return_value = [mock_image]
            
            result = await processor._extract_pdf_text(b"pdf content")
            
            assert result == "OCR text\n"
    
    @pytest.mark.asyncio
    async def test_get_document_context(self, processor):
        """Test getting document context for queries."""
        # Mock RAG system context response
        processor.rag_system.get_context_for_query.return_value = {
            'context': 'This is relevant context from documents',
            'sources': [{'filename': 'test.txt', 'similarity_score': 0.9}],
            'total_chunks': 2,
            'subjects_covered': ['math']
        }
        
        result = await processor.get_document_context(
            query="algebra equations",
            user_id="test_user",
            subject="math",
            max_context_length=2000
        )
        
        assert result['context'] == 'This is relevant context from documents'
        assert len(result['sources']) == 1
        assert result['total_chunks'] == 2
        assert 'math' in result['subjects_covered']
        processor.rag_system.get_context_for_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_processing(self, processor):
        """Test error handling during document processing."""
        with patch.object(processor, '_extract_text_file', side_effect=Exception("Processing error")):
            with pytest.raises(ValueError, match="Failed to process document"):
                await processor.process_document(
                    file_content=b"test content",
                    filename="test.txt",
                    content_type="text/plain",
                    user_id="test_user"
                )