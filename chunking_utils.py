"""Text chunking utilities for weather alert content."""
import logging
from typing import List, Dict, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    chunks = []
    step = chunk_size - chunk_overlap
    
    for start in range(0, len(text), step):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        
        # Stop if this chunk reaches the end
        if start + chunk_size >= len(text):
            break
    
    return chunks


def chunk_alerts_dataframe(
    alerts_df: pd.DataFrame,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    text_column: str = "embedding_text"
) -> pd.DataFrame:
    """
    Chunk alert documents from a DataFrame.
    
    Args:
        alerts_df: DataFrame with columns [id, location, embedding_text]
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        text_column: Name of the column containing text to chunk
    
    Returns:
        DataFrame with columns [alert_id, location, chunk_index, chunk_text]
    """
    logger.info(f"Chunking {len(alerts_df)} alerts with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    out_alert_ids = []
    out_locations = []
    out_chunk_indexes = []
    out_chunk_texts = []
    
    for idx, row in alerts_df.iterrows():
        alert_id = row['id']
        location = row['location']
        text = row[text_column]
        
        # Skip empty or null text
        if pd.isna(text) or not text.strip():
            logger.warning(f"Skipping alert {alert_id} with empty text")
            continue
        
        # Generate chunks for this alert
        chunks = chunk_text(text, chunk_size, chunk_overlap)
        
        # Store each chunk with metadata
        for chunk_index, chunk in enumerate(chunks):
            out_alert_ids.append(alert_id)
            out_locations.append(location)
            out_chunk_indexes.append(chunk_index)
            out_chunk_texts.append(chunk)
        
        # Progress logging
        if (idx + 1) % 10 == 0:
            logger.info(f"  Processed {idx + 1}/{len(alerts_df)} alerts")
    
    chunks_df = pd.DataFrame({
        "alert_id": out_alert_ids,
        "location": out_locations,
        "chunk_index": out_chunk_indexes,
        "chunk_text": out_chunk_texts,
    })
    
    logger.info(f"Generated {len(chunks_df)} chunks from {len(alerts_df)} alerts")
    return chunks_df


def load_unemdedded_alerts_from_db(
    conn,
    alert_table: str = "weather_alert_documents",
    embeddings_table: str = "weather_alert_embeddings"
) -> pd.DataFrame:
    """
    Load alerts that haven't been embedded yet.
    
    Args:
        conn: psycopg2 connection
        alert_table: Name of the alerts table
        embeddings_table: Name of the embeddings table
    
    Returns:
        DataFrame with columns [id, location, source_type, headline, issued_at, embedding_text]
    """
    query = f"""
        SELECT 
            d.id,
            d.location,
            d.source_type,
            d.headline,
            d.issued_at,
            TRIM(CONCAT(COALESCE(d.description, ''), '. ', COALESCE(d.instruction, ''))) AS embedding_text
        FROM {alert_table} d
        LEFT JOIN {embeddings_table} e ON d.id = e.alert_id
        WHERE e.alert_id IS NULL
          AND TRIM(CONCAT(COALESCE(d.description, ''), '. ', COALESCE(d.instruction, ''))) != ''
    """
    
    logger.info(f"Loading un-embedded alerts from {alert_table}")
    df = pd.read_sql_query(query, conn)
    logger.info(f"Found {len(df)} alerts without embeddings")
    
    return df


def load_all_alerts_from_db(
    conn,
    alert_table: str = "weather_alert_documents"
) -> pd.DataFrame:
    """
    Load all alerts from the database for embedding.
    
    Args:
        conn: psycopg2 connection
        alert_table: Name of the alerts table
    
    Returns:
        DataFrame with columns [id, location, source_type, headline, issued_at, embedding_text]
    """
    query = f"""
        SELECT 
            id,
            location,
            source_type,
            headline,
            issued_at,
            TRIM(CONCAT(COALESCE(description, ''), '. ', COALESCE(instruction, ''))) AS embedding_text
        FROM {alert_table}
        WHERE TRIM(CONCAT(COALESCE(description, ''), '. ', COALESCE(instruction, ''))) != ''
    """
    
    logger.info(f"Loading all alerts from {alert_table}")
    df = pd.read_sql_query(query, conn)
    logger.info(f"Loaded {len(df)} alerts")
    
    return df
