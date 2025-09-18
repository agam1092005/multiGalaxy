"""
RAG System API endpoints for Multi-Galaxy-Note.
Provides endpoints for document search, context retrieval, and knowledge base management.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ..services.rag_system import RAGSystem
from ..services.knowledge_base import KnowledgeBaseManager, SubjectArea, GradeLevel
from ..core.auth import get_current_user

router = APIRouter(prefix="/api/rag", tags=["RAG System"])

# Initialize services
rag_system = RAGSystem()
knowledge_base = KnowledgeBaseManager(rag_system)

# Pydantic models for request/response
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    subject: Optional[str] = Field(None, description="Subject filter")
    limit: int = Field(5, ge=1, le=50, description="Maximum number of results")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int
    query: str
    processing_time: float

class ContextRequest(BaseModel):
    query: str = Field(..., description="Query to get context for")
    subject: Optional[str] = Field(None, description="Subject filter")
    max_context_length: int = Field(4000, ge=500, le=10000, description="Maximum context length")

class ContextResponse(BaseModel):
    context: str
    sources: List[Dict[str, Any]]
    total_chunks: int
    subjects_covered: List[str]
    context_length: int
    query: str

class KnowledgeItemRequest(BaseModel):
    title: str = Field(..., description="Title of the knowledge item")
    content: str = Field(..., description="Content of the knowledge item")
    subject: str = Field(..., description="Subject area")
    grade_level: str = Field(..., description="Grade level")
    topics: List[str] = Field(default_factory=list, description="Related topics")
    difficulty_level: int = Field(5, ge=1, le=10, description="Difficulty level (1-10)")
    learning_objectives: List[str] = Field(default_factory=list, description="Learning objectives")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")

class KnowledgeItemResponse(BaseModel):
    id: str
    title: str
    subject: str
    grade_level: str
    status: str

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search for relevant documents using semantic similarity.
    """
    try:
        import time
        start_time = time.time()
        
        results = await rag_system.search(
            query=request.query,
            user_id=current_user["user_id"],
            subject=request.subject,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        processing_time = time.time() - start_time
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            query=request.query,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/context", response_model=ContextResponse)
async def get_context(
    request: ContextRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get relevant context for a query, optimized for LLM consumption.
    """
    try:
        context_result = await rag_system.get_context_for_query(
            query=request.query,
            user_id=current_user["user_id"],
            subject=request.subject,
            max_context_length=request.max_context_length
        )
        
        return ContextResponse(
            context=context_result["context"],
            sources=context_result["sources"],
            total_chunks=context_result["total_chunks"],
            subjects_covered=context_result["subjects_covered"],
            context_length=len(context_result["context"]),
            query=request.query
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context retrieval failed: {str(e)}")

@router.get("/stats")
async def get_rag_stats(current_user: dict = Depends(get_current_user)):
    """
    Get RAG system statistics.
    """
    try:
        rag_stats = await rag_system.get_collection_stats()
        kb_stats = await knowledge_base.get_knowledge_base_stats()
        
        return {
            "rag_collections": rag_stats,
            "knowledge_base": kb_stats,
            "user_id": current_user["user_id"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.post("/knowledge-base/add", response_model=KnowledgeItemResponse)
async def add_knowledge_item(
    request: KnowledgeItemRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new item to the knowledge base.
    """
    try:
        # Validate subject and grade level
        try:
            subject = SubjectArea(request.subject.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid subject: {request.subject}")
        
        try:
            grade_level = GradeLevel(request.grade_level.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid grade level: {request.grade_level}")
        
        item_id = await knowledge_base.add_knowledge_item(
            title=request.title,
            content=request.content,
            subject=subject,
            grade_level=grade_level,
            topics=request.topics,
            difficulty_level=request.difficulty_level,
            learning_objectives=request.learning_objectives,
            prerequisites=request.prerequisites,
            source="api"
        )
        
        return KnowledgeItemResponse(
            id=item_id,
            title=request.title,
            subject=request.subject,
            grade_level=request.grade_level,
            status="created"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add knowledge item: {str(e)}")

@router.get("/knowledge-base/search")
async def search_knowledge_base(
    query: str = Query(..., description="Search query"),
    subject: Optional[str] = Query(None, description="Subject filter"),
    grade_level: Optional[str] = Query(None, description="Grade level filter"),
    topics: Optional[str] = Query(None, description="Comma-separated topics"),
    difficulty_min: Optional[int] = Query(None, ge=1, le=10, description="Minimum difficulty"),
    difficulty_max: Optional[int] = Query(None, ge=1, le=10, description="Maximum difficulty"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search the knowledge base with filters.
    """
    try:
        # Parse optional parameters
        subject_enum = None
        if subject:
            try:
                subject_enum = SubjectArea(subject.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid subject: {subject}")
        
        grade_level_enum = None
        if grade_level:
            try:
                grade_level_enum = GradeLevel(grade_level.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid grade level: {grade_level}")
        
        topics_list = None
        if topics:
            topics_list = [topic.strip() for topic in topics.split(",")]
        
        difficulty_range = None
        if difficulty_min is not None or difficulty_max is not None:
            difficulty_range = (
                difficulty_min or 1,
                difficulty_max or 10
            )
        
        results = await knowledge_base.search_knowledge_base(
            query=query,
            subject=subject_enum,
            grade_level=grade_level_enum,
            topics=topics_list,
            difficulty_range=difficulty_range,
            limit=limit
        )
        
        return {
            "results": results,
            "total_results": len(results),
            "query": query,
            "filters": {
                "subject": subject,
                "grade_level": grade_level,
                "topics": topics_list,
                "difficulty_range": difficulty_range
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge base search failed: {str(e)}")

@router.get("/knowledge-base/curriculum/{standard_id}")
async def get_curriculum_content(
    standard_id: str,
    query: Optional[str] = Query(None, description="Additional search query"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get content aligned with specific curriculum standards.
    """
    try:
        results = await knowledge_base.get_curriculum_aligned_content(
            standard_id=standard_id,
            query=query
        )
        
        return {
            "results": results,
            "standard_id": standard_id,
            "query": query,
            "total_results": len(results)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Curriculum content retrieval failed: {str(e)}")

@router.get("/knowledge-base/taxonomy/{subject}/{grade_level}")
async def get_subject_taxonomy(
    subject: str,
    grade_level: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the topic taxonomy for a specific subject and grade level.
    """
    try:
        # Validate parameters
        try:
            subject_enum = SubjectArea(subject.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid subject: {subject}")
        
        try:
            grade_level_enum = GradeLevel(grade_level.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid grade level: {grade_level}")
        
        taxonomy = knowledge_base.get_subject_taxonomy(subject_enum, grade_level_enum)
        
        return {
            "subject": subject,
            "grade_level": grade_level,
            "taxonomy": taxonomy
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Taxonomy retrieval failed: {str(e)}")

@router.get("/knowledge-base/learning-path/{subject}/{grade_level}")
async def get_learning_path(
    subject: str,
    grade_level: str,
    current_topic: str = Query(..., description="Current topic"),
    target_topic: str = Query(..., description="Target topic"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a learning path from current topic to target topic.
    """
    try:
        # Validate parameters
        try:
            subject_enum = SubjectArea(subject.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid subject: {subject}")
        
        try:
            grade_level_enum = GradeLevel(grade_level.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid grade level: {grade_level}")
        
        learning_path = knowledge_base.get_learning_path(
            subject=subject_enum,
            grade_level=grade_level_enum,
            current_topic=current_topic,
            target_topic=target_topic
        )
        
        return {
            "subject": subject,
            "grade_level": grade_level,
            "current_topic": current_topic,
            "target_topic": target_topic,
            "learning_path": learning_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Learning path generation failed: {str(e)}")

@router.delete("/knowledge-base/{item_id}")
async def delete_knowledge_item(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a knowledge item from the knowledge base.
    """
    try:
        success = await knowledge_base.delete_knowledge_item(item_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge item not found")
        
        return {"status": "deleted", "item_id": item_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge item: {str(e)}")

@router.put("/knowledge-base/{item_id}")
async def update_knowledge_item(
    item_id: str,
    updates: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Update a knowledge item in the knowledge base.
    """
    try:
        success = await knowledge_base.update_knowledge_item(item_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge item not found")
        
        return {"status": "updated", "item_id": item_id, "updates": updates}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update knowledge item: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a document from the RAG system.
    """
    try:
        success = await rag_system.delete_document(document_id, current_user["user_id"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"status": "deleted", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")