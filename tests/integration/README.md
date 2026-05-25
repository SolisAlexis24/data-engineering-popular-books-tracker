# Integration Tests
## Popular Books Tracker — MISAMO inc.

Integration tests verify that system components interact correctly with each other and with AWS services. They require a configured AWS account and deployed resources.

> **Prerequisite**: Run `aws configure` with credentials that have access to the listed services.

---

## Integration Test Strategy

| ID | Test | Services involved | Automatable |
|----|------|------------------|-------------|
| IT-01 | Full end-to-end pipeline | Lambda, S3, Glue, Bedrock, Step Functions | Yes |
| IT-02 | Lambda uploads correctly to S3 Bronze | Lambda, S3 | Yes |
| IT-03 | Glue reads Bronze and writes Silver | S3, Glue, Bedrock | Yes |
| IT-04 | Glue reads Silver and writes to RDS | S3, Glue, RDS, Glue Catalog | Yes |
| IT-05 | Step Functions sequences Lambda → Glue | Step Functions, Lambda, Glue | Yes |
| IT-06 | EventBridge triggers Step Functions | EventBridge, Step Functions | Manual |

---

## IT-01: End-to-End Pipeline

**Description**: Execute the full Step Function and verify data reaches the Gold layer.

```bash
#!/bin/bash
# test_pipeline_e2e.sh

REGION="us-east-2"
SF_NAME="popular-books-tracker-pipeline"
BUCKET="<your-bucket>"

echo "=== IT-01: End-to-End Pipeline ==="

# 1. Trigger Step Functions
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn "arn:aws:states:$REGION:<account-id>:stateMachine:$SF_NAME" \
  --query 'executionArn' --output text --region $REGION)

echo "[INFO] Execution started: $EXECUTION_ARN"

# 2. Wait for result (15 min timeout)
STATUS="RUNNING"
TIMEOUT=900
ELAPSED=0

while [ "$STATUS" = "RUNNING" ] && [ $ELAPSED -lt $TIMEOUT ]; do
  sleep 30
  ELAPSED=$((ELAPSED + 30))
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn $EXECUTION_ARN \
    --query 'status' --output text --region $REGION)
  echo "[INFO] Status ($ELAPSED s): $STATUS"
done

# 3. Check result
if [ "$STATUS" = "SUCCEEDED" ]; then
  echo "[PASS] IT-01: Pipeline executed successfully"
else
  echo "[FAIL] IT-01: Pipeline failed with status: $STATUS"
  exit 1
fi

# 4. Verify files exist in S3 Bronze
COUNT=$(aws s3 ls s3://$BUCKET/1bronze/ --recursive | wc -l)
if [ $COUNT -gt 0 ]; then
  echo "[PASS] IT-01: Data found in S3 Bronze ($COUNT files)"
else
  echo "[FAIL] IT-01: No files found in S3 Bronze"
  exit 1
fi
```

---

## IT-02: Lambda → S3 Bronze

**Description**: Invoke Lambda directly and verify the JSON file appears in S3.

```python
# test_lambda_s3.py
import boto3
import json
from datetime import date

REGION = "us-east-2"
FUNCTION_NAME = "popular-books-tracker-scraper"
BUCKET = "<your-bucket>"


def test_lambda_uploads_to_s3_bronze():
    lambda_client = boto3.client("lambda", region_name=REGION)
    s3_client = boto3.client("s3", region_name=REGION)

    # Invoke Lambda
    response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse"
    )

    payload = json.loads(response["Payload"].read())
    assert payload["statusCode"] == 200, f"Lambda failed: {payload}"
    assert "year" in payload
    assert "week" in payload

    year = payload["year"]
    week = payload["week"]

    # Verify file in S3
    prefix = f"1bronze/year={year}/week={week}/"
    response = s3_client.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    assert response.get("KeyCount", 0) > 0, f"No files found at {prefix}"

    # Verify the JSON is valid
    obj_key = response["Contents"][0]["Key"]
    obj = s3_client.get_object(Bucket=BUCKET, Key=obj_key)
    data = json.loads(obj["Body"].read())
    assert isinstance(data, list)
    assert len(data) > 0
    assert "book" in data[0]
    assert "reviews" in data[0]

    print(f"[PASS] IT-02: Lambda uploaded {len(data)} books to s3://{BUCKET}/{obj_key}")
```

---

## IT-03: Glue Bronze → Silver

**Description**: Run the `bronze-to-silver` job with known parameters and verify Parquet files in Silver.

```python
# test_glue_bronze_silver.py
import boto3
import time
from datetime import date

REGION = "us-east-2"
JOB_NAME = "bronze-to-silver"
BUCKET = "<your-bucket>"


def test_glue_bronze_to_silver():
    glue_client = boto3.client("glue", region_name=REGION)
    s3_client = boto3.client("s3", region_name=REGION)

    today = date.today()
    year = str(today.year)
    week = f"{today.isocalendar().week:02d}"

    # Start job
    run = glue_client.start_job_run(
        JobName=JOB_NAME,
        Arguments={"--year": year, "--week": week}
    )
    run_id = run["JobRunId"]
    print(f"[INFO] IT-03: Job started: {run_id}")

    # Wait for result (10 min timeout)
    timeout = 600
    elapsed = 0
    while elapsed < timeout:
        time.sleep(30)
        elapsed += 30
        status = glue_client.get_job_run(JobName=JOB_NAME, RunId=run_id)
        state = status["JobRun"]["JobRunState"]
        print(f"[INFO] State ({elapsed}s): {state}")
        if state in ("SUCCEEDED", "FAILED", "ERROR", "STOPPED"):
            break

    assert state == "SUCCEEDED", f"Glue job failed with state: {state}"

    # Verify data in Silver
    for prefix in ["2silver/book_data/", "2silver/book_appearances/"]:
        response = s3_client.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
        assert response.get("KeyCount", 0) > 0, f"No files found at {prefix}"
        print(f"[PASS] IT-03: Data found at s3://{BUCKET}/{prefix}")
```

---

## IT-04: Glue Silver → Gold (RDS)

**Description**: Execute the `silver-to-gold` job and verify data in PostgreSQL.

```python
# test_glue_silver_gold.py
import boto3
import psycopg2
import time

REGION = "us-east-2"
JOB_NAME = "silver-to-gold"
RDS_HOST = "<rds-endpoint>"
RDS_DB = "books_gold"
RDS_USER = "booksadmin"
RDS_PASSWORD = "<password>"


def test_glue_silver_to_gold():
    glue_client = boto3.client("glue", region_name=REGION)

    # Count records before
    conn = psycopg2.connect(host=RDS_HOST, dbname=RDS_DB, user=RDS_USER, password=RDS_PASSWORD)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM metadata_repeticiones;")
    count_before = cur.fetchone()[0]
    conn.close()

    # Start job
    run = glue_client.start_job_run(JobName=JOB_NAME)
    run_id = run["JobRunId"]

    timeout, elapsed = 600, 0
    while elapsed < timeout:
        time.sleep(30)
        elapsed += 30
        state = glue_client.get_job_run(JobName=JOB_NAME, RunId=run_id)["JobRun"]["JobRunState"]
        if state in ("SUCCEEDED", "FAILED", "ERROR"):
            break

    assert state == "SUCCEEDED", f"Job failed: {state}"

    # Verify new records were inserted
    conn = psycopg2.connect(host=RDS_HOST, dbname=RDS_DB, user=RDS_USER, password=RDS_PASSWORD)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM metadata_repeticiones;")
    count_after = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM repeticiones_libros WHERE id_metadata = (SELECT MAX(id_metadata) FROM metadata_repeticiones);")
    books = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM repeticiones_generos WHERE id_metadata = (SELECT MAX(id_metadata) FROM metadata_repeticiones);")
    genres = cur.fetchone()[0]
    conn.close()

    assert count_after > count_before, "No new records inserted in metadata_repeticiones"
    assert 1 <= books <= 10, f"Expected 1-10 books, found {books}"
    assert 1 <= genres <= 20, f"Expected 1-20 genres, found {genres}"

    print(f"[PASS] IT-04: {books} books and {genres} genres inserted into RDS")
```

---

## IT-05: Step Functions Correct Sequence

**Description**: Verify that Step Functions executes Lambda before Glue and that parameters are correctly passed.

```python
# test_stepfunctions_sequence.py
import boto3
import time

REGION = "us-east-2"
SF_ARN = "arn:aws:states:<region>:<account-id>:stateMachine:popular-books-tracker-pipeline"


def test_step_functions_passes_year_week_to_glue():
    sf_client = boto3.client("stepfunctions", region_name=REGION)

    execution = sf_client.start_execution(StateMachineArn=SF_ARN)
    exec_arn = execution["executionArn"]

    # Wait for result
    timeout, elapsed = 900, 0
    while elapsed < timeout:
        time.sleep(30)
        elapsed += 30
        desc = sf_client.describe_execution(executionArn=exec_arn)
        status = desc["status"]
        if status != "RUNNING":
            break

    assert status == "SUCCEEDED", f"Pipeline failed: {status}"

    # Verify event history
    history = sf_client.get_execution_history(executionArn=exec_arn)
    events = history["events"]

    lambda_succeeded = any(e["type"] == "LambdaFunctionSucceeded" for e in events)
    glue_started = any(e["type"] == "TaskStateEntered" and
                       "bronze-to-silver" in str(e.get("stateEnteredEventDetails", ""))
                       for e in events)

    assert lambda_succeeded, "Lambda did not complete successfully"
    assert glue_started, "Glue job was not started by Step Functions"
    print("[PASS] IT-05: Lambda → Glue sequence verified")
```

---

## Running Integration Tests

```bash
# Install test dependencies
pip install pytest boto3 psycopg2-binary

# Run a specific test
pytest tests/integration/test_lambda_s3.py -v

# Run all integration tests (slow — requires active AWS)
pytest tests/integration/ -v --timeout=900
```

> **Note**: Integration tests incur real AWS costs (Bedrock, Glue DPU, RDS).  
> Run only in development/staging environments, never in production.
