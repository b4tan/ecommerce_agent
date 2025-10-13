# Project structure
```
ecommerce_agent/
├── backend/
│   ├── agent/
│   │   ├── graph.py           # LangGraph agent definition
│   │   ├── tools.py           # Product search tool
│   │   ├── schema.py          # Agent data models (Pydantic models)
│   │   └── system_prompt.txt  # AI instructions
│   └── gateway/
│       ├── app.py             # FastAPI application
│       ├── chat.py            # Chat endpoint
│       ├── upload.py          # Image upload endpoint
│       ├── schema.py          # API schemas (Pydantic models)
│       └── rate_limiter.py    # Rate limiting logic
├── services/
│   ├── hybrid_search.py       # FAISS + lexical search
│   ├── catalog_search.py      # Search API gateway
│   ├── query_filter.py        # SQL filter compiler
│   └── schema.py              # Product data models (Pydantic models)
├── client/
│   ├── index.html             # Frontend UI
│   └── app.js                 # Frontend logic
├── scripts/
│   ├── build_db.py            # Database builder (Original database was in csv form (csv -> sqlite))
│   └── build_faiss_gemini.py  # FAISS index builder (Creates indexes for fast searches)
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

### Search Flow
1. **User Query** → Frontend sends text/image to backend
2. **Rate Check** → Verify user hasn't exceeded limits
3. **AI Analysis** → Agent analyzes query and decides to search or respond
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

# Design & Architecture

## The Search Problem

When I first built this project, I thought of creating an agent where that had tools to search over a database. I took the straightforward approach, created a mock relational db in  and then searching with SQL queries with `LIKE` and `WHERE` clauses. This worked for exact matches but failed quickly in real-world scenarios. A user searching for "running shoes" wouldn't find products labeled "athletic sneakers." A typo like "runing shoes" returned nothing. Searches for "laptop" missed "notebook computer" entirely. The fundamental issue was that SQL operates on exact text matching, while humans think in concepts and meanings.

I upgraded to SQLite's FTS5 (Full-Text Search), which added indexed search and basic relevance ranking using BM25 scoring. This was significantly better for keyword matching and handled multiple words more intelligently. However, FTS5 still struggled with semantic understanding—it couldn't bridge the gap between synonyms like "laptop" and "notebook," and typos still broke searches unless I manually configured fuzzy search parameters, which becomes unmaintainable at scale.

I considered industry-standard solutions like Elasticsearch or OpenSearch, which excel at text search with built-in synonym handling, typo tolerance, and sophisticated ranking algorithms. However, both require dedicated server infrastructure, adding $50-200 in monthly hosting costs, plus operational complexity around cluster management, backup strategies, and version upgrades. For a small product catalog, this felt quite overbearing.

That's when I moved to a hybrid search architecture combining FAISS for semantic vector search with SQLite for structured filtering and lightweight keyword matching. FAISS (Facebook AI Similarity Search) handles the "meaning" part by converting text into high-dimensional vectors, where semantically similar concepts cluster together in vector space. SQLite handles the "rules" part—price ranges, rating thresholds, exact brand matches—which are naturally expressed as database constraints. Together, they deliver search quality comparable to Elasticsearch at a fraction of the cost and complexity.

## Core Design Principles

The architecture prioritizes four key objectives. First, search relevance must handle natural language variations. When someone searches for "red running shoes under $50," the system needs to understand that "crimson running sneakers" is semantically similar while also respecting the explicit price constraint. This requires blending semantic understanding (FAISS embeddings) with business logic (SQL filters) and keyword signals (lexical matching).

Next to that, performance matters and FAISS runs entirely in-process with vector similarity lookups that are pretty fast, while SQLite B-tree indexes make filtered queries blazingly fast. The entire search stack lives in the application process—no network hops, no external dependencies.

Aside from that, I also created a fallback handle. If FAISS initialization fails, the system falls back to SQL LIKE pattern matching. If embeddings are unavailable, keyword search takes over. If both fail, the system can still browse products using filters and sorting. Every failure mode has a fallback, logged with debug information so operators understand what degraded.

## Hybrid Search Implementation

The search pipeline executes in six stages, designed to balance recall (finding all relevant products) with precision (ranking the best ones first). The implementation lives primarily in `services/hybrid_search.py` and `services/catalog_search.py`.

**Stage 1: Semantic Recall (FAISS ANN).** 

**Stage 2: Lexical Recall (Keyword Matching).** 

**Stage 3: Candidate Union.** 

**Stage 4: SQL Filtering.**

**Stage 5: Normalized Reranking.** 

**Stage 6: Pagination and Response.** 

## Containerization & Deployment Architecture

Used docker to containerize backend and frontend for hosting

## API Design for Scale

The architecture enables horizontal scaling through stateless design and artifact locality. Gateway instances hold no session state—every request carries its own context. Services are pure functions that read from shared artifacts (SQLite, FAISS) without mutating them. 


## Error Handling & Resilience

### Input Validation

* Endpoints validate with **Pydantic** models (types, required fields, ranges).
* Filter compilation safelists columns/ops; values are **parameter-bound** (no string concatenation).

### Rate Limiting

* Per-IP/user quotas in `rate_limiter.py`. On exceed:

  * **HTTP 429** with JSON error payload containing `retry_after` seconds.

### HTTP Status Codes

* **400** – invalid payload (schema/filters).
* **404** – resource not found (e.g., image handle).
* **429** – rate limit exceeded.
* **5xx** – unexpected server error (logged with correlation id).


## Security & Design Shortcuts

This project was built in approximately 16 hours as a functional prototype, and some corners were definitely cut in the name of speed. Here's what I'd fix before going to production with real users.

**No Authentication.** The biggest issue is that anyone can hit the API endpoints without any authentication. There's no login, no API keys, no JWT tokens—just open HTTP endpoints. The `/chat` and `/chat/upload` routes are completely public. This was fine for a demo where I wanted to minimize complexity, but in production, this means anyone who finds your URL can:
- Burn through your Gemini API quota (costing you money)
- Scrape your entire product catalog
- Many more..

**SQL Injection Still Possible (Theoretically).** While the code uses parameterized queries and Pydantic validation, the `query_filter.py` compiler dynamically builds SQL from user input. I trust my implementation, but I haven't had it security-audited. There might be edge cases where carefully crafted filter combinations could inject SQL fragments. The safeguards are there (column whitelisting, parameter binding, no string concatenation), but without formal verification or penetration testing, I can't guarantee it's bulletproof.

**CORS Wide Open.** The FastAPI app has `allow_origins=["*"]` in its CORS middleware, meaning any website can make requests to the API. This was intentional for easy frontend development (no CORS errors), but in production, this enables cross-site request forgery. A malicious website could embed JavaScript that calls your API on behalf of visitors, potentially burning through your API quota or scraping data.

**No Request Size Limits.** While image uploads have a 20MB cap, there's no global request body size limit. Someone could theoretically send a 1GB JSON payload to `/chat`, causing memory exhaustion. FastAPI has default limits (100MB), but these weren't explicitly configured or tested. Production systems would set aggressive limits (1MB for JSON, 10MB for uploads) and fail fast on oversized requests.

**No Monitoring or Alerting.** There's zero operational visibility beyond stdout logs. No metrics on request latency, error rates, API quota consumption, or rate limit hits. If something breaks in production, you'd only know when users complain. Production systems would integrate Prometheus metrics, health check endpoints with detailed status, and alerts for anomalies (spike in 500 errors, approaching API quota, memory leaks).


* Redis for **distributed** rate limiting and response caching (no API changes).
* Incremental FAISS updates via `IndexIDMap2` for near-zero-downtime refreshes.
* Replace linear rerank with **learn-to-rank** behind the same scoring interface.
* Expand filter schema with new facets by editing `query_filter.py` (no search code changes).
* Implement proper authentication (OAuth2 + JWT) before any public launch.
* Migrate secrets to Secret Manager and enable audit logging.
* Add comprehensive monitoring (Prometheus) and alerting (PagerDuty).
* Replicate SQLite to PostgreSQL for durability if catalog becomes dynamic.
