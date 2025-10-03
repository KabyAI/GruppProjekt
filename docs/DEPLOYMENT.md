# GCP Data Ingestion Pipelines - Deployment Guide

## Overview
This project contains three data ingestion pipelines deployed as Cloud Run Jobs on GCP:
- **OpenAQ**: Air quality (PM2.5) data from California sensors
- **OpenMeteo**: Weather data for California cities
- **Delphi**: Flu surveillance data for California

## GCP Project Configuration

### Project Details
- **Project ID**: `compact-marker-471008-m0`
- **Project Number**: `285204042086`
- **Region**: `europe-north2` (Cloud Run Jobs, BigQuery, Artifact Registry)
- **Scheduler Region**: `europe-west1` (Cloud Scheduler location)

### Service Accounts
- **Main SA**: `cloud-run-ingest@compact-marker-471008-m0.iam.gserviceaccount.com`
  - Roles:
    - `roles/artifactregistry.reader`
    - `roles/bigquery.dataEditor`
    - `roles/bigquery.jobUser`
    - `roles/logging.logWriter`
    - `roles/secretmanager.secretAccessor`

### Secrets
- **openaq-api-key**: OpenAQ API key stored in Secret Manager
  - Access granted to `cloud-run-ingest` service account

## Infrastructure Components

### BigQuery
- **Dataset**: `raw` (in `europe-north2`)
- **Tables**:
  - `openaq_pm25_ca`: Air quality PM2.5 data
  - `openmeteo_daily_ca`: Daily weather data (partitioned by date)
  - `fluview_ca_weekly`: Weekly flu surveillance data

### Artifact Registry
- **Repository**: `starfish-docker`
- **Location**: `europe-north2`
- **Images**:
  - `ingest-openaq:latest`
  - `ingest-openmeteo:latest`
  - `ingest-delphi:latest`

### Cloud Run Jobs
All jobs configured with:
- Memory: 2Gi
- CPU: 1000m
- Max retries: 3
- Task timeout: 10m
- Execution environment: gen2

#### Job: ingest-openaq
- **Image**: `europe-north2-docker.pkg.dev/compact-marker-471008-m0/starfish-docker/ingest-openaq:latest`
- **Environment Variables**:
  - `GOOGLE_CLOUD_PROJECT=compact-marker-471008-m0`
  - `BQ_LOCATION=europe-north2`
  - `BQ_DATASET_RAW=raw`
  - `BQ_TABLE_RAW=openaq_pm25_ca`
  - `DATE_FROM=2022-01-01`
  - `PARAMETER_ID=2` (PM2.5)
  - `IDS=2009 2134 1256 8590 232 890 786 791 6836 2057 2156 1186 8721 6767 2822 2781 2945 3795 6606 7035 3548`
- **Secrets**: `OPENAQ_API_KEY` from Secret Manager

#### Job: ingest-openmeteo
- **Image**: `europe-north2-docker.pkg.dev/compact-marker-471008-m0/starfish-docker/ingest-openmeteo:latest`
- **Environment Variables**:
  - `GOOGLE_CLOUD_PROJECT=compact-marker-471008-m0`
  - `BQ_LOCATION=europe-north2`
  - `BQ_DATASET=raw`
  - `BQ_TABLE=openmeteo_daily_ca`
  - `START_DATE=2022-01-01`
  - `POINTS=37.34,-121.89,sj;38.58,-121.49,sac;32.72,-117.16,sd;34.05,-118.24,la;37.77,-122.42,sf;36.74,-119.78,fresno`

#### Job: ingest-delphi
- **Image**: `europe-north2-docker.pkg.dev/compact-marker-471008-m0/starfish-docker/ingest-delphi:latest`
- **Environment Variables**:
  - `GOOGLE_CLOUD_PROJECT=compact-marker-471008-m0`
  - `BQ_LOCATION=europe-north2`
  - `BQ_DATASET=raw`
  - `BQ_TABLE=fluview_ca_weekly`
  - `REGIONS=ca,state:ca`
  - `START_DATE=2022-01-01`

### Cloud Scheduler Jobs
- **scheduler-ingest-openaq**
  - Schedule: `0 2 * * *` (Daily at 2 AM CET)
  - Target: Cloud Run Job `ingest-openaq`
  
- **scheduler-ingest-openmeteo**
  - Schedule: `0 3 * * *` (Daily at 3 AM CET)
  - Target: Cloud Run Job `ingest-openmeteo`
  
- **scheduler-ingest-delphi**
  - Schedule: `0 4 * * 5` (Every Friday at 4 AM CET)
  - Target: Cloud Run Job `ingest-delphi`

## Deployment Commands

### Build and Deploy All Pipelines
```powershell
$PROJECT_ID = "compact-marker-471008-m0"

# OpenAQ
gcloud builds submit `
  --project $PROJECT_ID `
  --substitutions _REGION=europe-north2 `
  --config ingestion_pipeline_AQ/cloudbuild.yaml .

# OpenMeteo
gcloud builds submit `
  --project $PROJECT_ID `
  --substitutions _REGION=europe-north2 `
  --config ingestion_pipeline_openmeteo/cloudbuild.yaml .

# Delphi
gcloud builds submit `
  --project $PROJECT_ID `
  --substitutions _REGION=europe-north2 `
  --config ingestion_pipeline_delphi/cloudbuild.yaml .
```

### Manual Job Execution
```powershell
# Execute OpenAQ
gcloud run jobs execute ingest-openaq `
  --project=compact-marker-471008-m0 `
  --region=europe-north2 `
  --wait

# Execute OpenMeteo
gcloud run jobs execute ingest-openmeteo `
  --project=compact-marker-471008-m0 `
  --region=europe-north2 `
  --wait

# Execute Delphi
gcloud run jobs execute ingest-delphi `
  --project=compact-marker-471008-m0 `
  --region=europe-north2 `
  --wait
```

### Trigger Scheduler Manually
```powershell
# Trigger OpenAQ scheduler
gcloud scheduler jobs run scheduler-ingest-openaq `
  --location=europe-west1 `
  --project=compact-marker-471008-m0

# Trigger OpenMeteo scheduler
gcloud scheduler jobs run scheduler-ingest-openmeteo `
  --location=europe-west1 `
  --project=compact-marker-471008-m0

# Trigger Delphi scheduler
gcloud scheduler jobs run scheduler-ingest-delphi `
  --location=europe-west1 `
  --project=compact-marker-471008-m0
```

## Monitoring

### Check Job Execution Status
```powershell
# List recent executions
gcloud run jobs executions list `
  --job=ingest-openaq `
  --project=compact-marker-471008-m0 `
  --region=europe-north2 `
  --limit=5

# Describe specific execution
gcloud run jobs executions describe <EXECUTION_NAME> `
  --project=compact-marker-471008-m0 `
  --region=europe-north2
```

### View Logs
```powershell
# View recent logs for a job
gcloud logging read `
  'resource.type="cloud_run_job" AND resource.labels.job_name="ingest-openaq"' `
  --project=compact-marker-471008-m0 `
  --limit=50 `
  --freshness=1h

# View error logs only
gcloud logging read `
  'resource.type="cloud_run_job" AND resource.labels.job_name="ingest-openaq" AND severity="ERROR"' `
  --project=compact-marker-471008-m0 `
  --limit=20 `
  --freshness=24h
```

### Check Scheduler Status
```powershell
# List all scheduler jobs
gcloud scheduler jobs list `
  --location=europe-west1 `
  --project=compact-marker-471008-m0

# View scheduler job details
gcloud scheduler jobs describe scheduler-ingest-openaq `
  --location=europe-west1 `
  --project=compact-marker-471008-m0
```

### Query BigQuery Tables
```powershell
# Check row counts
bq query --use_legacy_sql=false `
  'SELECT 
    (SELECT COUNT(*) FROM `compact-marker-471008-m0.raw.openaq_pm25_ca`) as openaq_rows,
    (SELECT COUNT(*) FROM `compact-marker-471008-m0.raw.openmeteo_daily_ca`) as openmeteo_rows,
    (SELECT COUNT(*) FROM `compact-marker-471008-m0.raw.fluview_ca_weekly`) as delphi_rows'

# Check latest data
bq query --use_legacy_sql=false `
  'SELECT MAX(date) as latest_date FROM `compact-marker-471008-m0.raw.openmeteo_daily_ca`'
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed troubleshooting guide.

## Maintenance

### Updating Job Configuration
To update environment variables or other job settings:
```powershell
gcloud run jobs update ingest-openaq `
  --region=europe-north2 `
  --update-env-vars="NEW_VAR=value" `
  --project=compact-marker-471008-m0
```

### Updating Scheduler
```powershell
# Change schedule
gcloud scheduler jobs update http scheduler-ingest-openaq `
  --location=europe-west1 `
  --schedule="0 3 * * *" `
  --project=compact-marker-471008-m0

# Pause scheduler
gcloud scheduler jobs pause scheduler-ingest-openaq `
  --location=europe-west1 `
  --project=compact-marker-471008-m0

# Resume scheduler
gcloud scheduler jobs resume scheduler-ingest-openaq `
  --location=europe-west1 `
  --project=compact-marker-471008-m0
```

### Cleaning Up Tables
If you need to drop and recreate a table:
```powershell
# Using REST API (bq command may have issues)
$token = gcloud auth print-access-token
Invoke-RestMethod `
  -Uri "https://bigquery.googleapis.com/bigquery/v2/projects/compact-marker-471008-m0/datasets/raw/tables/TABLE_NAME" `
  -Method DELETE `
  -Headers @{Authorization="Bearer $token"}
```
