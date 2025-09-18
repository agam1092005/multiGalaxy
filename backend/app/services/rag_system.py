"""
RAG (Retrieval-Augmented Generation) System for Multi-Galaxy-Note.
Handles document embeddings, similarity search, and knowledge base management.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import asyncio

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class RAGSystem:
    """
    Comprehensive RAG system for document retrieval and knowledge management.
    Supports subject-specific organization and advanced similarity search.
    """
    
    def __init__(self):
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384  # Dimension for all-MiniLM-L6-v2
        
        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize collections for different purposes
        self.collections = {
            'documents': self._get_or_create_collection('documents', 'General document storage'),
            'math': self._get_or_create_collection('math', 'Mathematics-specific content'),
            'science': self._get_or_create_collection('science', 'Science-specific content'),
            'language': self._get_or_create_collection('language', 'Language arts content'),
            'history': self._get_or_create_collection('history', 'History and social studies'),
            'general': self._get_or_create_collection('general', 'General knowledge base')
        }
        
        # Subject mapping for automatic categorization
        self.subject_keywords = {
            'math': ['mathematics', 'algebra', 'geometry', 'calculus', 'statistics', 'equation', 'formula', 'theorem'],
            'science': ['physics', 'chemistry', 'biology', 'experiment', 'hypothesis', 'molecule', 'atom', 'cell'],
            'language': ['grammar', 'literature', 'writing', 'essay', 'poetry', 'vocabulary', 'syntax'],
            'history': ['historical', 'timeline', 'civilization', 'war', 'revolution', 'ancient', 'medieval']
        }
        
        # Chunk configuration
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.min_chunk_size = 50  # Reduced minimum chunk size for better handling of short texts
        
    def _get_or_create_collection(self, name: str, description: str):
        """Get or create a ChromaDB collection."""
        try:
            return self.chroma_client.get_collection(name)
        except ValueError:
            return self.chroma_client.create_collection(
                name=name,
                metadata={"description": description}
            )
    
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a document to the RAG system with automatic subject classification.
        
        Args:
            document_id: Unique identifier for the document
            content: Text content of the document
            metadata: Additional metadata (filename, user_id, etc.)
            subject: Optional subject classification
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Determine subject if not provided
            if not subject:
                subject = self._classify_subject(content)
            
            # Create text chunks
            chunks = self._create_smart_chunks(content)
            
            if not chunks:
                raise ValueError("No valid chunks could be created from the document")
            
            # Generate embeddings for all chunks
            embeddings = await self._generate_embeddings(chunks)
            
            # Prepare chunk data
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **metadata,
                    'document_id': document_id,
                    'chunk_index': i,
                    'chunk_size': len(chunk),
                    'subject': subject,
                    'created_at': datetime.now().isoformat(),
                    'chunk_type': self._classify_chunk_type(chunk)
                }
                chunk_metadatas.append(chunk_metadata)
            
            # Store in appropriate collections
            collections_used = []
            
            # Store in general documents collection
            self.collections['documents'].add(
                embeddings=embeddings,
                documents=chunks,
                ids=chunk_ids,
                metadatas=chunk_metadatas
            )
            collections_used.append('documents')
            
            # Store in subject-specific collection if applicable
            if subject in self.collections:
                self.collections[subject].add(
                    embeddings=embeddings,
                    documents=chunks,
                    ids=[f"{subject}_{chunk_id}" for chunk_id in chunk_ids],
                    metadatas=chunk_metadatas
                )
                collections_used.append(subject)
            
            logger.info(f"Added document {document_id} with {len(chunks)} chunks to collections: {collections_used}")
            
            return {
                'document_id': document_id,
                'chunks_created': len(chunks),
                'subject': subject,
                'collections': collections_used,
                'embedding_dimension': self.embedding_dimension,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error adding document {document_id}: {str(e)}")
            raise ValueError(f"Failed to add document to RAG system: {str(e)}")
    
    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant content using semantic similarity.
        
        Args:
            query: Search query
            user_id: Optional user ID to filter results
            subject: Optional subject to search within
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            include_metadata: Whether to include full metadata
            
        Returns:
            List of relevant chunks with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = await self._generate_embeddings([query])
            query_embedding = query_embedding[0]
            
            # Determine which collections to search
            collections_to_search = []
            if subject and subject in self.collections:
                collections_to_search.append(subject)
            else:
                # Search all subject-specific collections
                collections_to_search.extend(['math', 'science', 'language', 'history', 'general'])
            
            all_results = []
            
            for collection_name in collections_to_search:
                try:
                    collection = self.collections[collection_name]
                    
                    # Build where clause for filtering
                    where_clause = {}
                    if user_id:
                        where_clause['user_id'] = user_id
                    
                    # Search in collection
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=limit * 2,  # Get more results to filter later
                        where=where_clause if where_clause else None,
                        include=['documents', 'metadatas', 'distances']
                    )
                    
                    # Process results
                    if results['documents'] and results['documents'][0]:
                        for i in range(len(results['documents'][0])):
                            similarity_score = 1 - results['distances'][0][i]  # Convert distance to similarity
                            
                            if similarity_score >= similarity_threshold:
                                result = {
                                    'content': results['documents'][0][i],
                                    'similarity_score': similarity_score,
                                    'collection': collection_name,
                                    'document_id': results['metadatas'][0][i]['document_id'],
                                    'chunk_index': results['metadatas'][0][i]['chunk_index']
                                }
                                
                                if include_metadata:
                                    result['metadata'] = results['metadatas'][0][i]
                                
                                all_results.append(result)
                
                except Exception as e:
                    logger.warning(f"Error searching collection {collection_name}: {str(e)}")
                    continue
            
            # Sort by similarity score and limit results
            all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            final_results = all_results[:limit]
            
            # Add relevance ranking
            for i, result in enumerate(final_results):
                result['rank'] = i + 1
                result['relevance_category'] = self._categorize_relevance(result['similarity_score'])
            
            logger.info(f"Search for '{query}' returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching RAG system: {str(e)}")
            return []
    
    async def get_context_for_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        subject: Optional[str] = None,
        max_context_length: int = 4000
    ) -> Dict[str, Any]:
        """
        Get relevant context for a query, optimized for LLM consumption.
        
        Args:
            query: The query to find context for
            user_id: Optional user ID for personalized results
            subject: Optional subject filter
            max_context_length: Maximum total length of context
            
        Returns:
            Dictionary with formatted context and metadata
        """
        try:
            # Search for relevant chunks
            search_results = await self.search(
                query=query,
                user_id=user_id,
                subject=subject,
                limit=10,
                similarity_threshold=0.6
            )
            
            if not search_results:
                return {
                    'context': '',
                    'sources': [],
                    'total_chunks': 0,
                    'subjects_covered': []
                }
            
            # Build context string within length limit
            context_parts = []
            sources = []
            subjects_covered = set()
            current_length = 0
            
            for result in search_results:
                chunk_content = result['content']
                chunk_length = len(chunk_content)
                
                # Check if adding this chunk would exceed the limit
                if current_length + chunk_length > max_context_length:
                    # Try to fit a truncated version
                    remaining_space = max_context_length - current_length
                    if remaining_space > 200:  # Only if we have reasonable space left
                        chunk_content = chunk_content[:remaining_space-3] + "..."
                        context_parts.append(f"[Source: {result['metadata']['filename']}]\n{chunk_content}")
                        current_length = max_context_length
                    break
                
                # Add full chunk
                context_parts.append(f"[Source: {result['metadata']['filename']}]\n{chunk_content}")
                current_length += chunk_length + len(f"[Source: {result['metadata']['filename']}]\n")
                
                # Track metadata
                sources.append({
                    'document_id': result['document_id'],
                    'filename': result['metadata']['filename'],
                    'similarity_score': result['similarity_score'],
                    'chunk_index': result['chunk_index']
                })
                
                if 'subject' in result['metadata']:
                    subjects_covered.add(result['metadata']['subject'])
            
            context = "\n\n".join(context_parts)
            
            return {
                'context': context,
                'sources': sources,
                'total_chunks': len(context_parts),
                'subjects_covered': list(subjects_covered),
                'context_length': len(context),
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Error getting context for query: {str(e)}")
            return {
                'context': '',
                'sources': [],
                'total_chunks': 0,
                'subjects_covered': [],
                'error': str(e)
            }
    
    def _classify_subject(self, content: str) -> str:
        """Classify content into subject categories based on keywords."""
        content_lower = content.lower()
        subject_scores = {}
        
        for subject, keywords in self.subject_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                subject_scores[subject] = score
        
        if subject_scores:
            return max(subject_scores, key=subject_scores.get)
        return 'general'
    
    def _classify_chunk_type(self, chunk: str) -> str:
        """Classify the type of content in a chunk."""
        chunk_lower = chunk.lower()
        
        # Check for different content types
        if any(indicator in chunk_lower for indicator in ['equation', 'formula', '=', '+', '-', '*', '/']):
            return 'mathematical'
        elif any(indicator in chunk_lower for indicator in ['definition', 'concept', 'theory']):
            return 'conceptual'
        elif any(indicator in chunk_lower for indicator in ['example', 'problem', 'exercise']):
            return 'practical'
        elif any(indicator in chunk_lower for indicator in ['step', 'procedure', 'method']):
            return 'procedural'
        else:
            return 'general'
    
    def _create_smart_chunks(self, text: str) -> List[str]:
        """
        Create intelligent text chunks with semantic boundaries.
        """
        if len(text) <= self.chunk_size:
            return [text] if len(text) >= self.min_chunk_size else []
        
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                
                # If paragraph itself is too long, split it
                if len(paragraph) > self.chunk_size:
                    sub_chunks = self._split_long_paragraph(paragraph)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add remaining chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """Split a long paragraph into smaller chunks at sentence boundaries."""
        sentences = paragraph.split('. ')
        chunks = []
        current_chunk = ""
        
        for i, sentence in enumerate(sentences):
            # Add period back except for last sentence
            if i < len(sentences) - 1:
                sentence += '. '
            
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence
        
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        try:
            # Use asyncio to run the embedding generation in a thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, 
                self.embedding_model.encode, 
                texts
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def _categorize_relevance(self, similarity_score: float) -> str:
        """Categorize relevance based on similarity score."""
        if similarity_score >= 0.9:
            return 'highly_relevant'
        elif similarity_score >= 0.8:
            return 'very_relevant'
        elif similarity_score >= 0.7:
            return 'relevant'
        elif similarity_score >= 0.6:
            return 'somewhat_relevant'
        else:
            return 'low_relevance'
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections."""
        stats = {}
        
        for name, collection in self.collections.items():
            try:
                count = collection.count()
                stats[name] = {
                    'document_count': count,
                    'status': 'active'
                }
            except Exception as e:
                stats[name] = {
                    'document_count': 0,
                    'status': 'error',
                    'error': str(e)
                }
        
        return stats
    
    async def delete_document(self, document_id: str, user_id: Optional[str] = None) -> bool:
        """Delete all chunks of a document from all collections."""
        try:
            deleted_count = 0
            
            for collection_name, collection in self.collections.items():
                try:
                    # Build where clause
                    where_clause = {'document_id': document_id}
                    if user_id:
                        where_clause['user_id'] = user_id
                    
                    # Get matching chunks
                    results = collection.get(where=where_clause)
                    
                    if results['ids']:
                        # Delete the chunks
                        collection.delete(ids=results['ids'])
                        deleted_count += len(results['ids'])
                        logger.info(f"Deleted {len(results['ids'])} chunks from {collection_name}")
                
                except Exception as e:
                    logger.warning(f"Error deleting from collection {collection_name}: {str(e)}")
                    continue
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False
    
    async def update_document_metadata(
        self, 
        document_id: str, 
        metadata_updates: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """Update metadata for all chunks of a document."""
        try:
            updated_count = 0
            
            for collection_name, collection in self.collections.items():
                try:
                    # Build where clause
                    where_clause = {'document_id': document_id}
                    if user_id:
                        where_clause['user_id'] = user_id
                    
                    # Get matching chunks
                    results = collection.get(where=where_clause)
                    
                    if results['ids']:
                        # Update metadata for each chunk
                        for i, chunk_id in enumerate(results['ids']):
                            current_metadata = results['metadatas'][i]
                            updated_metadata = {**current_metadata, **metadata_updates}
                            
                            # ChromaDB doesn't have direct update, so we need to delete and re-add
                            collection.delete(ids=[chunk_id])
                            collection.add(
                                embeddings=[results['embeddings'][i]] if 'embeddings' in results else None,
                                documents=[results['documents'][i]],
                                ids=[chunk_id],
                                metadatas=[updated_metadata]
                            )
                        
                        updated_count += len(results['ids'])
                
                except Exception as e:
                    logger.warning(f"Error updating metadata in collection {collection_name}: {str(e)}")
                    continue
            
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"Error updating document metadata {document_id}: {str(e)}")
            return False