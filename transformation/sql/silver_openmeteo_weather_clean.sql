-- Silver layer: Clean and standardize OpenMeteo weather data
-- Validates weather measurements, standardizes units

CREATE OR REPLACE TABLE `{project_id}.silver.openmeteo_weather_clean` AS
WITH cleaned_data AS (
  SELECT
    -- Temporal dimensions
    CAST(date AS DATE) AS measurement_date,
    
    -- Location information
    region_label AS city,
    lat AS latitude,
    lon AS longitude,
    
    -- Temperature metrics (already in Celsius from ingestion)
    temp_max AS temp_max_celsius,
    temp_min AS temp_min_celsius,
    temp_mean AS temp_mean_celsius,
    
    -- Data quality assessment
    CASE
      WHEN temp_mean IS NULL THEN 'MISSING_TEMP'
      WHEN temp_mean < -50 OR temp_mean > 60 THEN 'INVALID_TEMP'  -- Extreme temps for California
      ELSE 'VALID'
    END AS data_quality_flag,
    
    -- Metadata
    CURRENT_TIMESTAMP() AS processed_at
    
  FROM `{project_id}.raw.openmeteo_daily_ca`
)

SELECT *
FROM cleaned_data
WHERE data_quality_flag = 'VALID'
  AND measurement_date IS NOT NULL;
