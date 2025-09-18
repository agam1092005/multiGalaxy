# Multi-Galaxy-Note

An AI-powered educational platform that provides interactive tutoring through a digital whiteboard interface, combining speech recognition, computer vision, and natural language processing.

## Features

- Interactive digital whiteboard with real-time collaboration
- Multimodal AI input processing (speech, visual, text)
- AI-powered instant feedback and tutoring
- Deep learning analytics and progress tracking
- Subject-specific tutoring capabilities
- Privacy-focused design with secure data handling

## Technology Stack

### Frontend
- React.js with TypeScript
- Fabric.js for whiteboard functionality
- Socket.io for real-time communication
- Tailwind CSS for styling

### Backend
- FastAPI with Python
- WebSocket support for real-time features
- PostgreSQL for data storage
- Redis for caching and session management

### AI/ML
- Google Gemini Pro for natural language processing
- Google Speech-to-Text for speech recognition
- Google Text-to-Speech for voice responses
- ChromaDB for vector storage and RAG

## Development Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Docker and Docker Compose

### Quick Start with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd multi-galaxy-note
```

2. Start the development environment:
```bash
docker-compose up -d
```

3. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Testing

### Run Backend Tests
```bash
cd backend
pytest
```

### Run Frontend Tests
```bash
cd frontend
npm test
```

## Project Structure

```
multi-galaxy-note/
├── frontend/                 # React.js frontend
│   ├── src/
│   ├── public/
│   └── package.json
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/             # API routes
│   │   ├── core/            # Core configuration
│   │   ├── models/          # Database models
│   │   └── services/        # Business logic
│   ├── tests/
│   └── requirements.txt
├── docker-compose.yml        # Development environment
└── .github/workflows/        # CI/CD pipelines
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.