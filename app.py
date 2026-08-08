import os
import base64
import time
import json
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

import streamlit as st
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from databricks.sdk import WorkspaceClient

# Set page config - must be first Streamlit command
st.set_page_config(
    page_title="Weather Retrieval Service",
    page_icon="🌦️",
    layout="wide"
)

# Cache the embedding model to load only once
@st.cache_resource
def load_embedding_model():
    """Load embedding model once and cache it."""
    print("="*60)
    print("🚀 Weather Retrieval Service Starting...")
    print("="*60)
    print("📦 Loading embedding model (may take 30-60 seconds on first run)...")
    os.environ["HF_HOME"] = "/tmp/.cache/huggingface"
    os.environ["TRANSFORMERS_CACHE"] = "/tmp/.cache/huggingface"
    os.environ["HF_HUB_CACHE"] = "/tmp/.cache/huggingface"
    
    start_time = time.time()
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    load_time = time.time() - start_time
    print(f"✅ Embedding model loaded in {load_time:.1f}s")
    print("🎉 Service ready!")
    print("="*60)
    return model

# Database configuration
w = WorkspaceClient()


def get_lakebase_connection():
    """Get Lakebase PostgreSQL connection using Databricks secret."""
    try:
        # Get secret scope and key from environment variables
        secret_scope = os.getenv('LAKEBASE_SECRET_SCOPE', 'database')
        secret_key = os.getenv('LAKEBASE_SECRET_KEY', 'lakebase-url')
        secret = w.secrets.get_secret(scope=secret_scope, key=secret_key)
        lakebase_url = base64.b64decode(secret.value).decode("utf-8")
        parsed = urlparse(lakebase_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )
        return conn
    except Exception as e:
        raise Exception(f"Failed to connect to Lakebase: {str(e)}")


def perform_search(query: str, top_k: int, embedding_model) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Search weather alerts using semantic similarity.
    
    Args:
        query: Search query text
        top_k: Number of results to return (1-20)
        embedding_model: Pre-loaded SentenceTransformer model
    
    Returns:
        Tuple of (results_list, error_message)
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            return None, "Query cannot be empty"
        
        # Clamp top_k
        top_k = max(1, min(20, int(top_k)))
        
        # Embed the query
        query_embedding = embedding_model.encode(query)
        
        # Convert numpy array to list for PostgreSQL
        embedding_list = query_embedding.tolist()
        
        # Format embedding as PostgreSQL array string
        embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
        
        # Connect to database and execute search
        conn = None
        cursor = None
        
        try:
            conn = get_lakebase_connection()
            cursor = conn.cursor()
            
            # Cosine similarity search using pgvector <=> operator
            search_query = """
                SELECT 
                    d.id, 
                    d.location, 
                    d.headline, 
                    d.narrative_text, 
                    e.chunk_text,
                    1 - (e.embedding <=> %s::vector) AS similarity
                FROM weather_alert_embeddings e
                JOIN weather_alert_documents d ON d.id = e.document_id
                ORDER BY e.embedding <=> %s::vector
                LIMIT %s;
            """
            
            cursor.execute(search_query, (embedding_str, embedding_str, top_k))
            rows = cursor.fetchall()
            
            # Handle empty results
            if not rows:
                return [], "No results found. The weather_embeddings table may be empty or no data has been synced yet."
            
            # Format results
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "location": row[1],
                    "headline": row[2],
                    "narrative_text": row[3],
                    "chunk_text": row[4],
                    "similarity": float(row[5])  # Convert to Python float
                })
            
            return results, None
            
        except psycopg2.Error as db_error:
            return None, f"Database query failed: {str(db_error)}"
            
        finally:
            # Always close cursor and connection
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    except Exception as e:
        return None, f"Internal server error: {str(e)}"


# Main Streamlit UI
def main():
    # Load model (cached)
    embedding_model = load_embedding_model()
    
    # Header
    st.title("🌦️ Weather Retrieval Service")
    st.markdown("Semantic search over weather alerts using vector embeddings.")
    
    # Sidebar for health info
    with st.sidebar:
        st.header("ℹ️ Service Info")
        st.success("✅ Service Healthy")
        st.info("Model: all-MiniLM-L6-v2")
        st.markdown("---")
        st.markdown("""
        ### How it works
        1. Enter your search query
        2. Adjust the number of results
        3. Click Search
        4. View matching weather alerts
        """)
    
    # Main search interface
    st.header("🔍 Search Weather Alerts")
    
    # Input form
    with st.form("search_form"):
        query = st.text_input(
            "Query",
            placeholder="e.g., risk of flooding near rivers",
            value="risk of flooding near rivers"
        )
        
        top_k = st.slider(
            "Number of Results",
            min_value=1,
            max_value=20,
            value=5
        )
        
        submit_button = st.form_submit_button("Search 🔍")
    
    # Perform search when button is clicked
    if submit_button:
        if not query.strip():
            st.error("❌ Query cannot be empty")
        else:
            with st.spinner("🔍 Searching..."):
                results, error = perform_search(query, top_k, embedding_model)
                
                if error:
                    st.error(f"❌ {error}")
                elif not results:
                    st.warning("⚠️ No results found")
                else:
                    st.success(f"✅ Found {len(results)} result(s)")
                    
                    # Display results
                    for i, result in enumerate(results, 1):
                        with st.expander(f"Result {i}: {result['headline']} (Similarity: {result['similarity']:.3f})"):
                            col1, col2 = st.columns([1, 3])
                            
                            with col1:
                                st.metric("Similarity", f"{result['similarity']:.3f}")
                                st.caption(f"**ID:** {result['id']}")
                                st.caption(f"**Location:** {result['location']}")
                            
                            with col2:
                                st.markdown(f"**Headline:** {result['headline']}")
                                st.markdown(f"**Narrative:** {result['narrative_text']}")
                                with st.container():
                                    st.markdown("**Relevant Chunk:**")
                                    st.text_area(
                                        "Chunk",
                                        value=result['chunk_text'],
                                        height=100,
                                        label_visibility="collapsed",
                                        key=f"chunk_{i}"
                                    )


if __name__ == "__main__":
    main()
