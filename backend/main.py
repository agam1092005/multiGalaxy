from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
from app.database import engine, Base
from app.api.auth import router as auth_router
from app.api.computer_vision import router as cv_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.ai_reasoning import router as ai_reasoning_router
from app.api.tts_whiteboard import router as tts_whiteboard_router
from app.api.analytics import router as analytics_router
from app.websocket.manager import connection_manager

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Multi-Galaxy-Note API",
    description="AI-powered educational platform with multimodal tutoring",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(cv_router, prefix="/api")
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(rag_router)
app.include_router(ai_reasoning_router, prefix="/api")
app.include_router(tts_whiteboard_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "multi-galaxy-note-api"}

# Mount Socket.IO app
socket_app = connection_manager.get_asgi_app()
app.mount("/socket.io", socket_app)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )