# Zakerly - Enterprise AI-Powered Document Intelligence Platform

Zakerly is a professional, enterprise-grade microservices platform that transforms documents into intelligent, interactive knowledge bases using advanced AI technology. Built with Python LangChain, it provides document ingestion, intelligent chat, question generation, and lecture creation capabilities.

## 🏗️ Architecture

###  Architecture
- **API Gateway**: Central entry point with rate limiting and request routing
- **Ingestion Service**: Document processing, metadata extraction, and vector storage
- **Chat Service**: Intelligent chat, question generation, and lecture creation
- **Frontend**: Modern React-based user interface
- **Database**: PostgreSQL with pgvector extension for vector storage
- **Cache**: Redis for session management and caching
- **Monitoring**: Prometheus and Grafana for observability

### Technology Stack
- **Backend**: Python 3.11, FastAPI, LangChain, OpenAI GPT-4
- **Database**: PostgreSQL 16 with pgvector extension
- **Cache**: Redis 7
- **Frontend**: React 18, Material-UI
- **Containerization**: Docker & Docker Compose
- **Monitoring**: Prometheus, Grafana
- **Load Balancing**: Nginx

## 🚀 Features

### Document Management
- **Multi-format Support**: PDF, TXT, MD, DOC, DOCX
- **Intelligent Metadata Extraction**: AI-powered title, author, category detection
- **Duplicate Detection**: Hash-based duplicate prevention
- **Vector Storage**: Automatic chunking and embedding storage

### AI-Powered Chat
- **Contextual Conversations**: Memory-enabled chat sessions
- **Multi-intent Support**: Q&A, question generation, lecture creation
- **Hybrid Search**: Internal knowledge base + web search fallback
- **Session Management**: Persistent chat sessions with history

### Question Generation
- **Automated Quiz Creation**: Generate questions from document content
- **Multiple Question Types**: Multiple choice, true/false, open-ended
- **Difficulty Levels**: Easy, medium, hard question generation
- **Topic-based Generation**: Generate questions for specific topics

### Lecture Generation
- **Structured Lectures**: AI-generated lectures with proper formatting
- **Audience Adaptation**: Content adapted for different audience levels
- **Topic Discovery**: Automatic topic extraction from documents
- **Professional Formatting**: Markdown-formatted output with headings

## 📋 Prerequisites

- Docker and Docker Compose
- OpenAI API key
- (Optional) Google API key for Gemini
- (Optional) Tavily API key for web search

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd langchain_zakerly
```

### 2. Environment Configuration
```bash
cp .env.example .env
# Edit .env file with your API keys
```

### 3. Start the Platform
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access the Platform
- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **pgAdmin**: http://localhost:8080 (admin@zakerly.com / admin123)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin / admin123)

## 📖 Usage Guide

### Document Upload
1. Navigate to the Upload page
2. Drag and drop or select documents
3. Wait for processing and metadata extraction
4. Documents are automatically categorized and indexed

### Chat Interface
1. Go to the Chat page
2. Select a category and book
3. Choose chat mode:
   - **Answer Questions**: General Q&A
   - **Generate Questions**: Create quiz questions
   - **Generate Lecture**: Create structured lectures
4. Start chatting with your documents

### Book Management
1. Visit the Books page
2. Browse documents by category
3. Search by title or author
4. Start chat sessions directly from book cards
5. Delete documents when needed

## 🔧 API Documentation

### Core Endpoints

#### Document Management
```bash
# Upload document
POST /api/v1/upload
Content-Type: multipart/form-data

# List books
GET /api/v1/books?category_id=1

# Get book details
GET /api/v1/books/{book_id}

# Delete book
DELETE /api/v1/books/{book_id}
```

#### Chat Operations
```bash
# Send chat message
POST /api/v1/chat
{
  "category": "math",
  "book_title": "CALCULUS_BASICS",
  "session_id": "uuid",
  "user_message": "Explain derivatives",
  "intent": "answer_question"
}

# Generate questions
POST /api/v1/generate-questions
{
  "book_title": "CALCULUS_BASICS",
  "user_message": "Generate 5 questions about derivatives"
}

# Generate lecture
POST /api/v1/generate-lecture
{
  "book_title": "CALCULUS_BASICS",
  "topic": "derivatives",
  "audience": "university"
}
```

#### Session Management
```bash
# Create session
POST /api/v1/sessions

# Get session
GET /api/v1/sessions/{session_id}

# Get user sessions
GET /api/v1/users/{user_id}/sessions

# Get chat history
GET /api/v1/sessions/{session_id}/history
```

## 🏢 Enterprise Features

### Scalability
- **Horizontal Scaling**: Each microservice can be scaled independently
- **Load Balancing**: Nginx-based load balancing
- **Database Optimization**: Connection pooling and query optimization
- **Caching Strategy**: Redis-based caching for improved performance

### Security
- **Rate Limiting**: API rate limiting to prevent abuse
- **Input Validation**: Comprehensive input validation and sanitization
- **Error Handling**: Structured error handling and logging
- **Health Checks**: Service health monitoring

### Monitoring & Observability
- **Metrics Collection**: Prometheus-based metrics
- **Dashboards**: Grafana dashboards for monitoring
- **Logging**: Structured logging across all services
- **Health Checks**: Automated health monitoring

### Data Management
- **Backup Strategy**: Database backup and recovery procedures
- **Data Encryption**: Encrypted data storage
- **GDPR Compliance**: Data privacy and deletion capabilities
- **Audit Logging**: Complete audit trail

## 🔧 Development

### Local Development Setup
```bash
# Install dependencies for each service
cd services/ingestion && pip install -r requirements.txt
cd services/chat && pip install -r requirements.txt
cd services/gateway && pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Run services individually
python services/ingestion/main.py
python services/chat/main.py
python services/gateway/main.py
npm start --prefix frontend
```

### Testing
```bash
# Run backend tests
pytest services/*/tests/

# Run frontend tests
npm test --prefix frontend

# Integration tests
docker-compose -f docker-compose.test.yml up
```

### Database Migrations
```bash
# Connect to database
docker-compose exec postgres psql -U zakerly_user -d zakerly_db

# Run custom migrations
docker-compose exec postgres psql -U zakerly_user -d zakerly_db -f /path/to/migration.sql
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Check all services
curl http://localhost:8000/api/v1/status

# Individual service health
curl http://localhost:8001/health  # Ingestion
curl http://localhost:8002/health  # Chat
curl http://localhost:8000/health  # Gateway
```

### Metrics
- **Request Rates**: API request rates and response times
- **Error Rates**: Error rates and types
- **Resource Usage**: CPU, memory, and disk usage
- **Database Performance**: Query performance and connection counts

### Logs
```bash
# View service logs
docker-compose logs -f ingestion-service
docker-compose logs -f chat-service
docker-compose logs -f api-gateway

# Export logs
docker-compose logs --no-color > zakerly.log
```

## 🚀 Deployment

### Production Deployment
1. **Environment Setup**: Configure production environment variables
2. **SSL Certificates**: Set up SSL/TLS certificates
3. **Load Balancer**: Configure external load balancer
4. **Database**: Set up managed PostgreSQL instance
5. **Monitoring**: Configure production monitoring
6. **Backup**: Set up automated backups

### Docker Swarm Deployment
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml zakerly
```

### Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n zakerly
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For enterprise support and custom implementations:
- Email: support@zakerly.com
- Documentation: https://docs.zakerly.com
- Issues: GitHub Issues

## 🔄 Version History

- **v1.0.0**: Initial release with core functionality
- **v1.1.0**: Added question generation
- **v1.2.0**: Added lecture generation
- **v1.3.0**: Enhanced monitoring and observability

---

**Zakerly** - Transforming documents into intelligent knowledge bases for the enterprise.