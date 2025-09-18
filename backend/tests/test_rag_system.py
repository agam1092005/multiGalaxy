"""
Tests for RAG System Implementation.
Tests document embeddings, similarity search, and knowledge base management.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

from app.services.rag_system import RAGSystem
from app.services.knowledge_base import KnowledgeBaseManager, SubjectArea, GradeLevel


class TestRAGSystem:
    """Test cases for RAG System functionality."""
    
    @pytest.fixture
    def rag_system(self):
        """Create a test RAG system instance."""
        # Create temporary directory for ChromaDB
        temp_dir = tempfile.mkdtemp()
        
        with patch('app.services.rag_system.chromadb.PersistentClient') as mock_client:
            # Mock ChromaDB client and collections
            mock_collection = Mock()
            mock_collection.add = Mock()
            mock_collection.query = Mock()
            mock_collection.get = Mock()
            mock_collection.delete = Mock()
            mock_collection.count = Mock(return_value=0)
            
            mock_client_instance = Mock()
            mock_client_instance.get_collection = Mock(return_value=mock_collection)
            mock_client_instance.create_collection = Mock(return_value=mock_collection)
            mock_client.return_value = mock_client_instance
            
            rag_system = RAGSystem()
            rag_system.collections = {
                'documents': mock_collection,
                'math': mock_collection,
                'science': mock_collection,
                'language': mock_collection,
                'history': mock_collection,
                'general': mock_collection
            }
            
            yield rag_system
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_document_content(self):
        """Sample document content for testing."""
        return """
        Introduction to Algebra
        
        Algebra is a branch of mathematics that uses symbols and letters to represent numbers and quantities in formulas and equations. The main purpose of algebra is to find unknown values.
        
        Basic Concepts:
        1. Variables: Letters like x, y, z that represent unknown numbers
        2. Constants: Fixed numbers like 5, -3, 0.5
        3. Expressions: Combinations of variables and constants like 2x + 3
        4. Equations: Mathematical statements that show two expressions are equal, like 2x + 3 = 7
        
        Solving Linear Equations:
        To solve a linear equation, we need to isolate the variable on one side of the equation.
        
        Example: Solve 2x + 3 = 7
        Step 1: Subtract 3 from both sides: 2x = 4
        Step 2: Divide both sides by 2: x = 2
        
        Practice Problems:
        1. Solve: 3x - 5 = 10
        2. Solve: 2(x + 4) = 16
        3. Solve: x/3 + 2 = 5
        """
    
    @pytest.mark.asyncio
    async def test_add_document(self, rag_system, sample_document_content):
        """Test adding a document to the RAG system."""
        # Mock embedding generation
        with patch.object(rag_system, '_generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
            
            result = await rag_system.add_document(
                document_id="test_doc_1",
                content=sample_document_content,
                metadata={
                    'filename': 'algebra_intro.txt',
                    'user_id': 'user123',
                    'content_type': 'text/plain'
                }
            )
            
            assert result['status'] == 'success'
            assert result['document_id'] == 'test_doc_1'
            assert result['subject'] == 'math'  # Should be classified as math
            assert result['chunks_created'] > 0
            assert 'documents' in result['collections']
            assert 'math' in result['collections']
    
    @pytest.mark.asyncio
    async def test_subject_classification(self, rag_system):
        """Test automatic subject classification."""
        # Test math content
        math_content = "Solve the quadratic equation x^2 + 5x + 6 = 0 using the quadratic formula."
        subject = rag_system._classify_subject(math_content)
        assert subject == 'math'
        
        # Test science content
        science_content = "The periodic table organizes chemical elements by atomic number and electron configuration."
        subject = rag_system._classify_subject(science_content)
        assert subject == 'science'
        
        # Test language content
        language_content = "Grammar rules help us construct proper sentences with correct syntax and punctuation."
        subject = rag_system._classify_subject(language_content)
        assert subject == 'language'
        
        # Test general content
        general_content = "This is some general text that doesn't fit into specific categories."
        subject = rag_system._classify_subject(general_content)
        assert subject == 'general'
    
    def test_smart_chunking(self, rag_system):
        """Test intelligent text chunking."""
        # Test short text (should return as single chunk)
        short_text = "This is a short text that should remain as one chunk."
        chunks = rag_system._create_smart_chunks(short_text)
        assert len(chunks) == 1
        assert chunks[0] == short_text
        
        # Test long text (should be split into multiple chunks)
        long_text = "This is a paragraph. " * 100  # Create long text
        chunks = rag_system._create_smart_chunks(long_text)
        assert len(chunks) > 1
        
        # Test text with paragraphs
        paragraph_text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = rag_system._create_smart_chunks(paragraph_text)
        assert all(len(chunk) >= rag_system.min_chunk_size for chunk in chunks)
    
    def test_chunk_type_classification(self, rag_system):
        """Test chunk type classification."""
        # Mathematical content
        math_chunk = "Solve the equation: 2x + 3 = 7"
        chunk_type = rag_system._classify_chunk_type(math_chunk)
        assert chunk_type == 'mathematical'
        
        # Conceptual content
        concept_chunk = "The definition of photosynthesis is the process by which plants convert light energy into chemical energy."
        chunk_type = rag_system._classify_chunk_type(concept_chunk)
        assert chunk_type == 'conceptual'
        
        # Practical content
        practical_chunk = "Example problem: Calculate the area of a rectangle with length 5 and width 3."
        chunk_type = rag_system._classify_chunk_type(practical_chunk)
        assert chunk_type == 'practical'
        
        # Procedural content
        procedural_chunk = "Step 1: Identify the variables. Step 2: Set up the equation. Step 3: Solve for x."
        chunk_type = rag_system._classify_chunk_type(procedural_chunk)
        assert chunk_type == 'procedural'
    
    @pytest.mark.asyncio
    async def test_search_functionality(self, rag_system):
        """Test search functionality with similarity scoring."""
        # Mock search results
        mock_results = {
            'documents': [['This is about algebra and equations', 'Mathematics involves solving problems']],
            'metadatas': [[
                {'document_id': 'doc1', 'filename': 'math.txt', 'chunk_index': 0, 'user_id': 'user123'},
                {'document_id': 'doc2', 'filename': 'math2.txt', 'chunk_index': 1, 'user_id': 'user123'}
            ]],
            'distances': [[0.2, 0.4]]  # Lower distance = higher similarity
        }
        
        # Mock the collection query method
        for collection in rag_system.collections.values():
            collection.query.return_value = mock_results
        
        with patch.object(rag_system, '_generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = [[0.1] * 384]
            
            results = await rag_system.search(
                query="algebra equations",
                user_id="user123",
                limit=5,
                similarity_threshold=0.5
            )
            
            assert len(results) > 0
            assert all('similarity_score' in result for result in results)
            assert all('relevance_category' in result for result in results)
            assert all(result['similarity_score'] >= 0.5 for result in results)
            
            # Results should be sorted by similarity score (descending)
            scores = [result['similarity_score'] for result in results]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_get_context_for_query(self, rag_system):
        """Test context retrieval for LLM consumption."""
        # Mock search results
        with patch.object(rag_system, 'search') as mock_search:
            mock_search.return_value = [
                {
                    'content': 'Algebra is a branch of mathematics dealing with symbols.',
                    'similarity_score': 0.9,
                    'document_id': 'doc1',
                    'chunk_index': 0,
                    'metadata': {'filename': 'algebra_intro.txt', 'user_id': 'user123'}
                },
                {
                    'content': 'Linear equations can be solved by isolating the variable.',
                    'similarity_score': 0.8,
                    'document_id': 'doc1',
                    'chunk_index': 1,
                    'metadata': {'filename': 'algebra_intro.txt', 'user_id': 'user123'}
                }
            ]
            
            context_result = await rag_system.get_context_for_query(
                query="How to solve algebra problems",
                user_id="user123",
                max_context_length=1000
            )
            
            assert context_result['context'] != ''
            assert len(context_result['sources']) > 0
            assert context_result['total_chunks'] > 0
            assert context_result['context_length'] <= 1000
            assert 'algebra_intro.txt' in context_result['context']
    
    def test_relevance_categorization(self, rag_system):
        """Test relevance score categorization."""
        assert rag_system._categorize_relevance(0.95) == 'highly_relevant'
        assert rag_system._categorize_relevance(0.85) == 'very_relevant'
        assert rag_system._categorize_relevance(0.75) == 'relevant'
        assert rag_system._categorize_relevance(0.65) == 'somewhat_relevant'
        assert rag_system._categorize_relevance(0.55) == 'low_relevance'
    
    @pytest.mark.asyncio
    async def test_delete_document(self, rag_system):
        """Test document deletion from all collections."""
        # Mock get method to return some chunks
        mock_get_results = {
            'ids': ['doc1_chunk_0', 'doc1_chunk_1'],
            'documents': ['chunk1', 'chunk2'],
            'metadatas': [
                {'document_id': 'doc1', 'user_id': 'user123'},
                {'document_id': 'doc1', 'user_id': 'user123'}
            ]
        }
        
        for collection in rag_system.collections.values():
            collection.get.return_value = mock_get_results
        
        result = await rag_system.delete_document('doc1', 'user123')
        assert result is True
        
        # Verify delete was called on collections
        for collection in rag_system.collections.values():
            collection.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_collection_stats(self, rag_system):
        """Test getting collection statistics."""
        # Mock count method
        for collection in rag_system.collections.values():
            collection.count.return_value = 10
        
        stats = await rag_system.get_collection_stats()
        
        assert 'documents' in stats
        assert 'math' in stats
        assert 'science' in stats
        
        for collection_name, collection_stats in stats.items():
            assert 'document_count' in collection_stats
            assert 'status' in collection_stats
            assert collection_stats['document_count'] == 10
            assert collection_stats['status'] == 'active'


class TestKnowledgeBaseManager:
    """Test cases for Knowledge Base Manager."""
    
    @pytest.fixture
    def knowledge_base_manager(self, rag_system):
        """Create a test knowledge base manager."""
        with patch('app.services.knowledge_base.Path') as mock_path:
            mock_path.return_value.mkdir = Mock()
            mock_path.return_value.exists = Mock(return_value=False)
            
            kb_manager = KnowledgeBaseManager(rag_system)
            yield kb_manager
    
    @pytest.mark.asyncio
    async def test_add_knowledge_item(self, knowledge_base_manager):
        """Test adding a knowledge item."""
        with patch.object(knowledge_base_manager.rag_system, 'add_document') as mock_add:
            mock_add.return_value = {'status': 'success'}
            
            item_id = await knowledge_base_manager.add_knowledge_item(
                title="Quadratic Equations",
                content="A quadratic equation is a polynomial equation of degree 2.",
                subject=SubjectArea.MATHEMATICS,
                grade_level=GradeLevel.HIGH,
                topics=["algebra", "polynomials"],
                difficulty_level=7,
                learning_objectives=["Solve quadratic equations", "Graph parabolas"]
            )
            
            assert item_id.startswith('kb_')
            assert item_id in knowledge_base_manager.knowledge_items
            
            item = knowledge_base_manager.knowledge_items[item_id]
            assert item.title == "Quadratic Equations"
            assert item.subject == SubjectArea.MATHEMATICS
            assert item.grade_level == GradeLevel.HIGH
            assert item.difficulty_level == 7
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base(self, knowledge_base_manager):
        """Test searching the knowledge base with filters."""
        # Mock RAG system search
        with patch.object(knowledge_base_manager.rag_system, 'search') as mock_search:
            mock_search.return_value = [
                {
                    'content': 'Quadratic equations have the form ax^2 + bx + c = 0',
                    'similarity_score': 0.9,
                    'metadata': {
                        'knowledge_item_id': 'kb_test_1',
                        'subject': 'mathematics',
                        'grade_level': 'high',
                        'topics': ['algebra', 'polynomials'],
                        'difficulty_level': 7
                    }
                }
            ]
            
            # Add a test knowledge item
            knowledge_base_manager.knowledge_items['kb_test_1'] = Mock()
            knowledge_base_manager.knowledge_items['kb_test_1'].id = 'kb_test_1'
            knowledge_base_manager.knowledge_items['kb_test_1'].title = 'Quadratic Equations'
            knowledge_base_manager.knowledge_items['kb_test_1'].subject = SubjectArea.MATHEMATICS
            knowledge_base_manager.knowledge_items['kb_test_1'].grade_level = GradeLevel.HIGH
            knowledge_base_manager.knowledge_items['kb_test_1'].topics = ['algebra', 'polynomials']
            knowledge_base_manager.knowledge_items['kb_test_1'].difficulty_level = 7
            knowledge_base_manager.knowledge_items['kb_test_1'].learning_objectives = ['Solve quadratic equations']
            knowledge_base_manager.knowledge_items['kb_test_1'].prerequisites = ['linear equations']
            
            results = await knowledge_base_manager.search_knowledge_base(
                query="quadratic equations",
                subject=SubjectArea.MATHEMATICS,
                grade_level=GradeLevel.HIGH,
                limit=5
            )
            
            assert len(results) > 0
            assert 'knowledge_item' in results[0]
            assert results[0]['knowledge_item']['title'] == 'Quadratic Equations'
    
    def test_subject_taxonomy(self, knowledge_base_manager):
        """Test subject taxonomy retrieval."""
        taxonomy = knowledge_base_manager.get_subject_taxonomy(
            SubjectArea.MATHEMATICS, 
            GradeLevel.HIGH
        )
        
        assert 'algebra' in taxonomy
        assert 'geometry' in taxonomy
        assert 'calculus' in taxonomy
        assert isinstance(taxonomy['algebra'], list)
    
    def test_learning_path_generation(self, knowledge_base_manager):
        """Test learning path generation."""
        path = knowledge_base_manager.get_learning_path(
            subject=SubjectArea.MATHEMATICS,
            grade_level=GradeLevel.HIGH,
            current_topic="polynomials",
            target_topic="derivatives"
        )
        
        assert isinstance(path, list)
        assert len(path) > 0
        assert "derivatives" in path
    
    @pytest.mark.asyncio
    async def test_curriculum_aligned_content(self, knowledge_base_manager):
        """Test curriculum-aligned content retrieval."""
        # Mock search results
        with patch.object(knowledge_base_manager, 'search_knowledge_base') as mock_search:
            mock_search.return_value = [
                {
                    'content': 'Place value content',
                    'similarity_score': 0.8,
                    'metadata': {'subject': 'mathematics', 'grade_level': 'elementary'}
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
    async def test_knowledge_base_stats(self, knowledge_base_manager):
        """Test knowledge base statistics."""
        # Add some test items
        knowledge_base_manager.knowledge_items = {
            'item1': Mock(subject=SubjectArea.MATHEMATICS, grade_level=GradeLevel.HIGH, difficulty_level=5),
            'item2': Mock(subject=SubjectArea.SCIENCE, grade_level=GradeLevel.MIDDLE, difficulty_level=7),
            'item3': Mock(subject=SubjectArea.MATHEMATICS, grade_level=GradeLevel.HIGH, difficulty_level=6)
        }
        
        with patch.object(knowledge_base_manager.rag_system, 'get_collection_stats') as mock_stats:
            mock_stats.return_value = {'documents': {'document_count': 10}}
            
            stats = await knowledge_base_manager.get_knowledge_base_stats()
            
            assert stats['total_items'] == 3
            assert stats['by_subject']['mathematics'] == 2
            assert stats['by_subject']['science'] == 1
            assert stats['by_grade_level']['high'] == 2
            assert stats['by_grade_level']['middle'] == 1
    
    @pytest.mark.asyncio
    async def test_update_knowledge_item(self, knowledge_base_manager):
        """Test updating a knowledge item."""
        # Add a test item
        test_item = Mock()
        test_item.title = "Original Title"
        test_item.difficulty_level = 5
        test_item.subject = SubjectArea.MATHEMATICS
        test_item.grade_level = GradeLevel.HIGH
        test_item.topics = ['algebra']
        test_item.source = 'manual'
        knowledge_base_manager.knowledge_items['test_item'] = test_item
        
        with patch.object(knowledge_base_manager.rag_system, 'update_document_metadata') as mock_update:
            mock_update.return_value = True
            
            result = await knowledge_base_manager.update_knowledge_item(
                'test_item',
                {'title': 'Updated Title', 'difficulty_level': 8}
            )
            
            assert result is True
            assert test_item.title == 'Updated Title'
            assert test_item.difficulty_level == 8
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_item(self, knowledge_base_manager):
        """Test deleting a knowledge item."""
        # Add a test item
        knowledge_base_manager.knowledge_items['test_item'] = Mock()
        
        with patch.object(knowledge_base_manager.rag_system, 'delete_document') as mock_delete:
            mock_delete.return_value = True
            
            result = await knowledge_base_manager.delete_knowledge_item('test_item')
            
            assert result is True
            assert 'test_item' not in knowledge_base_manager.knowledge_items


@pytest.mark.asyncio
async def test_rag_integration():
    """Integration test for RAG system components."""
    # This test would verify the complete RAG pipeline
    # from document ingestion to context retrieval
    
    with patch('app.services.rag_system.chromadb.PersistentClient'):
        rag_system = RAGSystem()
        
        # Mock embedding generation
        with patch.object(rag_system, '_generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = [[0.1] * 384, [0.2] * 384]
            
            # Add document
            result = await rag_system.add_document(
                document_id="integration_test",
                content="This is a test document about mathematics and algebra.",
                metadata={'filename': 'test.txt', 'user_id': 'user123'}
            )
            
            assert result['status'] == 'success'
            
            # Mock search for context retrieval
            with patch.object(rag_system, 'search') as mock_search:
                mock_search.return_value = [
                    {
                        'content': 'This is a test document about mathematics and algebra.',
                        'similarity_score': 0.9,
                        'document_id': 'integration_test',
                        'chunk_index': 0,
                        'metadata': {'filename': 'test.txt', 'user_id': 'user123'}
                    }
                ]
                
                # Get context
                context = await rag_system.get_context_for_query(
                    query="mathematics",
                    user_id="user123"
                )
                
                assert context['context'] != ''
                assert len(context['sources']) > 0
                assert 'test.txt' in context['context']


if __name__ == "__main__":
    pytest.main([__file__])