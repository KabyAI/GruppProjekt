# Troubleshooting Guide

## Common Issues and Solutions

### 1. Job Completes Successfully But No Data in BigQuery

**Symptoms:**
- Cloud Run Job shows "1 / 1 complete" with exit code 0
- No errors in logs
- BigQuery table doesn't exist or has no new data

**Root Causes:**
1. **Empty/Corrupted requirements.txt**
   - Python dependencies not installed in Docker image
   - Script fails with `ModuleNotFoundError` but exits silently

2. **Missing stdout logs**
   - Python output buffering prevents logs from appearing
   - Can't see script execution progress

**Solutions:**

#### Check if packages are installed during build:
```powershell
# Look for "Successfully installed" in build logs
gcloud builds list --project=compact-marker-471008-m0 --limit=1
gcloud builds log <BUILD_ID> | Select-String "Successfully installed"
```

If you don't see package installation, check your `requirements.txt`:
```powershell
# Verify file content (should show actual package names)
Get-Content requirements.txt -Raw | Format-Hex | Select-Object -First 5
```

If the file shows only `0D 0A` (empty), recreate it:
```powershell
# For OpenAQ
@"
google-cloud-bigquery==3.25.0
requests==2.32.3
"@ | Set-Content -Path "ingestion_pipeline_AQ/requirements.txt" -NoNewline

# For Delphi
@"
requests==2.32.3
pandas==2.2.2
google-cloud-bigquery==3.25.0
pyarrow==16.1.0
dbt-bigquery==1.6.1
dbt-core==1.6.1
pyyaml
"@ | Set-Content -Path "ingestion_pipeline_delphi/requirements.txt" -NoNewline
```

#### Add verbose pip output to Dockerfile:
```dockerfile
RUN cat requirements.txt && pip install -v --no-cache-dir -r requirements.txt
```

#### Ensure Python unbuffered output:
```dockerfile
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "script_name.py"]
```

#### Add debug logging to Python scripts:
```python
if __name__ == "__main__":
    print("[DEBUG] Script starting", flush=True)
    main()
    print("[DEBUG] Script finished", flush=True)
```

---

### 2. BigQuery Schema Incompatibility Error

**Symptoms:**
```
ERROR: Existing table has incompatible field
field: epiweek
current_type: INTEGER
expected_type: INT64
```

**Root Cause:**
Table exists from previous run with different schema (e.g., `INTEGER` vs `INT64`)

**Solution:**
Drop and recreate the table:
```powershell
# Method 1: Using REST API (recommended if bq command fails)
$token = gcloud auth print-access-token
Invoke-RestMethod `
  -Uri "https://bigquery.googleapis.com/bigquery/v2/projects/compact-marker-471008-m0/datasets/raw/tables/TABLE_NAME" `
  -Method DELETE `
  -Headers @{Authorization="Bearer $token"}

# Method 2: Using bq command
bq rm -f --table compact-marker-471008-m0:raw.TABLE_NAME

# Then re-run the job to recreate with correct schema
gcloud run jobs execute JOB_NAME `
  --project=compact-marker-471008-m0 `
  --region=europe-north2 `
  --wait
```

---

### 3. TypeError: log() got multiple values for argument 'message'

**Symptoms:**
```
TypeError: log() got multiple values for argument 'message'
  File "/app/ingestion_delphi.py", line 239, in fetch
```

**Root Cause:**
Python function signature conflict - using `message=` as both positional and keyword argument.

**Solution:**
In `ingestion_delphi.py`, change the keyword argument name:
```python
# BEFORE (line ~244):
log(
    "ERROR",
    "Delphi API returned error payload",
    region=region,
    message=payload.get("message"),  # ❌ Conflicts with function parameter
)

# AFTER:
log(
    "ERROR",
    "Delphi API returned error payload",
    region=region,
    error_message=payload.get("message"),  # ✅ Use different name
)
```

---

### 4. Secret Manager Access Denied

**Symptoms:**
```
ERROR: Secret 'openaq-api-key' not found
Permission denied on secret
```

**Solutions:**

#### Verify secret exists:
```powershell
gcloud secrets list --project=compact-marker-471008-m0
```

#### Check service account has access:
```powershell
gcloud secrets get-iam-policy openaq-api-key `
  --project=compact-marker-471008-m0
```

#### Grant access if missing:
```powershell
gcloud secrets add-iam-policy-binding openaq-api-key `
  --member="serviceAccount:cloud-run-ingest@compact-marker-471008-m0.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor" `
  --project=compact-marker-471008-m0
```

---

### 5. Cloud Build Fails with Docker Parse Error

**Symptoms:**
```
ERROR: failed to solve: dockerfile parse error on line 1: unknown instruction:
```

**Root Cause:**
Leading blank line or whitespace at start of Dockerfile

**Solution:**
Remove any blank lines at the beginning of the Dockerfile:
```powershell
# Check for leading whitespace
Get-Content dockerfile -Raw | Format-Hex | Select-Object -First 3

# If you see 0D 0A at the start, edit the file to remove it
```

---

### 6. Cloud Build Substitution Variable Errors

**Symptoms:**
```
ERROR: substitution _VAR_NAME is not defined
unknown built-in substitution variable: $SHORT_SHA
```

**Solutions:**

#### Use built-in substitutions correctly:
```yaml
# ❌ WRONG: $SHORT_SHA may not work in all contexts
_IMAGE_TAG: '$SHORT_SHA'

# ✅ RIGHT: Use literal value
_IMAGE_TAG: 'latest'
```

#### Define all custom substitutions:
```yaml
substitutions:
  _PROJECT_ID: 'compact-marker-471008-m0'
  _REGION: 'europe-north2'
  _IMAGE_TAG: 'latest'
```

---

### 7. Semicolon in Environment Variable Causes Build Failure

**Symptoms:**
Build fails when env var contains semicolons (e.g., coordinates with `;` separator)

**Solution:**
Use bash variable to escape semicolons:
```yaml
- name: gcr.io/google.com/cloudsdktool/cloud-sdk:slim
  entrypoint: bash
  args:
    - -c
    - |-
      set -exo pipefail
      # Store in bash variable with single quotes
      POINTS='37.34,-121.89,sj;38.58,-121.49,sac'
      
      # Reference the variable
      gcloud run jobs deploy job-name \
        --update-env-vars="POINTS=${POINTS}"
```

---

### 8. Cloud Scheduler Not Triggering Jobs

**Symptoms:**
- Scheduler shows as ENABLED
- No new job executions appearing

**Diagnostics:**
```powershell
# Check scheduler status
gcloud scheduler jobs describe scheduler-ingest-openaq `
  --location=europe-west1 `
  --project=compact-marker-471008-m0

# View scheduler logs
gcloud logging read `
  'resource.type="cloud_scheduler_job" AND resource.labels.job_name="scheduler-ingest-openaq"' `
  --project=compact-marker-471008-m0 `
  --limit=10 `
  --freshness=24h
```

**Solutions:**

#### Verify service account has Cloud Run Invoker role:
```powershell
gcloud projects get-iam-policy compact-marker-471008-m0 `
  --flatten="bindings[].members" `
  --filter="bindings.members:cloud-run-ingest@compact-marker-471008-m0.iam.gserviceaccount.com"
```

#### Test scheduler manually:
```powershell
gcloud scheduler jobs run scheduler-ingest-openaq `
  --location=europe-west1 `
  --project=compact-marker-471008-m0
```

#### Check if correct URI format:
```
https://europe-north2-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/JOB_NAME:run
```

---

### 9. Permission Denied Errors in BigQuery

**Symptoms:**
```
403 Access Denied: Permission bigquery.tables.list denied
Permission bigquery.datasets.get denied
```

**Solution:**
Ensure service account has required BigQuery roles:
```powershell
# Grant necessary roles
gcloud projects add-iam-policy-binding compact-marker-471008-m0 `
  --member="serviceAccount:cloud-run-ingest@compact-marker-471008-m0.iam.gserviceaccount.com" `
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding compact-marker-471008-m0 `
  --member="serviceAccount:cloud-run-ingest@compact-marker-471008-m0.iam.gserviceaccount.com" `
  --role="roles/bigquery.jobUser"
```

---

### 10. No Application Logs Appearing

**Symptoms:**
- Job completes but only shows "Container called exit(0)"
- No Python print statements in logs

**Solutions:**

1. **Ensure Python unbuffered output:**
   ```dockerfile
   ENV PYTHONUNBUFFERED=1
   CMD ["python", "-u", "script.py"]
   ```

2. **Use flush=True in print statements:**
   ```python
   print("Message", flush=True)
   ```

3. **Use Python logging module:**
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   logger.info("Message")
   ```

4. **Check Cloud Logging configuration:**
   ```powershell
   # Verify logs are being written
   gcloud logging read `
     'resource.type="cloud_run_job"' `
     --project=compact-marker-471008-m0 `
     --limit=5 `
     --freshness=5m
   ```

---

## Debugging Workflow

### Step 1: Check Job Execution Status
```powershell
gcloud run jobs executions list `
  --job=JOB_NAME `
  --project=compact-marker-471008-m0 `
  --region=europe-north2 `
  --limit=5
```

### Step 2: Check Logs
```powershell
# Get all logs
gcloud logging read `
  'resource.type="cloud_run_job" AND resource.labels.job_name="JOB_NAME"' `
  --project=compact-marker-471008-m0 `
  --limit=100 `
  --freshness=1h

# Get only errors
gcloud logging read `
  'resource.type="cloud_run_job" AND resource.labels.job_name="JOB_NAME" AND severity="ERROR"' `
  --project=compact-marker-471008-m0 `
  --limit=20 `
  --freshness=24h
```

### Step 3: Check BigQuery Activity
```powershell
# Check for BigQuery API calls from service account
gcloud logging read `
  'resource.type="bigquery_resource" AND protoPayload.authenticationInfo.principalEmail="cloud-run-ingest@compact-marker-471008-m0.iam.gserviceaccount.com"' `
  --project=compact-marker-471008-m0 `
  --limit=10 `
  --freshness=1h
```

### Step 4: Verify Build Process
```powershell
# Check latest build
gcloud builds list --project=compact-marker-471008-m0 --limit=1

# Get build logs
gcloud builds log BUILD_ID --project=compact-marker-471008-m0

# Look for package installation
gcloud builds log BUILD_ID | Select-String "Successfully installed|Collecting"
```

### Step 5: Test Manually
```powershell
# Execute job manually with wait
gcloud run jobs execute JOB_NAME `
  --project=compact-marker-471008-m0 `
  --region=europe-north2 `
  --wait

# Immediately check logs
gcloud logging read `
  'resource.type="cloud_run_job" AND resource.labels.job_name="JOB_NAME"' `
  --project=compact-marker-471008-m0 `
  --limit=50 `
  --freshness=2m
```

---

## Preventive Measures

1. **Always validate requirements.txt after editing:**
   ```powershell
   Get-Content requirements.txt
   ```

2. **Use verbose pip in Dockerfiles during development:**
   ```dockerfile
   RUN cat requirements.txt && pip install -v --no-cache-dir -r requirements.txt
   ```

3. **Add comprehensive debug logging:**
   ```python
   print(f"[DEBUG] Starting with config: {config}", flush=True)
   ```

4. **Test locally before deploying:**
   ```powershell
   docker build -t test-image .
   docker run --rm test-image
   ```

5. **Monitor Cloud Scheduler execution:**
   ```powershell
   # Set up log alerts for failed scheduler jobs
   gcloud logging read `
     'resource.type="cloud_scheduler_job" AND severity="ERROR"' `
     --project=compact-marker-471008-m0 `
     --freshness=24h
   ```
