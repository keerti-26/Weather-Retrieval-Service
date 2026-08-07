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

-- Create index for alert lookups
CREATE INDEX IF NOT EXISTS idx_weather_alert_documents
ON weather_alert_documents(location);

-- Verify the table was created
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'weather_alert_documents'
ORDER BY ordinal_position;