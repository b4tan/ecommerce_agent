# Ecommerce AI Agent

An intelligent shopping assistant that combines AI-powered conversational interface with advanced product search capabilities. Users can chat naturally about products and get relevant recommendations through both text and image inputs.

## 🚀 Features

### **Conversational Shopping**
- **Natural Language Interface**: Chat with the AI agent like you would with a human shopping assistant
- **Intent Classification**: Automatically detects whether you're asking questions, requesting recommendations, or just chatting
- **Smart Product Display**: Shows products only when making actual recommendations

### **Advanced Search Capabilities**
- **Full-Text Search (FTS5)**: Powered by SQLite FTS5 with optimized relevance scoring
- **Multi-Modal Input**: Search using text queries or upload product images
- **Intelligent Filtering**: Automatic semantic filtering to exclude irrelevant categories
- **Dynamic Results**: Returns 1-3 products based on what's actually found

### **Robust Database**
- **Typed Schema**: Proper SQLite data types (INTEGER, REAL, TEXT) for optimal performance
- **Comprehensive Indexing**: 22 B-tree indexes for fast filtering and sorting
- **FTS5 Integration**: 8 searchable text columns with weighted BM25 relevance scoring
- **Auto-Sync Triggers**: FTS index automatically stays in sync with data updates

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (HTML/JS)     │◄──►│   (FastAPI)     │◄──►│   (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌─────────┐            ┌─────────────┐        ┌─────────────┐
    │ Chat UI │            │ LangGraph   │        │ Products    │
    │ Image   │            │ Agent       │        │ FTS Index   │
    │ Upload  │            │ Tools       │        │ B-tree Idx  │
    └─────────┘            └─────────────┘        └─────────────┘
```

### **Components**

#### **Frontend (`client/`)**
- **Modern Chat Interface**: Clean, responsive design with message bubbles
- **Image Upload**: Drag-and-drop or click to upload product images
- **Real-time Updates**: Typing indicators and smooth message flow
- **Product Display**: Inline product cards with images, prices, and ratings

#### **Backend (`backend/`)**
- **FastAPI Gateway**: RESTful API with CORS support
- **LangGraph Agent**: Conversational AI with structured output
- **Google Gemini Integration**: LLM for natural language understanding
- **Tool System**: Extensible tool architecture for product search

#### **Services (`services/`)**
- **Catalog Search**: Advanced FTS5 search with relevance boosting
- **Catalog API**: Clean abstraction layer for database operations
- **Schema Management**: Pydantic models for type safety

#### **Database (`data/`)**
- **SQLite**: Lightweight, embedded database
- **FTS5 Virtual Table**: Full-text search with 8 indexed columns
- **B-tree Indexes**: 22 indexes for fast filtering and sorting
- **Typed Schema**: Proper data types for optimal performance

## 🔧 Setup & Installation

### **Prerequisites**
- Python 3.8+
- Node.js (for frontend serving)
- Google Gemini API key

### **1. Clone and Install**
```bash
git clone <repository-url>
cd ecommerce_agent
pip install -r requirements.txt
```

### **2. Database Setup**
```bash
# Build the database from CSV
python scripts/build_db.py scripts/amazon-products.csv ./data/catalog.sqlite products

# This creates:
# - Typed table with 55 columns
# - 22 B-tree indexes for fast queries
# - FTS5 virtual table with 8 searchable columns
# - Auto-sync triggers for data consistency
```

### **3. Environment Configuration**
```bash
# Create backend/.env file
echo "GOOGLE_API_KEY=your_gemini_api_key_here" > backend/.env
```

### **4. Run the Application**
```bash
# Terminal 1: Start backend server
cd backend
python -m uvicorn gateway.app:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Serve frontend (optional)
cd client
python -m http.server 3000
```

### **5. Access the Application**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## 🔍 How It Works

### **Search Flow**

#### **Text Search**
1. **User Query**: "show me black shirts for men"
2. **Intent Detection**: AI classifies as RECOMMENDATION
3. **Query Processing**: 
   - Converts to AND logic: "black AND shirt"
   - Adds semantic filtering: excludes accessories, electronics
   - Applies department filter: Men's only
4. **FTS5 Search**: 
   - Searches 8 indexed columns with weighted BM25 scoring
   - Title matches get +10 boost, description +5 boost
5. **Result Processing**: Returns 1-3 products based on actual matches
6. **Response**: Natural language + product cards

#### **Image Search**
1. **Image Upload**: User uploads product photo
2. **AI Vision**: Gemini analyzes image and extracts features
3. **Query Generation**: AI creates search query from image description
4. **Product Search**: Same FTS5 search process as text
5. **Results**: Relevant products based on visual similarity

### **Database Schema**

#### **Products Table (55 columns)**
```sql
CREATE TABLE products (
    asin TEXT PRIMARY KEY,           -- Amazon Standard Identification Number
    title TEXT,                      -- Product title
    brand TEXT,                      -- Brand name
    description TEXT,                -- Product description
    final_price REAL,                -- Current price
    rating REAL,                     -- Average rating (0-5)
    reviews_count INTEGER,           -- Number of reviews
    department TEXT,                 -- Men/Women/Unisex
    categories TEXT,                 -- JSON array of categories
    image_url TEXT,                  -- Product image URL
    url TEXT,                        -- Product page URL
    -- ... 44 more columns
);
```

#### **FTS5 Index (8 columns)**
```sql
CREATE VIRTUAL TABLE products_fts USING fts5(
    title,              -- Weight: 8.0 (highest priority)
    brand,              -- Weight: 5.0
    categories,         -- Weight: 4.0
    description,        -- Weight: 3.0
    features,           -- Weight: 2.0
    plus_content,       -- Weight: 1.5
    top_review,         -- Weight: 1.2
    department,         -- Weight: 1.0
    content='products',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 1 tokenchars "._-"'
);
```

#### **B-tree Indexes (22 indexes)**
- **Single-column**: brand, department, final_price, rating, etc.
- **Composite**: (brand, final_price), (department, final_price), etc.
- **Special**: title COLLATE NOCASE for case-insensitive search

## 🎯 Key Features Explained

### **Smart Search Relevance**
- **AND Logic**: "black shirt" becomes "black AND shirt" (not OR)
- **Semantic Filtering**: Automatically excludes irrelevant categories
- **Weighted BM25**: Title matches rank higher than description matches
- **Dynamic Results**: Shows 1-3 products based on actual availability

### **Intent Classification**
The AI automatically classifies responses as:
- **RECOMMENDATION**: When showing products (even with follow-up questions)
- **QUESTION**: When asking for clarification without products
- **CONVERSATION**: When just chatting or answering questions

### **Image Processing**
- **Multi-modal Input**: Upload images to find similar products
- **AI Vision**: Gemini analyzes images and extracts product features
- **Smart Matching**: Converts visual features to searchable text queries

## 📊 Performance

### **Search Performance**
- **FTS5 Queries**: ~0.03 seconds for complex searches
- **B-tree Filters**: Sub-millisecond for price/rating ranges
- **Total Response**: 2-6 seconds (mostly AI processing time)

### **Database Optimization**
- **Indexed Search**: All common filter combinations have indexes
- **FTS5 Virtual Table**: Fast full-text search with relevance scoring
- **Typed Schema**: Proper data types for optimal storage and queries

## 🛠️ Development

### **Adding New Search Features**
1. **Extend FTS Columns**: Add to `FTS_CANDIDATE_ORDER` in `build_db.py`
2. **Update Search Logic**: Modify `services/catalog_search.py`
3. **Add Filters**: Extend `_compile_filters()` function
4. **Rebuild Database**: Run `build_db.py` to update FTS index

### **Adding New Tools**
1. **Create Tool**: Add function in `backend/agent/tools.py`
2. **Register Tool**: Add to `TOOLS` list in `backend/agent/graph.py`
3. **Update Prompt**: Modify system prompt if needed

### **Testing**
```bash
# Run comprehensive tests
python -m pytest tests/ -v

# Test specific components
python -m pytest tests/catalog_search_test.py -v
python -m pytest tests/tool_test.py -v
```

## 🚨 Troubleshooting

### **Common Issues**

#### **"Failed to fetch" Error**
- Check if backend server is running on port 8001
- Verify API endpoint in `client/app.js`

#### **"Quota exceeded" Error**
- Google Gemini free tier has 250 requests/day limit
- Switch to `gemini-1.5-flash` or upgrade to paid plan

#### **Search Returns Wrong Results**
- Check FTS index is populated: `SELECT COUNT(*) FROM products_fts`
- Verify semantic filtering rules in `catalog_search.py`

#### **Slow Search Performance**
- Database search is fast (~0.03s), slowness is from AI processing
- Consider caching frequent queries
- Use faster Gemini model

### **Database Issues**
```bash
# Rebuild database from scratch
rm data/catalog.sqlite
python scripts/build_db.py scripts/amazon-products.csv ./data/catalog.sqlite products

# Check FTS index
sqlite3 data/catalog.sqlite "SELECT COUNT(*) FROM products_fts;"

# Verify indexes
sqlite3 data/catalog.sqlite "PRAGMA index_list('products');"
```

## 📈 Future Enhancements

### **Planned Features**
- **Image Similarity**: Direct image-to-image matching
- **Query Caching**: Cache frequent searches for faster responses
- **User Preferences**: Remember user's style and brand preferences
- **Price Alerts**: Notify when products go on sale
- **Multi-language**: Support for non-English queries

### **Technical Improvements**
- **Streaming Responses**: Real-time response generation
- **Advanced ML**: Custom relevance scoring models
- **Database Scaling**: PostgreSQL for larger datasets
- **Microservices**: Split into smaller, focused services

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

---

**Built with ❤️ using FastAPI, LangGraph, SQLite FTS5, and Google Gemini**
