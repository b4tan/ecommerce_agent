# 🛍️ E-commerce AI Agent

An intelligent shopping assistant powered by Google Gemini AI that provides natural conversational product recommendations through text and image inputs. Built with advanced hybrid search combining FAISS vector embeddings and lexical matching for highly relevant product discovery.

## ✨ Key Features

### 🤖 AI-Powered Conversations
- **Natural Language Understanding**: Chat naturally about products like talking to a human assistant
- **Intent Classification**: Automatically detects when to show products vs. ask clarifying questions
- **Context-Aware**: Maintains conversation history for coherent multi-turn interactions
- **Multimodal Input**: Search using text queries or upload product images

### 🔍 Advanced Hybrid Search
- **FAISS Vector Search**: Semantic similarity using Google Gemini embeddings (`text-embedding-004`)
- **Lexical Matching**: Title and description keyword matching with phrase detection
- **Normalized Scoring**: Min-max normalization across semantic, lexical, rating, and review signals
- **Smart Filtering**: SQL-based filters for price, rating, department, brand, availability
- **Dynamic Results**: Returns up to 3 most relevant products per query

### 🛡️ Production-Ready Safeguards
- **Rate Limiting**: Per-user and global limits to prevent abuse
- **Cost Controls**: Configurable daily API call caps to control expenses
- **Image Upload Limits**: Size and format restrictions with separate rate limits
- **Health Monitoring**: `/stats` endpoint for real-time usage tracking

### 💾 Optimized Database
- **SQLite with FTS5**: Full-text search with BM25 ranking
- **Pre-built FAISS Index**: No runtime embedding costs for search
- **Typed Schema**: Proper data types for optimal query performance
- **Comprehensive Indexing**: 22+ B-tree indexes for fast filtering

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (HTML/JS)                       │
│  • Chat interface  • Image upload  • Product display             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────┴────────────────────────────────────┐
│                    Backend (FastAPI + LangGraph)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Rate Limiter │  │  AI Agent    │  │ Search API   │          │
│  │  Middleware  │→ │  (Gemini)    │→ │  (Hybrid)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Data Layer (SQLite + FAISS)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Products   │  │  FAISS Index │  │   FTS5 Index │          │
│  │   (SQLite)   │  │  (Vectors)   │  │  (Full-text) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for deployment)
- Google API Key (Gemini)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd ecommerce_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `backend/.env`:
```bash
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Build Database and Index

```bash
# Build SQLite database with FTS5
python scripts/build_db.py scripts/amazon-products.csv data/catalog.sqlite products

# Build FAISS vector index (requires GOOGLE_API_KEY)
python scripts/build_faiss_gemini.py
```

This creates:
- `data/catalog.sqlite` - Product database with FTS5
- `data/products.faiss` - FAISS vector index
- `data/products_ids.json` - ASIN mappings

### 4. Run Locally

```bash
# Start backend server
cd backend
python -m uvicorn gateway.app:app --reload --port 8001

# Open frontend
# Open client/index.html in your browser
# Or serve with: python -m http.server 8000 (from client/ directory)
```

Visit: `http://localhost:8000` (frontend) or `http://localhost:8001/docs` (API docs)

## 🐳 Docker Deployment

### Build and Run

```bash
# Build image
docker build -t ecommerce-agent .

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | *required* | Google Gemini API key |
| `EMBED_MODEL` | `text-embedding-004` | Gemini embedding model |
| `MAX_IMAGE_MB` | `20` | Max image upload size (MB) |
| `ENABLE_RATE_LIMITING` | `true` | Enable/disable rate limiting |
| `MAX_REQUESTS_PER_MINUTE` | `10` | Per-user request limit |
| `MAX_REQUESTS_PER_HOUR` | `100` | Per-user hourly limit |
| `MAX_REQUESTS_PER_DAY` | `500` | Per-user daily limit |
| `MAX_IMAGE_UPLOADS_PER_HOUR` | `20` | Per-user image upload limit |
| `MAX_IMAGE_UPLOADS_PER_DAY` | `100` | Per-user daily image limit |
| `MAX_DAILY_API_CALLS` | `1000` | Global daily API call cap |

## 📊 API Endpoints

### Chat
```bash
POST /chat
Content-Type: application/json

{
  "query": "I need running shoes under $100"
}
```

### Image Upload
```bash
POST /chat/upload
Content-Type: multipart/form-data

file: <image file>
query: "find similar products" (optional)
```

### Health Check
```bash
GET /
# Returns: {"message": "OK"}
```

### Usage Stats
```bash
GET /stats
# Returns: {
#   "rate_limiting_enabled": true,
#   "api_calls_today": 234,
#   "api_calls_reset_time": "2024-10-14T00:00:00"
# }
```

## 🔧 Project Structure

```
ecommerce_agent/
├── backend/
│   ├── agent/
│   │   ├── graph.py           # LangGraph agent definition
│   │   ├── tools.py           # Product search tool
│   │   ├── schema.py          # Agent data models
│   │   └── system_prompt.txt  # AI instructions
│   └── gateway/
│       ├── app.py             # FastAPI application
│       ├── chat.py            # Chat endpoint
│       ├── upload.py          # Image upload endpoint
│       ├── schema.py          # API schemas
│       └── rate_limiter.py    # Rate limiting logic
├── services/
│   ├── hybrid_search.py       # FAISS + lexical search
│   ├── catalog_search.py      # Search API gateway
│   ├── query_filter.py        # SQL filter compiler
│   └── schema.py              # Product data models
├── client/
│   ├── index.html             # Frontend UI
│   └── app.js                 # Frontend logic
├── scripts/
│   ├── build_db.py            # Database builder
│   └── build_faiss_gemini.py  # FAISS index builder
├── data/
│   ├── catalog.sqlite         # Product database
│   ├── products.faiss         # Vector index
│   └── products_ids.json      # ASIN mappings
├── tests/                     # Comprehensive test suite
├── Dockerfile                 # Docker image definition
├── docker-compose.yml         # Docker compose config
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_hybrid_search.py

# Run with coverage
pytest --cov=backend --cov=services
```

## 💰 Cost Estimation

With default rate limits (1000 API calls/day max):

| Usage Level | Queries/Day | Est. Monthly Cost |
|-------------|-------------|-------------------|
| Light | 100 text queries | ~$0.60 |
| Medium | 500 text queries | ~$3.00 |
| Heavy | 1000 text queries | ~$6.00 |
| With Images | 100 images/day | ~$60.00 |

**Important**: 
- Search uses pre-built FAISS index (no API cost)
- Only chat and image analysis call Gemini API
- Set up budget alerts in Google Cloud Console!

## 🚢 Hosting Options

### Recommended Platforms

1. **Google Cloud Run** (Serverless, auto-scaling)
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/ecommerce-agent
   gcloud run deploy --image gcr.io/PROJECT_ID/ecommerce-agent
   ```

2. **Railway.app** (Easiest deployment)
   ```bash
   railway login
   railway up
   ```

3. **Fly.io** (Global edge deployment)
   ```bash
   fly launch
   fly deploy
   ```

4. **DigitalOcean App Platform** (Simple, predictable pricing)
   - Push to Docker Hub
   - Deploy via DO Console

5. **VPS** (Full control)
   - DigitalOcean Droplet ($5/month)
   - Linode, Vultr, etc.

See deployment guides for detailed instructions.

## 🛡️ Security & Best Practices

### Production Checklist
- ✅ Set up Google Cloud budget alerts
- ✅ Enable rate limiting (`ENABLE_RATE_LIMITING=true`)
- ✅ Use environment variables for secrets
- ✅ Update CORS settings for your domain
- ✅ Monitor `/stats` endpoint regularly
- ✅ Start with conservative rate limits
- ✅ Set up HTTPS (most platforms provide this)

### Rate Limiting
Rate limiting is **enabled by default** to protect against:
- Abuse and spam
- Unexpected cost spikes
- API quota exhaustion

Adjust limits in `docker-compose.yml` based on your budget and expected traffic.

## 🔍 How It Works

### Search Flow
1. **User Query** → Frontend sends text/image to backend
2. **Rate Check** → Verify user hasn't exceeded limits
3. **AI Analysis** → Gemini analyzes query and decides to search
4. **Hybrid Search**:
   - FAISS finds semantically similar products (vector search)
   - Lexical matching finds keyword matches (title/description)
   - SQL filters apply constraints (price, rating, etc.)
   - Scores are normalized and combined
5. **Ranking** → Top 3 products returned
6. **AI Response** → Gemini formats results naturally
7. **Display** → Frontend shows products with images

### Search Scoring
```python
total_score = (
    0.4 × semantic_score +    # FAISS similarity
    0.3 × lexical_score +     # Keyword matching
    0.2 × rating_score +      # Product rating
    0.1 × review_score        # Review count
)
```

All scores normalized to [0, 1] per query for fair comparison.

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Add authentication system
- Implement Redis for distributed rate limiting
- Add response caching
- Support more product attributes
- Improve search relevance
- Add conversation memory persistence

## 📝 License

MIT License - feel free to use for personal or commercial projects.

## 🆘 Troubleshooting

### "Module not found" errors
```bash
# Ensure you're in the right directory
cd backend
python -m uvicorn gateway.app:app --reload --port 8001
```

### "GOOGLE_API_KEY not found"
```bash
# Create backend/.env with your API key
echo "GOOGLE_API_KEY=your_key_here" > backend/.env
```

### Database not found
```bash
# Rebuild database and index
python scripts/build_db.py scripts/amazon-products.csv data/catalog.sqlite products
python scripts/build_faiss_gemini.py
```

### Rate limit errors (429)
```bash
# Temporarily disable for testing
# In docker-compose.yml:
ENABLE_RATE_LIMITING=false
```

### High costs
```bash
# Check usage
curl http://localhost:8001/stats

# Lower limits in docker-compose.yml
MAX_DAILY_API_CALLS=100
```

## 📚 Documentation

- **Architecture**: See code comments in `backend/agent/graph.py`
- **Search Algorithm**: See `services/hybrid_search.py`
- **API Reference**: Visit `/docs` endpoint when server is running
- **System Prompt**: See `backend/agent/system_prompt.txt`

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - AI agent orchestration
- [Google Gemini](https://ai.google.dev/) - LLM and embeddings
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [SQLite FTS5](https://www.sqlite.org/fts5.html) - Full-text search

---

**Ready to deploy?** Make sure to set up budget alerts in Google Cloud Console first! 💰
