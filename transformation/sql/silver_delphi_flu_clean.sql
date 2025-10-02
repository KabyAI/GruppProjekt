-- Silver layer: Clean and normalize Delphi flu surveillance data
-- Validates illness rates, handles weekly data structure

CREATE OR REPLACE TABLE `{project_id}.silver.delphi_flu_clean` AS
WITH cleaned_data AS (
  SELECT
    -- Temporal dimensions
    epiweek,
    CAST(week_start AS DATE) AS week_start_date,
    
    -- Geographic information
    region AS geo_code,
    'state' AS geo_type,
    
    -- Flu surveillance signals  
    wili AS flu_rate_value,
    ili AS ili_rate,
    num_ili,
    num_patients,
    
    -- Data quality flags
    CASE
      WHEN wili IS NULL THEN 'NULL_VALUE'
      WHEN wili < 0 THEN 'NEGATIVE_RATE'
      WHEN num_patients < 100 THEN 'LOW_SAMPLE_SIZE'
      ELSE 'VALID'
    END AS data_quality_flag,
    
    -- Metadata
    CURRENT_TIMESTAMP() AS processed_at
    
  FROM `{project_id}.raw.fluview_ca_weekly`
)

SELECT 
  *,
  -- Calculate stderr approximation
  CASE 
    WHEN num_patients > 0 
    THEN SQRT(flu_rate_value * (100 - flu_rate_value) / num_patients)
    ELSE NULL
  END AS flu_rate_stderr
  
FROM cleaned_data
WHERE data_quality_flag IN ('VALID', 'LOW_SAMPLE_SIZE')
  AND week_start_date IS NOT NULL
  AND flu_rate_value IS NOT NULL;
