-- Gold layer: Feature engineering for ML model (WEEKLY aggregation)
-- Joins weather, air quality, and flu data with WEEKLY temporal alignment
-- Goal: Predict respiratory illness from environmental factors
-- Strategy: Aggregate daily air quality and weather to weekly to match Delphi flu data

CREATE OR REPLACE TABLE `{project_id}.gold.health_environment_features` AS

WITH 
-- Step 1: Get weekly flu data (already weekly from Delphi)
weekly_flu AS (
  SELECT
    week_start_date,
    epiweek,
    geo_code,
    geo_type,
    flu_rate_value AS illness_rate,
    flu_rate_stderr AS illness_rate_stderr,
    num_patients AS illness_sample_size
  FROM `{project_id}.silver.delphi_flu_clean`
  WHERE geo_type = 'state'  -- Use state-level data for California
),

-- Step 2: Aggregate air quality to WEEKLY (matching flu week boundaries)
weekly_air_quality AS (
  SELECT
    DATE_TRUNC(measurement_date, WEEK(MONDAY)) AS week_start_date,  -- Week starts on Monday (matches Delphi)
    AVG(pm25_value) AS pm25_avg,
    STDDEV(pm25_value) AS pm25_stddev,
    MIN(pm25_value) AS pm25_min,
    MAX(pm25_value) AS pm25_max,
    COUNT(*) AS num_measurements,
    COUNT(DISTINCT location_id) AS num_sensors,
    -- Air quality category (EPA standard)
    CASE
      WHEN AVG(pm25_value) <= 12.0 THEN 'Good'
      WHEN AVG(pm25_value) <= 35.4 THEN 'Moderate'
      WHEN AVG(pm25_value) <= 55.4 THEN 'Unhealthy for Sensitive'
      WHEN AVG(pm25_value) <= 150.4 THEN 'Unhealthy'
      WHEN AVG(pm25_value) <= 250.4 THEN 'Very Unhealthy'
      ELSE 'Hazardous'
    END AS air_quality_category
  FROM `{project_id}.silver.openaq_pm25_clean`
  GROUP BY week_start_date
),

-- Step 3: Aggregate weather to WEEKLY (average across all CA cities per week)
weekly_weather AS (
  SELECT
    DATE_TRUNC(measurement_date, WEEK(MONDAY)) AS week_start_date,  -- Week starts on Monday (matches Delphi)
    AVG(temp_mean_celsius) AS temp_avg_celsius,
    AVG(temp_max_celsius) AS temp_max_celsius,
    AVG(temp_min_celsius) AS temp_min_celsius,
    STDDEV(temp_mean_celsius) AS temp_stddev,
    CAST(NULL AS FLOAT64) AS precipitation_total_mm,  -- Not available in simplified silver
    CAST(NULL AS FLOAT64) AS precipitation_avg_mm,
    COUNT(DISTINCT city) AS num_cities,
    COUNT(*) AS num_days
  FROM `{project_id}.silver.openmeteo_weather_clean`
  GROUP BY week_start_date
),

-- Step 4: Join all data sources on week_start_date
joined_data AS (
  SELECT
    f.week_start_date,
    f.epiweek,
    
    -- Target variable: Flu/respiratory illness rate
    f.illness_rate,
    f.illness_rate_stderr,
    f.illness_sample_size,
    
    -- Air quality features (weekly aggregates)
    aq.pm25_avg,
    aq.pm25_stddev,
    aq.pm25_min,
    aq.pm25_max,
    aq.num_measurements AS pm25_measurements,
    aq.num_sensors,
    aq.air_quality_category,
    
    -- Weather features (weekly aggregates)
    w.temp_avg_celsius,
    w.temp_max_celsius,
    w.temp_min_celsius,
    w.temp_stddev,
    w.precipitation_total_mm,
    w.precipitation_avg_mm,
    w.num_cities,
    w.num_days AS weather_days,
    
    -- Data completeness flag
    CASE
      WHEN aq.pm25_avg IS NULL THEN 'MISSING_AIR_QUALITY'
      WHEN w.temp_avg_celsius IS NULL THEN 'MISSING_WEATHER'
      WHEN w.num_days < 5 THEN 'INCOMPLETE_WEEK'  -- Flag weeks with less than 5 days of data
      ELSE 'COMPLETE'
    END AS data_completeness
    
  FROM weekly_flu f
  LEFT JOIN weekly_air_quality aq ON f.week_start_date = aq.week_start_date
  LEFT JOIN weekly_weather w ON f.week_start_date = w.week_start_date
)

-- Step 5: Add temporal and derived features for ML
SELECT
  *,
  
  -- Temporal features
  EXTRACT(YEAR FROM week_start_date) AS year,
  EXTRACT(MONTH FROM week_start_date) AS month,
  EXTRACT(QUARTER FROM week_start_date) AS quarter,
  
  -- Season indicator (important for respiratory illness)
  CASE
    WHEN EXTRACT(MONTH FROM week_start_date) IN (12, 1, 2) THEN 'Winter'
    WHEN EXTRACT(MONTH FROM week_start_date) IN (3, 4, 5) THEN 'Spring'
    WHEN EXTRACT(MONTH FROM week_start_date) IN (6, 7, 8) THEN 'Summer'
    ELSE 'Fall'
  END AS season,
  
  -- Derived features
  temp_max_celsius - temp_min_celsius AS temp_range_celsius,
  
  -- Lag features (previous weeks for time series modeling)
  LAG(illness_rate, 1) OVER (ORDER BY week_start_date) AS illness_rate_lag_1w,
  LAG(illness_rate, 2) OVER (ORDER BY week_start_date) AS illness_rate_lag_2w,
  LAG(illness_rate, 4) OVER (ORDER BY week_start_date) AS illness_rate_lag_4w,
  
  LAG(pm25_avg, 1) OVER (ORDER BY week_start_date) AS pm25_avg_lag_1w,
  LAG(temp_avg_celsius, 1) OVER (ORDER BY week_start_date) AS temp_avg_lag_1w,
  
  -- Rolling averages (4-week window for smoothing)
  AVG(pm25_avg) OVER (ORDER BY week_start_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS pm25_rolling_4w,
  AVG(temp_avg_celsius) OVER (ORDER BY week_start_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS temp_rolling_4w,
  AVG(illness_rate) OVER (ORDER BY week_start_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS illness_rate_rolling_4w,
  
  -- Metadata
  CURRENT_TIMESTAMP() AS processed_at

FROM joined_data
WHERE data_completeness IN ('COMPLETE', 'INCOMPLETE_WEEK')  -- Keep weeks with some data
  AND week_start_date >= '2022-01-01'  -- Match the start date from ingestion
ORDER BY week_start_date;

-- Add table options
ALTER TABLE `{project_id}.gold.health_environment_features`
SET OPTIONS (
  description = 'ML-ready WEEKLY dataset joining respiratory illness rates with air quality and weather data for California. Each row = 1 week. Target: illness_rate (weekly). Features: PM2.5 (weekly avg), temperature (weekly avg), precipitation (weekly total), wind, temporal indicators, and lag features.',
  partition_expiration_days = NULL
);

-- Add table options
ALTER TABLE `{project_id}.gold.health_environment_features`
SET OPTIONS (
  description = 'ML-ready dataset joining respiratory illness rates with air quality and weather data for California. Target: illness_rate, Features: PM2.5, temperature, precipitation, wind, temporal indicators, and lag features.',
  partition_expiration_days = NULL
);
