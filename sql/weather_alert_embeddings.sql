CREATE EXTENSION IF NOT EXISTS vector;

-- Create the embeddings table
-- IMPORTANT: Replace {{EMBEDDING_DIM}} below with the correct dimension for your model:
--   - sentence-transformers/all-MiniLM-L6-v2: 384
--   - sentence-transformers/all-mpnet-base-v2: 768
--   - BAAI/bge-small-en-v1.5: 384
--   - BAAI/bge-base-en-v1.5: 768
--   - BAAI/bge-large-en-v1.5: 1024
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

-- Create HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_weather_alert_embeddings_embedding
ON weather_alert_embeddings
USING hnsw (embedding vector_cosine_ops);

-- Verify the table was created
SELECT 
    table_name,
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'weather_alert_embeddings'
ORDER BY ordinal_position;