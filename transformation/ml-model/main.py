"""
Data Transformation Pipeline: Raw -> Silver -> Gold
Executes BigQuery SQL transformations to prepare data for ML training
"""

import os
import sys
from pathlib import Path
from google.cloud import bigquery
from google.api_core import exceptions
import time

# Configuration
PROJECT_ID = os.getenv("PROJECT_ID", "compact-marker-471008-m0")
LOCATION = os.getenv("LOCATION", "europe-north2")

# SQL file paths - in container, sql/ is copied to /app/sql/
SQL_DIR = Path("/app/sql")

TRANSFORMATION_STEPS = [
    # Silver layer: Clean and validate
    {
        "name": "silver_openaq_pm25_clean",
        "sql_file": "silver_openaq_pm25_clean.sql",
        "description": "Clean and validate OpenAQ PM2.5 air quality data"
    },
    {
        "name": "silver_openmeteo_weather_clean",
        "sql_file": "silver_openmeteo_weather_clean.sql",
        "description": "Clean and standardize OpenMeteo weather data"
    },
    {
        "name": "silver_delphi_flu_clean",
        "sql_file": "silver_delphi_flu_clean.sql",
        "description": "Clean and normalize Delphi flu surveillance data"
    },
    # Gold layer: Feature engineering
    {
        "name": "gold_health_environment_features",
        "sql_file": "gold_health_environment_features.sql",
        "description": "Join and engineer features for ML training"
    }
]


def create_datasets_if_not_exist(client: bigquery.Client):
    """Create silver and gold datasets if they don't exist"""
    datasets = ["silver", "gold"]
    
    for dataset_id in datasets:
        dataset_ref = f"{PROJECT_ID}.{dataset_id}"
        
        try:
            client.get_dataset(dataset_ref)
            print(f"[INFO] Dataset {dataset_id} already exists")
        except exceptions.NotFound:
            print(f"[INFO] Creating dataset {dataset_id}...")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = LOCATION
            dataset.description = f"{dataset_id.capitalize()} layer: {'Cleaned and validated data' if dataset_id == 'silver' else 'ML-ready feature store'}"
            client.create_dataset(dataset)
            print(f"[SUCCESS] Dataset {dataset_id} created")


def run_transformation(client: bigquery.Client, step: dict) -> bool:
    """Execute a single transformation step"""
    print(f"\n{'='*60}")
    print(f"[STEP] {step['name']}")
    print(f"[DESC] {step['description']}")
    print(f"{'='*60}")
    
    # Read SQL file
    sql_path = SQL_DIR / step['sql_file']
    if not sql_path.exists():
        print(f"[ERROR] SQL file not found: {sql_path}")
        return False
    
    with open(sql_path, 'r') as f:
        sql = f.read()
    
    # Replace project_id placeholder
    sql = sql.replace('{project_id}', PROJECT_ID)
    
    print(f"[INFO] Executing SQL from {step['sql_file']}...")
    
    try:
        # Execute query
        job_config = bigquery.QueryJobConfig()
        job_config.use_legacy_sql = False
        
        query_job = client.query(sql, job_config=job_config)
        
        # Wait for completion with progress updates
        start_time = time.time()
        while not query_job.done():
            elapsed = time.time() - start_time
            print(f"[INFO] Query running... ({elapsed:.1f}s elapsed)")
            time.sleep(5)
        
        # Check for errors
        if query_job.errors:
            print(f"[ERROR] Query failed with errors:")
            for error in query_job.errors:
                print(f"  - {error}")
            return False
        
        # Get result statistics
        elapsed = time.time() - start_time
        
        # Try to get row count even if table doesn't exist yet
        try:
            result_rows = query_job.result()
            row_count = query_job.total_rows if hasattr(query_job, 'total_rows') else 0
            print(f"[INFO] Query result rows: {row_count}")
        except Exception as e:
            print(f"[DEBUG] Could not get result rows: {str(e)}")
        
        if query_job.statement_type == 'CREATE_TABLE':
            # For CREATE OR REPLACE TABLE, check the destination table
            destination_table = query_job.destination
            if destination_table:
                try:
                    table = client.get_table(destination_table)
                    print(f"[SUCCESS] Table created: {table.full_table_id}")
                    print(f"[INFO] Total rows: {table.num_rows:,}")
                    print(f"[INFO] Table size: {table.num_bytes / (1024**2):.2f} MB")
                except Exception as e:
                    print(f"[WARNING] Table created but could not fetch details: {str(e)}")
            else:
                print(f"[WARNING] CREATE TABLE query completed but no destination table set - likely 0 rows returned")
        else:
            print(f"[SUCCESS] Query completed")
            if query_job.total_bytes_processed:
                print(f"[INFO] Bytes processed: {query_job.total_bytes_processed / (1024**2):.2f} MB")
        
        print(f"[INFO] Execution time: {elapsed:.2f}s")
        return True
        
    except Exception as e:
        print(f"[ERROR] Transformation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main transformation pipeline"""
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║   Data Transformation Pipeline: Raw -> Silver -> Gold    ║
    ║   Project: {PROJECT_ID:^43} ║
    ║   Location: {LOCATION:^42} ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Initialize BigQuery client
    try:
        client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
        print(f"[INFO] Connected to BigQuery project: {PROJECT_ID}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize BigQuery client: {str(e)}")
        sys.exit(1)
    
    # Create datasets if needed
    print("\n[PHASE 1] Ensuring datasets exist...")
    create_datasets_if_not_exist(client)
    
    # Execute transformation steps
    print("\n[PHASE 2] Executing transformations...")
    
    success_count = 0
    failed_steps = []
    
    pipeline_start = time.time()
    
    for step in TRANSFORMATION_STEPS:
        success = run_transformation(client, step)
        
        if success:
            success_count += 1
        else:
            failed_steps.append(step['name'])
            print(f"[WARNING] Step {step['name']} failed, continuing...")
    
    pipeline_duration = time.time() - pipeline_start
    
    # Summary
    print(f"\n{'='*60}")
    print(f"[SUMMARY] Transformation Pipeline Complete")
    print(f"{'='*60}")
    print(f"Total steps: {len(TRANSFORMATION_STEPS)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed_steps)}")
    print(f"Total duration: {pipeline_duration:.2f}s")
    
    if failed_steps:
        print(f"\n[WARNING] Failed steps:")
        for step in failed_steps:
            print(f"  - {step}")
    
    # Verify gold table
    if success_count == len(TRANSFORMATION_STEPS):
        print("\n[VERIFICATION] Checking gold.health_environment_features...")
        try:
            table = client.get_table(f"{PROJECT_ID}.gold.health_environment_features")
            print(f"[SUCCESS] Gold table ready for ML training!")
            print(f"[INFO] Total records: {table.num_rows:,}")
            print(f"[INFO] Schema fields: {len(table.schema)}")
            
            # Sample query to show date range
            query = f"""
            SELECT 
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(*) as total_rows,
                COUNT(DISTINCT date) as unique_dates
            FROM `{PROJECT_ID}.gold.health_environment_features`
            """
            result = client.query(query).result()
            row = list(result)[0]
            print(f"[INFO] Date range: {row.min_date} to {row.max_date}")
            print(f"[INFO] Unique dates: {row.unique_dates}")
            
        except Exception as e:
            print(f"[WARNING] Could not verify gold table: {str(e)}")
    
    # Exit with appropriate code
    if failed_steps:
        print("\n[EXIT] Pipeline completed with errors")
        sys.exit(1)
    else:
        print("\n[EXIT] Pipeline completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
