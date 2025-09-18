"""
Document upload and management API endpoints.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.security import HTTPBearer
import logging

from ..services.document_processor import DocumentProcessor
from ..core.auth import get_current_user
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Initialize document processor
document_processor = DocumentProcessor()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upload and process a document.
    
    Supports PDF, DOCX, PPTX, images (JPEG, PNG, TIFF), and text files.
    """
    try:
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=413,
                detail="File size exceeds 10MB limit"
            )
        
        # Validate file type
        if not file.content_type:
            raise HTTPException(
                status_code=400,
                detail="Could not determine file type"
            )
        
        # Process document
        result = await document_processor.process_document(
            file_content=file_content,
            filename=file.filename or "unknown",
            content_type=file.content_type,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Document uploaded and processed successfully",
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing document"
        )

@router.get("/")
async def get_user_documents(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all documents for the current user."""
    try:
        documents = await document_processor.get_user_documents(str(current_user.id))
        
        return {
            "success": True,
            "data": documents
        }
        
    except Exception as e:
        logger.error(f"Error getting user documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving documents"
        )

@router.get("/search")
async def search_documents(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of results"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Search for relevant content in user's documents."""
    try:
        results = await document_processor.search_documents(
            query=query,
            user_id=str(current_user.id),
            limit=limit
        )
        
        return {
            "success": True,
            "query": query,
            "data": results
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while searching documents"
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete a document and all its associated data."""
    try:
        success = await document_processor.delete_document(
            document_id=document_id,
            user_id=str(current_user.id)
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Document not found or access denied"
            )
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while deleting document"
        )

@router.get("/supported-types")
async def get_supported_file_types() -> Dict[str, Any]:
    """Get list of supported file types for upload."""
    return {
        "success": True,
        "data": {
            "supported_types": [
                {
                    "type": "PDF",
                    "mime_type": "application/pdf",
                    "extensions": [".pdf"],
                    "description": "Portable Document Format"
                },
                {
                    "type": "Word Document",
                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "extensions": [".docx"],
                    "description": "Microsoft Word Document"
                },
                {
                    "type": "PowerPoint Presentation",
                    "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "extensions": [".pptx"],
                    "description": "Microsoft PowerPoint Presentation"
                },
                {
                    "type": "JPEG Image",
                    "mime_type": "image/jpeg",
                    "extensions": [".jpg", ".jpeg"],
                    "description": "JPEG Image with OCR text extraction"
                },
                {
                    "type": "PNG Image",
                    "mime_type": "image/png",
                    "extensions": [".png"],
                    "description": "PNG Image with OCR text extraction"
                },
                {
                    "type": "TIFF Image",
                    "mime_type": "image/tiff",
                    "extensions": [".tiff", ".tif"],
                    "description": "TIFF Image with OCR text extraction"
                },
                {
                    "type": "Text File",
                    "mime_type": "text/plain",
                    "extensions": [".txt"],
                    "description": "Plain Text File"
                }
            ],
            "max_file_size": "10MB",
            "features": [
                "Text extraction from documents",
                "OCR for image-based text",
                "Content indexing for search",
                "Vector embeddings for semantic search"
            ]
        }
    }