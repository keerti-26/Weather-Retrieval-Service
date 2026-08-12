"""Flask REST API for Weather Retrieval Service."""
import os
import logging
from typing import Dict, Any, List, Tuple

from flask import Flask, request, jsonify, render_template
import numpy as np
from sentence_transformers import SentenceTransformer

import lakebase
from weather_client import NWSClient
from embedding_utils import batch_insert_alerts_to_lakebase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize NWS client
nws_client = NWSClient()

# Load embedding model once at startup
os.environ["HF_HOME"] = "/tmp/.cache/huggingface"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/.cache/huggingface"
os.environ["HF_HUB_CACHE"] = "/tmp/.cache/huggingface"

logger.info("Loading embedding model...")
embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2",
    cache_folder="/tmp/.cache/huggingface"
)
logger.info("Embedding model loaded successfully")

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Weather Retrieval Service",
        "model": "sentence-transformers/all-MiniLM-L6-v2"
    }), 200

@app.route('/weather/sync', methods=['POST'])
def sync_weather_alerts():
    """
    Sync weather alerts from NWS API into Lakebase.
    
    Request body:
    {
        "cities": ["Boston, MA", "Austin, TX", "New York, NY"],
        "state_codes": ["MA", "TX"]  # optional, alternative to cities
    }
    
    Returns:
    {
        "success": true,
        "alerts_fetched": 15,
        "alerts_inserted": 12,
        "message": "Successfully synced weather alerts"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return({
                "success": False,
                "error": "Request body is empty"
            }), 400
        cities = data.get("cities", [])
        state_codes = data.get("state_codes", [])
        if not cities and not state:
            return jsonify({
                "success": False,
                "error": "Must provide either cities or state_code"
            }), 400
        all_alerts = []
        if cities:
            logger.info(f"Fetching  alerts for {len(cities)} cities")
            all_alerts.extend(nws_client.fetch_alert_for_cities(cities))
        if state_codes:
            logger.info(f"fetching alerts for{len(state_codes)} states codes")
            all_alerts.extend(nws_client.fetch_alerts_for_cities(state_codes))
        if not all_alerts:
            return jsonify(
                {
                    "success": True,
                    "alerts_fetched": 0,
                    "alerts_inserted": 0,
                    "message": "No alerts found for specified location"
                }), 200

        with lakebase.get_connection() as conn:
            inserted_count = batch_insert_alerts_to_lakebase(
                alerts = all_alerts,
                conn = conn,
                alert_table = "weather_alerts_documents"
            )
        logger.info(f"Synced to Lakebase{len(all_alerts)}, Inserted count {inserted_count}")
        return jsonify({
            "success": True,
            "alerts_fetched": len(all_alerts),
            "alerts_inserted": inserted_count,
            "message": "Successfully synced weather alerts"
        }), 200
    except Exception as e:
        logger.error(f"Error syncing weather alerts:{e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })
               

@app.route('/weather/search', methods=['POST'])
def search_weather_alerts():
    """
    Search weather alerts using semantic similarity.
    
    Request body:
    {
        "query": "tornado warnings in texas",
        "top_k": 5
    }
    
    Returns:
    {
        "success": true,
        "query": "tornado warnings in texas",
        "results": [
            {
                "id": "alert_123",
                "location": "Austin, TX",
                "headline": "Tornado Warning",
                "chunk_text": "...",
                "similarity": 0.85
            }
        ],
        "count": 5
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must be JSON"
            }), 400
        
        query = data.get("query")
        top_k = data.get("top_k")
        if not query:
            return jsonify({
                "success": False,
                "error": "Query cant be empty"
            }), 400
         
        # Clamp top_k
        top_k = max(1, min(20, int(top_k)))
        # Embed the query
        query_embeddings = embedding_model.encode(query)
        embedding_list = query_embeddings.tolist()
        embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'

        #Search lakebase
        with lakebase.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    search_query = """
                    Select d.id,
                        d.location,
                        d.headline,
                        e.chunk_text,
                        1- (e.embedding <=> %s::vector) as similarity
                    from weather_alert_embeddings as e
                    join weather_alert_documents as d
                    on e.alert_id = d.id
                    order by e.embedding <=> %s::vector
                    limit %s
                    """
                    cur.execute(search_query, (embedding_str, embedding_str, top_k))
                    rows = cur.fetchall()
                except Exception as db_error:
                    logger.error(f"Database query error: {db_error}")
                    raise
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "location": row["location"],
                "headline": row["headline"],
                "chunk_text": row["chunk_text"],
                "similarity": float(row["similarity"])

            })
        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }),200
    except Exception as e:
        logger.error(f"Error in the endpoint:{e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
            



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
