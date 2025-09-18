#!/usr/bin/env python3
"""
Demonstration script for RAG System Implementation.
Shows the complete functionality of document processing, embedding, and retrieval.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rag_system import RAGSystem
from app.services.knowledge_base import KnowledgeBaseManager, SubjectArea, GradeLevel
from app.services.document_processor import DocumentProcessor


async def demo_rag_system():
    """Demonstrate RAG system functionality."""
    print("🚀 Multi-Galaxy-Note RAG System Demo")
    print("=" * 50)
    
    try:
        # Initialize RAG system
        print("\n1. Initializing RAG System...")
        rag_system = RAGSystem()
        print("✅ RAG System initialized with ChromaDB")
        
        # Initialize Knowledge Base Manager
        print("\n2. Initializing Knowledge Base Manager...")
        kb_manager = KnowledgeBaseManager(rag_system)
        print("✅ Knowledge Base Manager initialized")
        
        # Initialize Document Processor
        print("\n3. Initializing Document Processor...")
        doc_processor = DocumentProcessor()
        print("✅ Document Processor initialized")
        
        # Demo 1: Add sample documents
        print("\n" + "=" * 50)
        print("📚 DEMO 1: Adding Sample Documents")
        print("=" * 50)
        
        sample_documents = [
            {
                'id': 'algebra_intro',
                'content': '''
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
                ''',
                'metadata': {
                    'filename': 'algebra_intro.txt',
                    'user_id': 'demo_user',
                    'content_type': 'text/plain'
                }
            },
            {
                'id': 'photosynthesis',
                'content': '''
                Photosynthesis: The Process of Life
                
                Photosynthesis is the process by which plants, algae, and some bacteria convert light energy into chemical energy stored in glucose. This process is essential for life on Earth as it produces oxygen and serves as the foundation of most food chains.
                
                The Process:
                1. Light Absorption: Chlorophyll in plant leaves absorbs sunlight
                2. Water Uptake: Roots absorb water from the soil
                3. Carbon Dioxide Intake: Leaves take in CO2 from the atmosphere
                4. Chemical Reaction: Light energy converts CO2 and H2O into glucose and oxygen
                
                Chemical Equation:
                6CO2 + 6H2O + light energy → C6H12O6 + 6O2
                
                Importance:
                - Produces oxygen for respiration
                - Creates food for plants and animals
                - Removes carbon dioxide from atmosphere
                ''',
                'metadata': {
                    'filename': 'photosynthesis.txt',
                    'user_id': 'demo_user',
                    'content_type': 'text/plain'
                }
            }
        ]
        
        for doc in sample_documents:
            print(f"\n📄 Adding document: {doc['metadata']['filename']}")
            result = await rag_system.add_document(
                document_id=doc['id'],
                content=doc['content'],
                metadata=doc['metadata']
            )
            print(f"   ✅ Added {result['chunks_created']} chunks to '{result['subject']}' collection")
        
        # Demo 2: Search functionality
        print("\n" + "=" * 50)
        print("🔍 DEMO 2: Document Search")
        print("=" * 50)
        
        search_queries = [
            "How to solve linear equations?",
            "What is photosynthesis?",
            "algebra variables and constants",
            "chemical equation for photosynthesis"
        ]
        
        for query in search_queries:
            print(f"\n🔎 Searching for: '{query}'")
            results = await rag_system.search(
                query=query,
                user_id="demo_user",
                limit=3,
                similarity_threshold=0.6
            )
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"   {i}. Score: {result['similarity_score']:.3f} | Collection: {result['collection']}")
                    print(f"      Content: {result['content'][:100]}...")
            else:
                print("   No results found")
        
        # Demo 3: Context retrieval for LLM
        print("\n" + "=" * 50)
        print("🤖 DEMO 3: Context Retrieval for AI")
        print("=" * 50)
        
        context_query = "Explain how to solve algebra problems step by step"
        print(f"\n🎯 Getting context for: '{context_query}'")
        
        context_result = await rag_system.get_context_for_query(
            query=context_query,
            user_id="demo_user",
            max_context_length=1000
        )
        
        print(f"📊 Context Statistics:")
        print(f"   - Total chunks: {context_result['total_chunks']}")
        print(f"   - Context length: {context_result['context_length']} characters")
        print(f"   - Subjects covered: {context_result['subjects_covered']}")
        print(f"   - Sources: {len(context_result['sources'])}")
        
        print(f"\n📝 Generated Context:")
        print("-" * 30)
        print(context_result['context'][:500] + "..." if len(context_result['context']) > 500 else context_result['context'])
        
        # Demo 4: Knowledge Base Management
        print("\n" + "=" * 50)
        print("📖 DEMO 4: Knowledge Base Management")
        print("=" * 50)
        
        print("\n➕ Adding knowledge items...")
        
        knowledge_items = [
            {
                'title': 'Quadratic Formula',
                'content': 'The quadratic formula is used to solve quadratic equations of the form ax² + bx + c = 0. The formula is x = (-b ± √(b² - 4ac)) / 2a.',
                'subject': SubjectArea.MATHEMATICS,
                'grade_level': GradeLevel.HIGH,
                'topics': ['algebra', 'quadratic equations'],
                'difficulty_level': 7
            },
            {
                'title': 'Cell Structure',
                'content': 'Cells are the basic units of life. Plant cells have cell walls, chloroplasts, and large vacuoles. Animal cells have centrioles and smaller vacuoles.',
                'subject': SubjectArea.SCIENCE,
                'grade_level': GradeLevel.MIDDLE,
                'topics': ['biology', 'cells'],
                'difficulty_level': 5
            }
        ]
        
        for item in knowledge_items:
            item_id = await kb_manager.add_knowledge_item(**item)
            print(f"   ✅ Added: {item['title']} (ID: {item_id})")
        
        # Demo 5: Subject-specific search
        print("\n🎯 Subject-specific search...")
        
        math_results = await kb_manager.search_knowledge_base(
            query="quadratic equations",
            subject=SubjectArea.MATHEMATICS,
            limit=5
        )
        
        print(f"   📐 Math results: {len(math_results)} items found")
        for result in math_results:
            if 'knowledge_item' in result:
                kb_item = result['knowledge_item']
                print(f"      - {kb_item['title']} (Difficulty: {kb_item['difficulty_level']}/10)")
        
        # Demo 6: System Statistics
        print("\n" + "=" * 50)
        print("📊 DEMO 6: System Statistics")
        print("=" * 50)
        
        rag_stats = await rag_system.get_collection_stats()
        kb_stats = await kb_manager.get_knowledge_base_stats()
        
        print("\n📈 RAG System Collections:")
        for collection, stats in rag_stats.items():
            print(f"   - {collection}: {stats['document_count']} documents ({stats['status']})")
        
        print(f"\n📚 Knowledge Base:")
        print(f"   - Total items: {kb_stats['total_items']}")
        print(f"   - By subject: {kb_stats['by_subject']}")
        print(f"   - By grade level: {kb_stats['by_grade_level']}")
        
        # Demo 7: Curriculum Alignment
        print("\n" + "=" * 50)
        print("🎓 DEMO 7: Curriculum Alignment")
        print("=" * 50)
        
        print("\n📋 Available curriculum standards:")
        for standard_id, standard in kb_manager.curriculum_standards.items():
            print(f"   - {standard.standard_code}: {standard.name}")
        
        # Get curriculum-aligned content
        if kb_manager.curriculum_standards:
            first_standard = list(kb_manager.curriculum_standards.keys())[0]
            aligned_content = await kb_manager.get_curriculum_aligned_content(
                standard_id=first_standard,
                query="mathematics"
            )
            print(f"\n🎯 Content aligned with {first_standard}: {len(aligned_content)} items")
        
        print("\n" + "=" * 50)
        print("✅ RAG System Demo Completed Successfully!")
        print("=" * 50)
        
        print("\n🎉 Key Features Demonstrated:")
        print("   ✓ Document processing and chunking")
        print("   ✓ Semantic similarity search")
        print("   ✓ Subject-specific organization")
        print("   ✓ Context retrieval for AI systems")
        print("   ✓ Knowledge base management")
        print("   ✓ Curriculum alignment")
        print("   ✓ Performance monitoring")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_rag_system())