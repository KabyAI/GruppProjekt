-- Silver layer: Clean and validate OpenAQ PM2.5 data
-- Removes invalid readings, standardizes formats, adds data quality flags

CREATE OR REPLACE TABLE `{project_id}.silver.openaq_pm25_clean` AS
WITH cleaned_data AS (
  SELECT
    -- Temporal dimensions (keep as-is, don't parse)
    date_utc AS measurement_timestamp,
    DATE(CAST(date_utc AS TIMESTAMP)) AS measurement_date,
    
    -- Location information
    location_id,
    sensor_id,
    latitude,
    longitude,
    
    -- Measurement data
    value AS pm25_value,
    units AS pm25_unit,
    parameter,
    
    -- Data quality flags
    CASE 
      WHEN value IS NULL THEN 'NULL_VALUE'
      WHEN value < 0 THEN 'NEGATIVE_VALUE'
      WHEN value > 500 THEN 'EXTREME_VALUE'  -- EPA scale maxes at 500
      ELSE 'VALID'
    END AS data_quality_flag,
    
    -- Metadata
    CURRENT_TIMESTAMP() AS processed_at
    
  FROM `{project_id}.raw.openaq_pm25_ca`
)

SELECT *
FROM cleaned_data
WHERE data_quality_flag = 'VALID'  -- Only keep valid measurements
  AND measurement_date IS NOT NULL
  AND pm25_value BETWEEN 0 AND 500;  -- EPA Air Quality Index range
