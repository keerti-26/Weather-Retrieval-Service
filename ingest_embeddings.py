#!/usr/bin/env python3
"""Embedding ingestion script for weather alerts.

This script:
1. Loads un-embedded alerts from weather_alert_documents
2. Chunks the alert content (description + instruction)
3. Generates embeddings using sentence-transformers/all-MiniLM-L6-v2
4. Batch inserts embeddings into weather_alert_embeddings via psycopg2

Usage:
    python ingest_embeddings.py
"""
import os
import logging
import sys

import lakebase
from chunking_utils import load_unemdedded_alerts_from_db, chunk_alerts_dataframe
from embedding_utils import EmbeddingGenerator, insert_embeddings_to_lakebase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
ALERT_TABLE = "weather_alert_documents"
EMBEDDINGS_TABLE = "weather_alert_embeddings"
BATCH_SIZE = 32


def main():
    """Main embedding ingestion pipeline."""
    logger.info("="*60)
    logger.info("Starting Weather Alert Embedding Ingestion")
    logger.info("="*60)
    
    try:
        # Step 1: Load un-embedded alerts
        logger.info("\n[1/4] Loading un-embedded alerts from database...")
        with lakebase.get_connection() as conn:
            alerts_df = load_unemdedded_alerts_from_db(
                conn=conn,
                alert_table=ALERT_TABLE,
                embeddings_table=EMBEDDINGS_TABLE
            )
        
        if len(alerts_df) == 0:
            logger.info("\n✅ No new alerts to embed. All alerts are already processed.")
            return 0
        
        logger.info(f"   Found {len(alerts_df)} alerts without embeddings")
        
        # Step 2: Chunk the alerts
        logger.info(f"\n[2/4] Chunking alerts (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
        chunks_df = chunk_alerts_dataframe(
            alerts_df=alerts_df,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            text_column="embedding_text"
        )
        logger.info(f"   Generated {len(chunks_df)} chunks from {len(alerts_df)} alerts")
        
        # Step 3: Generate embeddings
        logger.info(f"\n[3/4] Computing embeddings using {EMBEDDING_MODEL}...")
        embedding_gen = EmbeddingGenerator(model_name=EMBEDDING_MODEL)
        chunk_embeddings_df = embedding_gen.embed_chunks(
            chunks_df=chunks_df,
            batch_size=BATCH_SIZE
        )
        logger.info(f"   Computed {len(chunk_embeddings_df)} embeddings")
        
        # Step 4: Insert embeddings into database
        logger.info(f"\n[4/4] Inserting embeddings into {EMBEDDINGS_TABLE}...")
        with lakebase.get_connection() as conn:
            inserted_count = insert_embeddings_to_lakebase(
                embeddings_df=chunk_embeddings_df,
                conn=conn,
                embeddings_table=EMBEDDINGS_TABLE
            )
        
        logger.info("\n" + "="*60)
        logger.info("✅ Embedding Ingestion Complete!")
        logger.info("="*60)
        logger.info(f"   Alerts processed:  {len(alerts_df)}")
        logger.info(f"   Chunks generated:  {len(chunks_df)}")
        logger.info(f"   Embeddings inserted: {inserted_count}")
        logger.info("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Error during embedding ingestion: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
