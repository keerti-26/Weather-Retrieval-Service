"""Embedding generation utilities for weather alert chunks."""
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
import psycopg2
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Handles embedding generation for text chunks."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self.model = None
        
        # Set HuggingFace cache to /tmp for Databricks
        os.environ["HF_HOME"] = "/tmp/.cache/huggingface"
        os.environ["TRANSFORMERS_CACHE"] = "/tmp/.cache/huggingface"
        os.environ["HF_HUB_CACHE"] = "/tmp/.cache/huggingface"
    
    def load_model(self):
        """Load the embedding model."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder="/tmp/.cache/huggingface"
            )
            logger.info("Model loaded successfully")
    
    def embed_chunks(
        self,
        chunks_df: pd.DataFrame,
        batch_size: int = 32
    ) -> pd.DataFrame:
        """
        Generate embeddings for text chunks.
        
        Args:
            chunks_df: DataFrame with columns [alert_id, location, chunk_index, chunk_text]
            batch_size: Number of chunks to process in each batch
        
        Returns:
            DataFrame with added 'embedding' column
        """
        self.load_model()
        
        logger.info(f"Computing embeddings for {len(chunks_df)} chunks")
        
        all_embeddings = []
        
        for i in range(0, len(chunks_df), batch_size):
            batch = chunks_df.iloc[i:i+batch_size]
            
            # Generate embeddings for batch
            vectors = self.model.encode(
                batch["chunk_text"].tolist(),
                show_progress_bar=False
            )
            
            all_embeddings.extend(vectors.tolist())
            
            # Progress logging
            if (i + batch_size) % 128 == 0:
                logger.info(f"  Processed {min(i + batch_size, len(chunks_df))}/{len(chunks_df)} chunks")
        
        # Add embeddings to dataframe
        result_df = chunks_df.copy()
        result_df['embedding'] = all_embeddings
        result_df['model_name'] = self.model_name
        result_df['embedded_at'] = datetime.now()
        
        logger.info(f"Successfully computed {len(result_df)} embeddings")
        return result_df


def insert_embeddings_to_lakebase(
    embeddings_df: pd.DataFrame,
    conn,
    embeddings_table: str = "weather_alert_embeddings"
) -> int:
    """
    Insert chunk embeddings into Lakebase using psycopg2.
    
    Args:
        embeddings_df: DataFrame with columns [alert_id, location, chunk_index, 
                       chunk_text, embedding, model_name, embedded_at]
        conn: psycopg2 connection
        embeddings_table: Name of the embeddings table
    
    Returns:
        Number of rows inserted
    """
    if len(embeddings_df) == 0:
        logger.warning("No embeddings to insert")
        return 0
    
    logger.info(f"Inserting {len(embeddings_df)} embeddings into {embeddings_table}")
    
    # Generate unique IDs (alert_id + chunk_index)
    embeddings_df['id'] = (
        embeddings_df['alert_id'] + '_' + embeddings_df['chunk_index'].astype(str)
    )
    
    # Convert to list of dicts
    rows = embeddings_df.to_dict('records')
    
    # Prepare data tuples for batch insert
    insert_data = [
        (
            row['id'],
            row['alert_id'],
            row['location'],
            int(row['chunk_index']),
            row['chunk_text'],
            '{' + ','.join(str(float(x)) for x in row['embedding']) + '}',
            row['model_name'],
            row['embedded_at']
        )
        for row in rows
    ]
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        # Batch insert with ON CONFLICT DO NOTHING
        insert_sql = f"""
            INSERT INTO {embeddings_table} (
                id, alert_id, location, chunk_index, chunk_text, 
                embedding, model_name, embedded_at
            ) VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """
        
        cursor.executemany(insert_sql, insert_data)
        conn.commit()
        
        inserted_count = cursor.rowcount
        logger.info(f"✅ Successfully inserted {inserted_count} chunk embeddings")
        logger.info(f"   (Duplicates were skipped via ON CONFLICT DO NOTHING)")
        
        return inserted_count
        
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Database error inserting embeddings: {e}")
        raise
    finally:
        if cursor:
            cursor.close()

def batch_insert_forecasts_to_lakebase(
    forecasts: List[Dict],
    conn,
    forecast_table: str = "weather_forecast"
) -> int:
    """
    Batch insert weather forecasts into Lakebase using psycopg2.
    
    Args:
        alerts: List of normalized alert dictionaries
        conn: psycopg2 connection
        alert_table: Name of the alerts table
    
    Returns:
        Number of rows inserted
    """
    if not forecasts:
        logger.warning("No forecasts to insert")
        return 0
    logger.info(f"Inserting {len(forecasts)} forecast into table {forecast_table}")
    insert_data = [
        (
            forecast["id"],
            forecast["location"],
            forecast["number_counter"],
            forecast["day"],
            forecast["starttime"],
            forecast["endtime"],
            forecast["temperature"],
            forecast["precipitation_prob"],
            forecast["wind_speed"],
            forecast["wind_direction"],
            forecast["detailed_forecast"]
        )
        for forecast in forecasts
    ]
    cursor = None
    try:
        cursor = conn.cursor()
        insert_sql = f"""
          Insert into {forecast_table}(
            id, location, number_counter, day, starttime, endtime, temperature, precipitation_prob,wind_speed, wind_direction, detailed_forecast
        ) VALUES(
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (id) DO NOTHING
        """
        cursor.executemany(insert_sql, insert_data)
        conn.commit()
        inserted_count = cursor.rowcount
        logger.info(f"✅ Successfully inserted {inserted_count} new forecasts")
        logger.info(f"   (Duplicates were skipped via ON CONFLICT DO NOTHING)")
        
        return inserted_count
        
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Database error inserting alerts: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
            
def batch_insert_alerts_to_lakebase(
    alerts: List[Dict],
    conn,
    alert_table: str = "weather_alert_documents"
) -> int:
    """
    Batch insert weather alerts into Lakebase using psycopg2.
    
    Args:
        alerts: List of normalized alert dictionaries
        conn: psycopg2 connection
        alert_table: Name of the alerts table
    
    Returns:
        Number of rows inserted
    """
    if not alerts:
        logger.warning("No alerts to insert")
        return 0
    
    logger.info(f"Inserting {len(alerts)} alerts into {alert_table}")
    
    # Prepare data tuples for batch insert
    insert_data = [
        (
            alert['id'],
            alert['location'],
            alert['source_type'],
            alert['headline'],
            alert['description'],
            alert['instruction'],
            alert['issued_at'],
            alert['payload']
        )
        for alert in alerts
    ]
    
    cursor = None
    try:
        cursor = conn.cursor()
        
        # Batch insert with ON CONFLICT DO NOTHING
        insert_sql = f"""
            INSERT INTO {alert_table} (
                id, location, source_type, headline, description, 
                instruction, issued_at, payload, synced_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING
        """
        
        cursor.executemany(insert_sql, insert_data)
        conn.commit()
        
        inserted_count = cursor.rowcount
        logger.info(f"✅ Successfully inserted {inserted_count} new alerts")
        logger.info(f"   (Duplicates were skipped via ON CONFLICT DO NOTHING)")
        
        return inserted_count
        
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Database error inserting alerts: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
