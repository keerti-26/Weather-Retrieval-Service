import os
import base64
import time
from urllib.parse import urlparse
from typing import Dict, Any, List

from flask import Flask, request, jsonify, render_template
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from databricks.sdk import WorkspaceClient

# Initialize Flask app with explicit template folder
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)
print(f"📁 Template directory: {template_dir}")

# Module-level model loading (happens once at startup)
print("="*60)
print("🚀 Weather Retrieval Service Starting...")
print("="*60)
print("📦 Loading embedding model (may take 30-60 seconds on first run)...")
os.environ["HF_HOME"] = "/tmp/.cache/huggingface"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/.cache/huggingface"
os.environ["HF_HUB_CACHE"] = "/tmp/.cache/huggingface"

start_time = time.time()
EMBEDDING_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
load_time = time.time() - start_time
print(f"✅ Embedding model loaded in {load_time:.1f}s")
print("🎉 Service ready!")
print("="*60)

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


@app.route('/', methods=['GET'])
def home():
    """Root endpoint - landing page."""
    try:
        return render_template('index.html')
    except Exception as e:
        # If template fails, return error info
        return jsonify({
            "error": "Template rendering failed",
            "details": str(e),
            "template_folder": app.template_folder,
            "available_templates": os.listdir(app.template_folder) if os.path.exists(app.template_folder) else "Template folder not found"
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "model": "all-MiniLM-L6-v2"}), 200


@app.route('/weather/search', methods=['POST'])
def search_weather():
    """
    Search weather alerts using semantic similarity.
    
    Body:
        query (str): Search query text
        top_k (int, optional): Number of results to return (default: 5, range: 1-20)
    
    Returns:
        JSON with top matching weather alert chunks and similarity scores
    """
    try:
        # Parse and validate request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        # Validate query
        query = data.get('query', '').strip()
        if not query:
            return jsonify({"error": "'query' field is required and cannot be empty"}), 400
        
        # Validate and clamp top_k
        top_k = data.get('top_k', 5)
        try:
            top_k = int(top_k)
            if top_k < 1:
                top_k = 1
            elif top_k > 20:
                top_k = 20
        except (ValueError, TypeError):
            return jsonify({"error": "'top_k' must be an integer between 1 and 20"}), 400
        
        # Embed the query using pre-loaded model
        query_embedding = EMBEDDING_MODEL.encode(query)
        
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
                return jsonify({
                    "results": [],
                    "query": query,
                    "top_k": top_k,
                    "message": "No results found. The weather_embeddings table may be empty or no data has been synced yet."
                }), 200
            
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
            
            return jsonify({
                "results": results,
                "query": query,
                "top_k": top_k
            }), 200
            
        except psycopg2.Error as db_error:
            # Database-specific errors
            return jsonify({
                "error": "Database query failed",
                "details": str(db_error)
            }), 500
            
        finally:
            # Always close cursor and connection
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    except Exception as e:
        # Catch-all for unexpected errors
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


if __name__ == '__main__':
    # Use APP_PORT environment variable provided by Databricks Apps
    port = int(os.getenv('APP_PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
