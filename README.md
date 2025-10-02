# California Health & Environment Data Pipeline

An automated ELT (Extract, Load, Transform) pipeline that analyzes the relationship between environmental factors (air quality and weather) and respiratory illness rates in California.

## 🎯 Project Goal

Investigate whether temperature and air quality (PM2.5) correlate with respiratory disease rates by combining:
- **Air Quality Data** - PM2.5 measurements from 21 California sensors (OpenAQ)
- **Weather Data** - Daily temperature data from 6 major California cities (OpenMeteo)
- **Health Data** - Weekly flu surveillance data for California (CDC FluView via Delphi)

## 📊 Project Board
[Se vår Trello board här](https://trello.com/b/vKhhPczW/projekt-uppgift-data-enginering)

## 🏗️ Architecture

### Data Flow
```
Raw Data Sources → Ingestion (Cloud Run Jobs) → BigQuery Raw Layer
                                                      ↓
                                              Transformation Pipeline
                                                      ↓
                                    Silver Layer (Cleaned) → Gold Layer (ML-Ready)
                                                      ↓
                                              ML Analysis & Visualization
```

### GCP Infrastructure
- **Project**: `compact-marker-471008-m0`
- **Region**: `europe-north2`
- **Datasets**: `raw`, `silver`, `gold`
- **Automation**: Cloud Scheduler + Cloud Run Jobs

## 📁 Project Structure

```
GruppProjekt/
├── ingestion_pipeline_AQ/          # OpenAQ air quality ingestion
│   ├── ingestion_openaq.py         # Fetches PM2.5 data from 21 CA sensors
│   ├── cloudbuild.yaml             # Cloud Build deployment config
│   ├── Dockerfile                  # Container definition
│   └── requirements.txt            # Python dependencies
├── ingestion_pipeline_openmeteo/   # Weather data ingestion
│   ├── ingestion_openmeteo.py      # Fetches daily weather for 6 CA cities
│   ├── cloudbuild.yaml
│   ├── Dockerfile
│   └── requirements.txt
├── ingestion_pipeline_delphi/      # Flu surveillance ingestion
│   ├── ingestion_delphi.py         # Fetches weekly flu data for California
│   ├── cloudbuild.yaml
│   ├── dockerfile
│   └── requirements.txt
├── transformation/                  # Data transformation pipeline
│   ├── sql/                        # SQL transformation queries
│   │   ├── silver_*.sql            # Clean and validate raw data
│   │   └── gold_*.sql              # Join and engineer features for ML
│   └── ml-model/
│       ├── main.py                 # Transformation orchestration script
│       ├── cloudbuild.yaml         # Deployment config
│       ├── Dockerfile
│       └── requirements.txt
├── ml-model/                       # ML training pipeline (in progress)
│   └── train.py
├── docs/                           # Documentation
│   ├── DEPLOYMENT.md               # Complete deployment guide
│   ├── TROUBLESHOOTING.md          # Common issues and solutions
│   └── sprint-01/                  # Sprint documentation
└── README.md                       # This file
```

## 🚀 Getting Started

### Prerequisites

1. **Google Cloud SDK** installed and authenticated
2. **Access to GCP Project** `compact-marker-471008-m0`
3. **PowerShell** (for Windows) or Bash (for Linux/Mac)

### For New Team Members

1. **Clone the repository**
   ```bash
   git clone https://github.com/KabyAI/GruppProjekt.git
   cd GruppProjekt
   ```

2. **Authenticate with Google Cloud**
   ```bash
   gcloud auth login
   gcloud config set project compact-marker-471008-m0
   ```

3. **Verify access to BigQuery**
   ```bash
   # Check if you can see the datasets
   gcloud alpha bq datasets list
   ```

4. **Explore the data**
   - Open [BigQuery Console](https://console.cloud.google.com/bigquery?project=compact-marker-471008-m0)
   - Navigate to: `compact-marker-471008-m0` → `gold` → `health_environment_features`
   - Click "Preview" to see the ML-ready dataset

## 📊 Data Layers

### Raw Layer (`raw` dataset)
Unprocessed data directly from sources:
- `openaq_pm25_ca` - 22,958 PM2.5 measurements
- `openmeteo_daily_ca` - 8,226 daily weather records
- `fluview_ca_weekly` - 195 weeks of flu surveillance data

### Silver Layer (`silver` dataset)
Cleaned and validated data:
- `openaq_pm25_clean` - Valid PM2.5 readings (removes outliers, nulls)
- `openmeteo_weather_clean` - Standardized weather metrics
- `delphi_flu_clean` - Normalized weekly flu rates

### Gold Layer (`gold` dataset)
ML-ready feature store:
- `health_environment_features` - 190 weeks of joined data (2022-01-03 to 2022-07-11)
  - **Target variable**: `illness_rate` (weekly respiratory illness rate)
  - **Air quality features**: `pm25_avg`, `pm25_stddev`, `pm25_min`, `pm25_max`
  - **Weather features**: `temp_avg_celsius`, `temp_max_celsius`, `temp_min_celsius`
  - **Temporal features**: `year`, `month`, `quarter`, `season`
  - **Lag features**: 1-week, 2-week, 4-week lags for time series analysis
  - **Rolling averages**: 4-week moving averages

## 🔄 Running the Pipeline

### Automated Schedule (Already Configured)
The pipeline runs automatically:
- **OpenAQ ingestion**: Daily at 2:00 AM CET
- **OpenMeteo ingestion**: Daily at 3:00 AM CET
- **Delphi ingestion**: Weekly on Fridays at 4:00 AM CET
- **Transformation**: Manual (can be scheduled after ingestion)

### Manual Execution

**Run data ingestion:**
```powershell
# Ingest air quality data
gcloud run jobs execute ingest-openaq --project=compact-marker-471008-m0 --region=europe-north2 --wait

# Ingest weather data
gcloud run jobs execute ingest-openmeteo --project=compact-marker-471008-m0 --region=europe-north2 --wait

# Ingest flu data
gcloud run jobs execute ingest-delphi --project=compact-marker-471008-m0 --region=europe-north2 --wait
```

**Run transformation pipeline:**
```powershell
# Transform raw → silver → gold
gcloud run jobs execute transform-pipeline --project=compact-marker-471008-m0 --region=europe-north2 --wait
```

**Check job status:**
```powershell
# View recent executions
gcloud run jobs executions list --job=transform-pipeline --project=compact-marker-471008-m0 --region=europe-north2 --limit=5

# View logs
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="transform-pipeline"' --project=compact-marker-471008-m0 --limit=50 --freshness=1h
```

## 🔍 Exploring the Data

### Quick SQL Queries

**Check data freshness:**
```sql
SELECT 
  MIN(week_start_date) as earliest_week,
  MAX(week_start_date) as latest_week,
  COUNT(*) as total_weeks
FROM `compact-marker-471008-m0.gold.health_environment_features`;
```

**View average metrics by season:**
```sql
SELECT 
  season,
  ROUND(AVG(illness_rate), 2) as avg_illness_rate,
  ROUND(AVG(pm25_avg), 2) as avg_pm25,
  ROUND(AVG(temp_avg_celsius), 2) as avg_temp
FROM `compact-marker-471008-m0.gold.health_environment_features`
GROUP BY season
ORDER BY 
  CASE season 
    WHEN 'Winter' THEN 1 
    WHEN 'Spring' THEN 2 
    WHEN 'Summer' THEN 3 
    ELSE 4 
  END;
```

**Check correlation between PM2.5 and illness:**
```sql
SELECT 
  CORR(pm25_avg, illness_rate) as pm25_illness_correlation,
  CORR(temp_avg_celsius, illness_rate) as temp_illness_correlation
FROM `compact-marker-471008-m0.gold.health_environment_features`;
```

## 🛠️ Making Changes

### Modifying the Pipeline

1. **Update ingestion logic**
   - Edit files in `ingestion_pipeline_*/`
   - Rebuild and deploy:
     ```powershell
     $PROJECT_ID = "compact-marker-471008-m0"
     gcloud builds submit --project $PROJECT_ID --substitutions _REGION=europe-north2 --config ingestion_pipeline_AQ/cloudbuild.yaml .
     ```

2. **Update transformation logic**
   - Edit SQL files in `transformation/sql/`
   - Rebuild and deploy:
     ```powershell
     gcloud builds submit --project $PROJECT_ID --substitutions _REGION=europe-north2 --config transformation/ml-model/cloudbuild.yaml .
     ```

3. **Test your changes**
   - Run the job manually to verify
   - Check BigQuery for updated data
   - Review logs for errors

## 📚 Documentation

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Complete deployment guide with all commands and configurations
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Solutions to common issues encountered during development

## 🐛 Common Issues

### No data in BigQuery after job runs
- Check logs: `gcloud logging read 'resource.type="cloud_run_job"' --limit=50`
- Verify BigQuery permissions for service account
- See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions

### Build fails
- Check `requirements.txt` for corruption (should not be empty)
- Verify Dockerfile paths are correct
- Check Cloud Build logs in GCP Console

### Date mismatch in gold table
- Ensure week boundaries align (Delphi uses Monday-starting weeks)
- Verify `DATE_TRUNC(..., WEEK(MONDAY))` is used consistently

## 🎓 Learning Resources

- **BigQuery SQL**: [Google Cloud BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- **Cloud Run Jobs**: [Cloud Run Documentation](https://cloud.google.com/run/docs/quickstarts/jobs)
- **Cloud Scheduler**: [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)

## 👥 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes and test thoroughly
3. Commit with clear messages: `git commit -m "Add: description of changes"`
4. Push and create a pull request
5. Tag team members for review

## 📧 Support

For questions or issues:
- Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) first
- Ask in the team Slack/Discord
- Review our [Trello board](https://trello.com/b/vKhhPczW/projekt-uppgift-data-enginering)

## 📈 Next Steps

- [ ] Train ML model to analyze correlations
- [ ] Build Streamlit visualization dashboard
- [ ] Set up automated transformation scheduling
- [ ] Add more California cities to weather data
- [ ] Expand to other health metrics (COVID-19, asthma, etc.)

---

**Built with ❤️ **

## Project Structure
```
GruppProjekt/
├── docs/
│   ├── sprint-01/          # Sprint planning and documentation
│   ├── DEPLOYMENT.md       # Complete deployment guide
│   └── TROUBLESHOOTING.md  # Troubleshooting guide
├── ingestion_pipeline_AQ/
│   ├── cloudbuild.yaml     # Cloud Build configuration
│   ├── Dockerfile          # Container definition
│   ├── ingestion_openaq.py # OpenAQ data ingestion script
│   └── requirements.txt    # Python dependencies
├── ingestion_pipeline_openmeteo/
│   ├── cloudbuild.yaml
│   ├── Dockerfile
│   ├── ingestion_openmeteo.py
│   └── requirements.txt
├── ingestion_pipeline_delphi/
│   ├── cloudbuild.yaml
│   ├── dockerfile
│   ├── ingestion_delphi.py
│   └── requirements.txt
└── README.md
```

## GCP Deployment

### Current Configuration
- **Project**: `compact-marker-471008-m0`
- **Region**: `europe-north2`
- **BigQuery Dataset**: `raw`
- **Service Account**: `cloud-run-ingest@compact-marker-471008-m0.iam.gserviceaccount.com`

### Automated Schedule
- **OpenAQ**: Daily at 2 AM CET
- **OpenMeteo**: Daily at 3 AM CET  
- **Delphi**: Weekly on Fridays at 4 AM CET

### BigQuery Tables
- `raw.openaq_pm25_ca` - Air quality measurements
- `raw.openmeteo_daily_ca` - Weather data (partitioned by date)
- `raw.fluview_ca_weekly` - Flu surveillance data

## Quick Start

### Prerequisites
- Google Cloud SDK installed and authenticated
- Access to GCP project `compact-marker-471008-m0`
- PowerShell (for Windows deployment commands)

### Deploy All Pipelines
```powershell
$PROJECT_ID = "compact-marker-471008-m0"

# Build and deploy
gcloud builds submit --project $PROJECT_ID --substitutions _REGION=europe-north2 --config ingestion_pipeline_AQ/cloudbuild.yaml .
gcloud builds submit --project $PROJECT_ID --substitutions _REGION=europe-north2 --config ingestion_pipeline_openmeteo/cloudbuild.yaml .
gcloud builds submit --project $PROJECT_ID --substitutions _REGION=europe-north2 --config ingestion_pipeline_delphi/cloudbuild.yaml .
```

### Manual Execution
```powershell
# Execute individual pipelines
gcloud run jobs execute ingest-openaq --project=compact-marker-471008-m0 --region=europe-north2 --wait
gcloud run jobs execute ingest-openmeteo --project=compact-marker-471008-m0 --region=europe-north2 --wait
gcloud run jobs execute ingest-delphi --project=compact-marker-471008-m0 --region=europe-north2 --wait
```

### View Logs
```powershell
# Check job logs
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="ingest-openaq"' --project=compact-marker-471008-m0 --limit=50 --freshness=1h

# Check for errors
gcloud logging read 'resource.type="cloud_run_job" AND severity="ERROR"' --project=compact-marker-471008-m0 --limit=20 --freshness=24h
```

## Documentation
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Complete deployment guide with all commands and configurations
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions


See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.
