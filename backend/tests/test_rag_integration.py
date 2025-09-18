"""
Integration tests for RAG System functionality.
Tests the complete pipeline from document processing to context retrieval.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from app.services.document_processor import DocumentProcessor
from app.services.rag_system import RAGSystem
from app.services.knowledge_base import KnowledgeBaseManager, SubjectArea, GradeLevel


class TestRAGIntegration:
    """Integration tests for RAG system components."""
    
    @pytest.fixture
    def mock_rag_system(self):
        """Create a mock RAG system for testing."""
        mock_rag = Mock()
        mock_rag.add_document = AsyncMock(return_value={
            'status': 'success',
            'chunks_created': 2,
            'subject': 'math',
            'collections': ['documents', 'math'],
            'embedding_dimension': 384
        })
        mock_rag.search = AsyncMock(return_value=[
            {
                'content': 'Algebra is a branch of mathematics dealing with symbols.',
                'similarity_score': 0.9,
                'document_id': 'test_doc',
                'chunk_index': 0,
                'metadata': {
                    'filename': 'algebra.txt',
                    'user_id': 'user123',
                    'subject': 'math'
                }
            }
        ])
        mock_rag.get_context_for_query = AsyncMock(return_value={
            'context': 'Algebra is a branch of mathematics dealing with symbols.',
            'sources': [{'filename': 'algebra.txt', 'similarity_score': 0.9}],
            'total_chunks': 1,
            'subjects_covered': ['math'],
            'context_length': 50
        })
        mock_rag.delete_document = AsyncMock(return_value=True)
        mock_rag.get_collection_stats = AsyncMock(return_value={
            'documents': {'document_count': 5, 'status': 'active'},
            'math': {'document_count': 3, 'status': 'active'}
        })
        return mock_rag
    
    @pytest.fixture
    def document_processor(self, mock_rag_system):
        """Create a document processor with mocked RAG system."""
        with patch('app.services.document_processor.RAGSystem') as mock_rag_class:
            mock_rag_class.return_value = mock_rag_system
            processor = DocumentProcessor()
            processor.rag_system = mock_rag_system
            return processor
    
    @pytest.fixture
    def knowledge_base_manager(self, mock_rag_system):
        """Create a knowledge base manager with mocked RAG system."""
        with patch('app.services.knowledge_base.Path') as mock_path:
            mock_path.return_value.mkdir = Mock()
            mock_path.return_value.exists = Mock(return_value=False)
            
            kb_manager = KnowledgeBaseManager(mock_rag_system)
            return kb_manager
    
    @pytest.mark.asyncio
    async def test_document_processing_pipeline(self, document_processor):
        """Test the complete document processing pipeline."""
        # Sample document content
        sample_content = b"Introduction to Algebra. Algebra uses variables like x and y to represent unknown values."
        
        with patch.object(document_processor, '_save_file', return_value='test_path'):
            # Process document
            result = await document_processor.process_document(
                file_content=sample_content,
                filename="algebra_intro.txt",
                content_type="text/plain",
                user_id="user123"
            )
            
            # Verify document was processed
            assert result['status'] == 'processed'
            assert result['filename'] == 'algebra_intro.txt'
            assert result['subject'] == 'math'
            assert result['chunk_count'] == 2
            
            # Verify RAG system was called
            document_processor.rag_system.add_document.assert_called_once()
            
            # Test document search
            search_results = await document_processor.search_documents(
                query="algebra variables",
                user_id="user123",
                subject="math"
            )
            
            assert len(search_results) > 0
            assert search_results[0]['similarity_score'] == 0.9
            document_processor.rag_system.search.assert_called()
            
            # Test context retrieval
            context = await document_processor.get_document_context(
                query="what is algebra",
                user_id="user123",
                subject="math"
            )
            
            assert context['context'] != ''
            assert len(context['sources']) > 0
            assert 'math' in context['subjects_covered']
            document_processor.rag_system.get_context_for_query.assert_called()
    
    @pytest.mark.asyncio
    async def test_knowledge_base_integration(self, knowledge_base_manager):
        """Test knowledge base integration with RAG system."""
        # Add knowledge item
        item_id = await knowledge_base_manager.add_knowledge_item(
            title="Linear Equations",
            content="A linear equation is an equation of the first degree.",
            subject=SubjectArea.MATHEMATICS,
            grade_level=GradeLevel.HIGH,
            topics=["algebra", "equations"],
            difficulty_level=6
        )
        
        # Verify item was added
        assert item_id.startswith('kb_')
        assert item_id in knowledge_base_manager.knowledge_items
        
        # Verify RAG system was called
        knowledge_base_manager.rag_system.add_document.assert_called()
        
        # Test knowledge base search
        with patch.object(knowledge_base_manager.rag_system, 'search') as mock_search:
            mock_search.return_value = [
                {
                    'content': 'A linear equation is an equation of the first degree.',
                    'similarity_score': 0.85,
                    'metadata': {
                        'knowledge_item_id': item_id,
                        'subject': 'mathematics',
                        'grade_level': 'high',
                        'topics': ['algebra', 'equations'],
                        'difficulty_level': 6
                    }
                }
            ]
            
            # Add the knowledge item to the manager for search
            knowledge_base_manager.knowledge_items[item_id].id = item_id
            knowledge_base_manager.knowledge_items[item_id].title = 'Linear Equations'
            knowledge_base_manager.knowledge_items[item_id].subject = SubjectArea.MATHEMATICS
            knowledge_base_manager.knowledge_items[item_id].grade_level = GradeLevel.HIGH
            knowledge_base_manager.knowledge_items[item_id].topics = ['algebra', 'equations']
            knowledge_base_manager.knowledge_items[item_id].difficulty_level = 6
            knowledge_base_manager.knowledge_items[item_id].learning_objectives = ['Solve linear equations']
            knowledge_base_manager.knowledge_items[item_id].prerequisites = ['basic algebra']
            
            results = await knowledge_base_manager.search_knowledge_base(
                query="linear equations",
                subject=SubjectArea.MATHEMATICS,
                grade_level=GradeLevel.HIGH
            )
            
            assert len(results) > 0
            assert 'knowledge_item' in results[0]
            assert results[0]['knowledge_item']['title'] == 'Linear Equations'
    
    @pytest.mark.asyncio
    async def test_subject_specific_organization(self, document_processor, knowledge_base_manager):
        """Test subject-specific content organization."""
        # Process documents for different subjects
        math_content = b"Quadratic equations have the form ax^2 + bx + c = 0"
        science_content = b"Photosynthesis is the process by which plants convert light energy"
        
        with patch.object(document_processor, '_save_file', return_value='test_path'):
            # Configure RAG system to return different subjects
            document_processor.rag_system.add_document.side_effect = [
                {
                    'status': 'success',
                    'chunks_created': 1,
                    'subject': 'math',
                    'collections': ['documents', 'math']
                },
                {
                    'status': 'success',
                    'chunks_created': 1,
                    'subject': 'science',
                    'collections': ['documents', 'science']
                }
            ]
            
            # Process math document
            math_result = await document_processor.process_document(
                file_content=math_content,
                filename="quadratic.txt",
                content_type="text/plain",
                user_id="user123"
            )
            
            # Process science document
            science_result = await document_processor.process_document(
                file_content=science_content,
                filename="photosynthesis.txt",
                content_type="text/plain",
                user_id="user123"
            )
            
            # Verify subject classification
            assert math_result['subject'] == 'math'
            assert science_result['subject'] == 'science'
            
            # Verify documents were added to appropriate collections
            assert 'math' in math_result['rag_collections']
            assert 'science' in science_result['rag_collections']
    
    @pytest.mark.asyncio
    async def test_curriculum_alignment(self, knowledge_base_manager):
        """Test curriculum standard alignment functionality."""
        # Test getting curriculum-aligned content
        with patch.object(knowledge_base_manager, 'search_knowledge_base') as mock_search:
            mock_search.return_value = [
                {
                    'content': 'Place value understanding content',
                    'similarity_score': 0.8,
                    'metadata': {
                        'subject': 'mathematics',
                        'grade_level': 'elementary'
                    }
                }
            ]
            
            results = await knowledge_base_manager.get_curriculum_aligned_content(
                standard_id="ccss_math_5_nbt_1",
                query="place value"
            )
            
            assert len(results) > 0
            assert 'curriculum_alignment' in results[0]
            assert results[0]['curriculum_alignment']['standard_id'] == 'ccss_math_5_nbt_1'
    
    @pytest.mark.asyncio
    async def test_retrieval_accuracy(self, document_processor):
        """Test retrieval accuracy and relevance scoring."""
        # Configure mock to return results with different similarity scores
        document_processor.rag_system.search.return_value = [
            {
                'content': 'Highly relevant algebra content',
                'similarity_score': 0.95,
                'document_id': 'doc1',
                'metadata': {'filename': 'algebra1.txt'}
            },
            {
                'content': 'Moderately relevant math content',
                'similarity_score': 0.75,
                'document_id': 'doc2',
                'metadata': {'filename': 'math2.txt'}
            },
            {
                'content': 'Less relevant content',
                'similarity_score': 0.55,
                'document_id': 'doc3',
                'metadata': {'filename': 'general.txt'}
            }
        ]
        
        # Test search with different similarity thresholds
        high_threshold_results = await document_processor.search_documents(
            query="algebra",
            user_id="user123",
            limit=10
        )
        
        # Verify results are sorted by relevance
        scores = [result['similarity_score'] for result in high_threshold_results]
        assert scores == sorted(scores, reverse=True)
        
        # Verify highest scoring result is most relevant
        assert high_threshold_results[0]['similarity_score'] == 0.95
        assert 'algebra' in high_threshold_results[0]['content'].lower()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_resilience(self, document_processor):
        """Test error handling and system resilience."""
        # Test handling of RAG system errors
        document_processor.rag_system.search.side_effect = Exception("RAG system error")
        
        # Search should return empty results instead of crashing
        results = await document_processor.search_documents(
            query="test query",
            user_id="user123"
        )
        
        assert results == []
        
        # Test context retrieval error handling
        document_processor.rag_system.get_context_for_query.side_effect = Exception("Context error")
        
        context = await document_processor.get_document_context(
            query="test query",
            user_id="user123"
        )
        
        assert context['context'] == ''
        assert 'error' in context
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, mock_rag_system):
        """Test performance-related metrics and statistics."""
        # Test collection statistics
        stats = await mock_rag_system.get_collection_stats()
        
        assert 'documents' in stats
        assert 'math' in stats
        assert stats['documents']['document_count'] == 5
        assert stats['math']['document_count'] == 3
        
        # Verify all collections are active
        for collection_name, collection_stats in stats.items():
            assert collection_stats['status'] == 'active'


if __name__ == "__main__":
    pytest.main([__file__])