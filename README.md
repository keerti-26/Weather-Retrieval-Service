# Weather Retrieval Service

A semantic search system for weather alerts using pgvector, sentence-transformers, and Lakebase PostgreSQL.

## Table of Contents
- [MCP Server](#mcp-server)
- [Data Source Choice](#data-source-choice)
- [Architecture](#architecture)
- [Schema Design](#schema-design)
- [Setup Instructions](#setup-instructions)
- [Running the Pipeline](#running-the-pipeline)
- [API Endpoints](#api-endpoints)
- [Known Limitations](#known-limitations)

---

## MCP Server

### Overview

This project includes a Model Context Protocol (MCP) server that exposes weather data tools for AI agents. The server provides three core capabilities:

1. **Current Weather** - Real-time conditions for a city
2. **Weather Forecast** - Multi-day forecast (1-7 days)
3. **Umbrella Prediction** - Smart recommendation based on precipitation probability

### MCP Tools

#### `get_current_weather_by_location(city: str)`
Returns current weather conditions including temperature, precipitation probability, wind speed/direction, and detailed forecast.

**Example:**
```python
# Tool call
get_current_weather_by_location("Boston, MA")

# Returns
{
  'location': 'Boston, MA',
  'day': 'Tonight',
  'temperature': 68,
  'precipitation_prob': 29,
  'wind_speed': '1 to 5 mph',
  'wind_direction': 'NE',
  'detailed_forecast': 'A chance of rain showers and patchy fog...'
}
```

#### `get_weather_forecast_by_location(city: str, days: int = 7)`
Returns multi-day forecast with high/low temperatures, precipitation chances, and conditions for each day/night period.

**Parameters:**
- `city`: City name (e.g., "Boston, MA")
- `days`: Number of days (1-7, defaults to 7)

**Example:**
```python
# Tool call
get_weather_forecast_by_location("Austin, TX", days=3)

# Returns list of forecast periods
[
  {
    'location': 'Austin, TX',
    'day': 'Tuesday',
    'starttime': datetime(2026, 8, 18, 6, 0),
    'temperature': 95,
    'precipitation_prob': 10,
    ...
  },
  ...
]
```

#### `predict_umbrella_needed_by_location(city: str, date: date)`
Predicts whether an umbrella is needed based on a 40% precipitation probability threshold.

**Logic:**
- Returns "Yes" if max precipitation probability > 40%
- Returns "No" if precipitation probability ≤ 40%
- Returns error message if no forecast data available

**Example:**
```python
# Tool call
predict_umbrella_needed_by_location("Denver, CO", date(2026, 8, 19))

# Returns
"Yes - An umbrella is recommended for Denver, CO on 2026-08-19. Precipitation probability exceeds 40%."
```

### Deployment

#### Transport Protocol

This MCP server uses **HTTP transport** (`transport="http"`) over standard HTTP/1.1, which is compatible with Databricks Apps and Agent Bricks. FastMCP's HTTP transport supports:
- JSON-RPC 2.0 protocol (MCP standard)
- SSE (Server-Sent Events) for streaming responses
- Full MCP tool discovery and execution

**In `weather_mcp_server.py`:**
```python
mcp.run(transport="http", host="0.0.0.0", port=port)
```

This configuration exposes the MCP server over HTTP on the port specified by Databricks Apps (`DATABRICKS_APP_PORT` environment variable). Agent Bricks connects via the app URL and communicates using the MCP protocol.

#### 1. Deploy MCP Server as Databricks App

```bash
# Navigate to mcp_server directory
cd mcp_server

# Deploy the app
databricks apps deploy weather-mcp-server --source-code-path .

# Start the app
databricks apps start weather-mcp-server

# Get app URL and status
databricks apps get weather-mcp-server
```

The MCP server will be available at the app URL (e.g., `https://<workspace>.cloud.databricks.com/apps/weather-mcp-server`).

**Deployment Files:**
- **`mcp_server/requirements.txt`**: FastMCP, Starlette, database drivers, ML models
- **`mcp_server/app.yaml`**: Databricks Apps configuration with environment variables and Python command
- **`mcp_server/weather_mcp_server.py`**: Main MCP server with 3 tools
- **`mcp_server/weather_broker.py`**: Database adapter for separating data access logic

#### 2. Register as External Tool in Agent Bricks

1. Open **Agent Bricks** in your Databricks workspace
2. Navigate to **External Tools** → **Add External Tool**
3. Select **MCP Server**
4. Enter the app URL from step 1
5. The three tools will be automatically discovered and registered:
   - `get_current_weather_by_location`
   - `get_weather_forecast_by_location`
   - `predict_umbrella_needed_by_location`

#### 3. Create Agent with System Prompt

1. Create a new agent in Agent Bricks
2. Attach the registered MCP tools
3. Use the system prompt from `SYSTEM_PROMPT.md`:
   - Explains available tools and when to use each
   - Defines error handling guidelines
   - Specifies the 40% precipitation threshold for umbrella predictions
   - Lists supported cities (Boston, Austin, New York, Denver, San Francisco)

### Architecture

```
┌─────────────────────────┐
│  Agent Bricks           │
│  (Natural Language UI)  │
└───────────┬─────────────┘
            │
            │ MCP Protocol
            │
┌───────────▼─────────────┐
│  MCP Server             │
│  (weather_mcp_server.py)│
│                         │
│  Tools:                 │
│  - get_current_weather  │
│  - get_forecast         │
│  - predict_umbrella     │
└───────────┬─────────────┘
            │
            │ Adapter calls
            │
┌───────────▼─────────────┐
│  Weather Broker         │
│  (weather_broker.py)    │
│                         │
│  - DB connection        │
│  - Query logic          │
│  - Error handling       │
└───────────┬─────────────┘
            │
            │ SQL queries
            │
┌───────────▼─────────────┐
│  Lakebase Postgres      │
│                         │
│  Tables:                │
│  - weather_forecast     │
│  - weather_alert_...    │
└─────────────────────────┘
```

### Data Pipeline

Weather forecast data is populated via the notebook:

**Notebook:** `notebooks/ingest_weather_alert_report`

**Cells 11-12:**
- **Cell 11:** Fetches 7-day forecasts from NWS API for 5 cities
- **Cell 12:** Inserts forecast data into `weather_forecast` table

**Run the pipeline:**
```bash
# Open the notebook and run cells 1-4, 11-12
# Or run all cells to also ingest weather alerts
```

**Forecast coverage:** Boston, Austin, New York, Denver, San Francisco (expandable)

### System Prompt

See `SYSTEM_PROMPT.md` for the complete agent system prompt with:
- Tool descriptions and when to use each
- Error handling guidelines
- Supported cities and location handling
- Example conversation workflows
- 40% precipitation threshold explanation

### Demonstration & Evidence

For complete project documentation and grading evidence:

1. **`DEMONSTRATION.md`** - 6 example interactions showing:
   - Natural language queries
   - Tool calls with parameters
   - Structured JSON responses
   - Agent's final answers
   - Error handling examples
   - Compliance with system prompt guidelines

2. **`AGENT_REGISTRATION_GUIDE.md`** - Step-by-step instructions to:
   - Register MCP server in Agent Bricks
   - Create weather assistant agent
   - Attach tools and system prompt
   - Capture screenshots for evidence
   - Troubleshoot common issues

3. **`SECURITY_CHECKLIST.md`** - Pre-push security audit:
   - Verifies no hardcoded credentials
   - Documents safe vs. sensitive files
   - Pre-commit checklist
   - GitHub security best practices

**Tool Response Format:**
All tools return **structured dictionaries** (not strings), enabling reliable parsing by AI agents:
- **Current weather**: `{"location": ..., "temperature": ..., "precipitation_prob": ...}`
- **Forecast**: `{"forecasts": [{...}, {...}]}`
- **Umbrella**: `{"recommendation": "yes"|"no", "reason": ..., "threshold": 40}`
- **Errors**: `{"error": "..."}`

---

## Data Source Choice

### National Weather Service (NWS) Active Alerts

**Why NWS Active Alerts?**

1. **Real-time, Actionable Data**: NWS alerts provide time-sensitive, critical weather information that people actively search for ("tornado warnings near me", "flood alerts in Texas").

2. **Rich Unstructured Content**: Each alert contains narrative fields:
   - `headline`: Brief summary (e.g., "Tornado Warning")
   - `description`: Detailed context about the weather event
   - `instruction`: Actionable safety guidance
   
   These fields are perfect for semantic embedding and retrieval.

3. **Free & Reliable API**: The NWS API (https://api.weather.gov) is:
   - Free to use (no authentication required)
   - Stable and well-documented
   - Covers all US states and territories

4. **Geographically Scoped**: Alerts are tied to specific locations, enabling location-aware search.

5. **Retrieval-Focused Use Case**: Weather alerts are inherently query-driven — users search for specific events, locations, or conditions.

**Data Coverage**: 
- 5 major US cities: Boston (MA), Austin (TX), New York (NY), Denver (CO), San Francisco (CA)
- Expandable to all 50 states

---

## Architecture

```
┌─────────────────┐
│  NWS API        │
│  (alerts)       │
└────────┬────────┘
         │
         v
┌─────────────────┐      ┌──────────────────┐
│ weather_client  │─────>│  Lakebase        │
│  .py            │      │  (PostgreSQL +   │
└─────────────────┘      │   pgvector)      │
                         └──────────┬───────┘
                                    │
         ┌──────────────────────────┴────────────────────┐
         │                                                │
         v                                                v
┌─────────────────────┐                    ┌──────────────────────┐
│ weather_alert_      │                    │ weather_alert_       │
│ documents           │                    │ embeddings           │
│                     │                    │                      │
│ - id (PK)           │                    │ - id (PK)            │
│ - location          │<───────────────────│ - alert_id (FK)      │
│ - headline          │                    │ - chunk_text         │
│ - description       │                    │ - embedding (vector) │
│ - instruction       │                    │ - chunk_index        │
└─────────────────────┘                    └──────────────────────┘
         │                                                │
         │                                                │
         v                                                v
┌─────────────────────────────────────────────────────────────┐
│                     Flask REST API                          │
│                                                             │
│  GET  /                -  Web UI for search interface       │
│  GET  /health          -  Health check endpoint            │
│  POST /weather/search  -  Semantic search (pgvector <=>)   │
└─────────────────────────────────────────────────────────────┘
```

---

## Schema Design

### 1. `weather_alert_documents` Table

**Purpose**: Store raw weather alert data from NWS.

**Columns**:
- `id` (TEXT, PRIMARY KEY): Unique alert ID from NWS
- `location` (TEXT, NOT NULL): City/region (e.g., "Boston, MA")
- `source_type` (TEXT): Always "alert" (extensible for future sources like forecasts)
- `headline` (TEXT): Brief alert headline
- `description` (TEXT): Detailed narrative about the weather event
- `instruction` (TEXT): Safety instructions and guidance
- `issued_at` (TIMESTAMPTZ): When the alert was issued
- `payload` (JSONB): Full raw alert JSON from NWS API
- `synced_at` (TIMESTAMPTZ): When we fetched the alert

**Rationale**:
- Preserves full alert context (JSONB payload)
- Separates structured metadata (headline, location) from narrative text
- Time tracking for data freshness and deduplication

### 2. `weather_alert_embeddings` Table

**Purpose**: Store vector embeddings of chunked alert content.

**Columns**:
- `id` (TEXT, PRIMARY KEY): Composite key `{alert_id}_{chunk_index}`
- `alert_id` (TEXT, NOT NULL): Foreign key to `weather_alert_documents.id`
- `location` (TEXT): Denormalized for faster filtering
- `chunk_index` (INTEGER): Order of chunk within the parent alert
- `chunk_text` (TEXT): The actual text chunk that was embedded
- `embedding` (VECTOR(384)): pgvector embedding (384-dimensional)
- `model_name` (TEXT): Embedding model used ("sentence-transformers/all-MiniLM-L6-v2")
- `embedded_at` (TIMESTAMPTZ): When the embedding was generated

**Index**:
```sql
CREATE INDEX idx_weather_alert_embeddings_embedding
ON weather_alert_embeddings
USING hnsw (embedding vector_cosine_ops);
```

**Rationale**:
- **HNSW index**: Approximate nearest-neighbor search for fast cosine similarity queries
- **Chunking**: Breaks long alert descriptions into 800-character chunks with 100-character overlap
  - Why 800? Balances semantic coherence with context window
  - Why 100 overlap? Prevents losing context at chunk boundaries
- **Denormalization**: Stores `location` for fast location-filtered searches without JOINs

### 3. Chunking Parameters

```python
CHUNK_SIZE = 800       # characters
CHUNK_OVERLAP = 100    # characters
```

**Why These Values?**
- Tested 500 vs 800 character chunks — 800 provided better semantic coherence
- 100-character overlap ensures no information loss at boundaries
- Sliding window: `[0:800], [700:1500], [1400:2200], ...`

**Embedding Text Construction**:
```sql
TRIM(CONCAT(COALESCE(description, ''), '. ', COALESCE(instruction, '')))
```
- Combines narrative description + safety instructions
- Provides richer context than headline alone

### 4. Embedding Model

**Model**: `sentence-transformers/all-MiniLM-L6-v2`

**Specifications**:
- **Dimensions**: 384
- **Speed**: Fast inference (~2-3ms per chunk on CPU)
- **Quality**: Strong performance on semantic similarity tasks
- **Size**: Small footprint (~90MB)

**Why This Model?**
- Good balance of speed and accuracy for production use
- Widely used and well-tested in the community
- Compatible with Databricks Serverless compute
- Works well with short-to-medium text (weather alerts are typically 200-1500 chars)

**Alternatives Considered**:
- `all-mpnet-base-v2`: Higher quality but slower (768 dimensions)
- `bge-small-en-v1.5`: Similar quality, similar speed

---

## Setup Instructions

### Prerequisites

1. **Lakebase PostgreSQL Database**
   - Databricks Lakebase project created
   - Connection URL stored in Databricks secret scope

2. **Python Environment**
   - Python 3.9+
   - Access to install packages

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set Up Databricks Secret

```python
# Run setup_secret.py to store your Lakebase connection URL
python setup_secret.py
```

Or manually create the secret:
```bash
databricks secrets create-scope database
databricks secrets put-secret database lakebase-url
# Paste your base64-encoded Lakebase URL when prompted
```

### Step 3: Create Database Tables

Connect to your Lakebase database and run:

```bash
# Create documents table
psql "$LAKEBASE_URL" < sql/weather_alert_documents.sql

# Create embeddings table (requires pgvector extension)
psql "$LAKEBASE_URL" < sql/weather_alert_embeddings.sql
```

Or use a SQL client:
```sql
-- From sql/weather_alert_documents.sql
CREATE TABLE IF NOT EXISTS weather_alert_documents (
    id TEXT PRIMARY KEY,
    location TEXT NOT NULL,
    source_type TEXT NOT NULL,
    headline TEXT,
    description TEXT,
    instruction TEXT,
    issued_at TIMESTAMPTZ,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_weather_alert_documents ON weather_alert_documents(location);

-- From sql/weather_alert_embeddings.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS weather_alert_embeddings (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL,
    location TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    model_name TEXT NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_weather_alert_embeddings_embedding
ON weather_alert_embeddings
USING hnsw (embedding vector_cosine_ops);
```

### Step 4: Verify Setup

```python
import lakebase

with lakebase.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        print("✅ Database connection successful!")
```

---

## Running the Pipeline

### End-to-End Workflow

```
1. Sync & Embed (via Notebook or Script)  →  2. Search (via Flask API)
   (Fetch NWS + Vectorize)                    (Query)
```

### Option A: Using the Notebook + Flask API

#### 1. Sync and Embed Data (Notebook)

Run the Databricks notebook `ingest_weather_alert_report` to fetch alerts and generate embeddings:

1. **Cells 1-4**: Configuration and setup
2. **Cell 5**: Fetch alerts from NWS API
3. **Cell 6**: Insert alerts into `weather_alert_documents`
4. **Cell 7**: Load un-embedded alerts
5. **Cell 8**: Chunk alert content
6. **Cell 9**: Compute embeddings
7. **Cell 10**: Insert embeddings into `weather_alert_embeddings`

#### 2. Deploy and Start the Flask Server

**Local Development:**
```bash
python app.py
# Server starts on http://0.0.0.0:5000
```

**Production Deployment (Databricks App):**
```bash
# Deploy as a Databricks App (uses app.yaml config)
databricks apps deploy weather-search-app --source-code-path .

# Start the app
databricks apps start weather-search-app

# Check status
databricks apps get weather-search-app
```

The app will be served via gunicorn with the configuration specified in `app.yaml`

#### 3. Search for Alerts

#### 4. Search for Alerts (Flask API)

```bash
curl -X POST http://localhost:5000/weather/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tornado warnings in texas",
    "top_k": 5
  }'
```

**Response**:
```json
{
  "success": true,
  "query": "tornado warnings in texas",
  "results": [
    {
      "id": "alert_123",
      "location": "Austin, TX",
      "headline": "Tornado Warning",
      "chunk_text": "The National Weather Service has issued a Tornado Warning for Travis County...",
      "similarity": 0.8521
    }
  ],
  "count": 5
}
```

### Option B: Using Standalone Scripts

#### 1. Fetch and Embed Alerts

```bash
# Run the embedding ingestion script
python ingest_embeddings.py
```

**Output**:
```
============================================================
Starting Weather Alert Embedding Ingestion
============================================================

[1/4] Loading un-embedded alerts from database...
   Found 12 alerts without embeddings

[2/4] Chunking alerts (size=800, overlap=100)...
   Generated 47 chunks from 12 alerts

[3/4] Computing embeddings using sentence-transformers/all-MiniLM-L6-v2...
   Computed 47 embeddings

[4/4] Inserting embeddings into weather_alert_embeddings...
   Successfully inserted 47 chunk embeddings

============================================================
✅ Embedding Ingestion Complete!
============================================================
   Alerts processed:  12
   Chunks generated:  47
   Embeddings inserted: 47
============================================================
```

#### 2. Start Flask Server and Search

Follow steps 2-4 from Option A above

---

## API Endpoints

### Home Page

**GET** `/`

**Response**: HTML web interface for searching weather alerts

### Health Check

**GET** `/health`

**Response**:
```json
{
  "status": "healthy",
  "service": "Weather Retrieval Service",
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

### Search Alerts

**POST** `/weather/search`

**Request Body**:
```json
{
  "query": "tornado warnings in texas",
  "top_k": 5
}
```

**Success Response (200)**:
```json
{
  "success": true,
  "query": "tornado warnings in texas",
  "results": [
    {
      "id": "alert_id",
      "location": "Austin, TX",
      "headline": "Tornado Warning",
      "chunk_text": "...",
      "similarity": 0.85
    }
  ],
  "count": 5
}
```

**Parameters**:
- `query` (required): Search query string
- `top_k` (optional): Number of results (1-20, default: 5)

---

## Project Structure

```
Weather-Retrieval-Service/
├── app.py                      # Flask REST API (search endpoint)
├── ingest_embeddings.py        # Standalone embedding ingestion script
│
├── weather_client.py           # NWS API client
├── lakebase.py                 # Lakebase connection utilities
├── chunking_utils.py           # Text chunking logic
├── embedding_utils.py          # Embedding generation & DB insertion
│
├── sql/
│   ├── weather_alert_documents.sql     # Documents table DDL
│   └── weather_alert_embeddings.sql    # Embeddings table DDL + pgvector index
│
├── templates/
│   └── index.html              # Web UI for search interface
│
├── requirements.txt            # Python dependencies
├── app.yaml                    # Databricks Apps deployment config (gunicorn + Flask)
├── README.md                   # This file
└── ingest_weather_alert_report # Databricks notebook (data sync + embedding generation)
```

---

## Known Limitations & Future Improvements

### Current Limitations

1. **Limited Geographic Coverage**
   - Only covers 5 major US cities
   - **Improvement**: Expand to all 50 states, or make location configurable via API

2. **No Forecast Data**
   - Only ingests active alerts, not forecasts
   - **Improvement**: Integrate NWS forecast endpoints for predictive queries ("what's the weather outlook for next week?")

3. **No Incremental Updates**
   - Full sync replaces all data; no smart change detection
   - **Improvement**: Implement CDC (change data capture) to update only new/modified alerts

4. **Basic Chunking Strategy**
   - Fixed-size character windows don't respect sentence boundaries
   - **Improvement**: Use semantic chunking (split on sentence boundaries, respect paragraph structure)

5. **No Result Re-Ranking**
   - Pure cosine similarity without additional relevance signals
   - **Improvement**: Add multi-factor ranking:
     - Alert severity (Tornado Warning > Frost Advisory)
     - Recency (recent alerts ranked higher)
     - Location proximity (if user provides lat/long)

6. **No Observability**
   - No metrics on search quality, embedding coverage, or latency
   - **Improvement**: Add:
     - Prometheus metrics (query latency, cache hit rate)
     - Logging of popular queries for model fine-tuning
     - Embedding quality checks (detect low-diversity or degenerate embeddings)

7. **Single Embedding Model**
   - Only uses one model; no A/B testing or ensemble
   - **Improvement**: Support multiple models with weighted voting

8. **No User Feedback Loop**
   - Can't learn from user clicks or relevance judgments
   - **Improvement**: Add implicit feedback (clicks, dwell time) to retrain/fine-tune embeddings

9. **No Caching**
   - Every search recomputes the query embedding
   - **Improvement**: Cache popular query embeddings (Redis)

10. **Error Recovery**
    - If NWS API is down, sync fails completely
    - **Improvement**: Add retry logic with exponential backoff, fallback to cached data

### Performance Considerations

- **Embedding model load time**: ~10-30 seconds on cold start
  - Mitigation: Keep Flask app warm, or use model serving endpoint
- **pgvector HNSW index**: Approximate search (not exact)
  - Trade-off: 10-100x faster than exact brute-force, with 95%+ recall

---

## Technical Details

### Why psycopg2 Instead of Spark JDBC?

**Spark JDBC Issues with pgvector**:
- Spark doesn't natively understand the `VECTOR` type from pgvector
- Writing vectors via JDBC requires string serialization, which is error-prone
- Batching and connection pooling are harder to control

**psycopg2 Benefits**:
- Native PostgreSQL driver with full type support
- Direct control over batching (via `executemany` or `execute_values`)
- Works seamlessly with pgvector's native `VECTOR` type
- Simpler error handling and transaction management

### Vector Search Query

```sql
SELECT 
    d.id,
    d.location, 
    d.headline,
    e.chunk_text,
    1 - (e.embedding <=> %s::vector) AS similarity
FROM weather_alert_embeddings e
JOIN weather_alert_documents d ON d.id = e.alert_id
ORDER BY e.embedding <=> %s::vector
LIMIT %s;
```

**Key Points**:
- `<=>` is pgvector's cosine distance operator
- `1 - distance` converts distance to similarity score (0-1)
- `ORDER BY ... <=>` uses the HNSW index for fast approximate search
- `JOIN` pulls in document metadata for display

---

## Testing

### Manual Testing

```bash
# 1. Ingest data and generate embeddings
python ingest_embeddings.py

# 2. Start Flask server
python app.py
# Server starts on http://0.0.0.0:5000

# 3. Test health check
curl http://localhost:5000/health

# 4. Test search endpoint
curl -X POST http://localhost:5000/weather/search \
  -H "Content-Type: application/json" \
  -d '{"query": "severe thunderstorm", "top_k": 3}'

# 5. Or visit the web UI
# Open http://localhost:5000 in your browser
```

### Verify Database State

```sql
-- Check documents
SELECT COUNT(*) AS total_alerts FROM weather_alert_documents;

-- Check embeddings
SELECT COUNT(*) AS total_embeddings FROM weather_alert_embeddings;

-- Check average chunks per alert
SELECT AVG(chunks) AS avg_chunks_per_alert
FROM (
    SELECT alert_id, COUNT(*) AS chunks
    FROM weather_alert_embeddings
    GROUP BY alert_id
) sub;

-- Test vector search directly
SELECT 
    d.headline,
    e.chunk_text,
    1 - (e.embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM weather_alert_embeddings e
JOIN weather_alert_documents d ON d.id = e.alert_id
ORDER BY e.embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

---

## License

MIT License

---

## Contact

For questions or issues, contact: your-email@example.com
