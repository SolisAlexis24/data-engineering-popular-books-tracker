# Configuration Tests
## Popular Books Tracker — MISAMO inc.

Configuration tests verify that the AWS infrastructure is correctly set up before running the pipeline. They do not execute the full pipeline; instead, they validate the state of deployed resources.

> **Objective**: Detect configuration errors *before* they cause production failures.

---

## Strategy

| ID | Test | What it verifies |
|----|------|-----------------|
| CT-01 | S3 bucket accessible and private | Bucket exists, public access blocked, write permitted |
| CT-02 | Lambda correctly configured | Timeout, memory, layer, handler, environment variable |
| CT-03 | Glue jobs configured | Jobs exist, script in S3, correct parameters, IAM role |
| CT-04 | RDS accessible from Glue | PostgreSQL connection, tables exist, FK constraints correct |
| CT-05 | Bedrock model available | Access to Nova Lite model active |
| CT-06 | Step Functions definition correct | State machine exists, correct states, valid ARNs |
| CT-07 | IAM roles have required permissions | Minimum policies for each service |
| CT-08 | EventBridge rule enabled | Rule active, correct cron, target configured |

---

## CT-01: S3 Bucket

```python
# test_s3_config.py
import boto3
import pytest

REGION = "us-east-2"
BUCKET = "<your-bucket>"


def test_bucket_exists():
    s3 = boto3.client("s3", region_name=REGION)
    response = s3.head_bucket(Bucket=BUCKET)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_bucket_blocks_public_access():
    s3 = boto3.client("s3", region_name=REGION)
    config = s3.get_public_access_block(Bucket=BUCKET)["PublicAccessBlockConfiguration"]

    assert config["BlockPublicAcls"] is True
    assert config["BlockPublicPolicy"] is True
    assert config["IgnorePublicAcls"] is True
    assert config["RestrictPublicBuckets"] is True


def test_can_write_to_bronze_prefix():
    s3 = boto3.client("s3", region_name=REGION)
    test_key = "1bronze/test-config-check.txt"
    try:
        s3.put_object(Bucket=BUCKET, Key=test_key, Body=b"config-test")
        s3.delete_object(Bucket=BUCKET, Key=test_key)
    except Exception as e:
        pytest.fail(f"Cannot write to S3 Bronze: {e}")


def test_bronze_silver_prefixes_structure():
    s3 = boto3.client("s3", region_name=REGION)
    for prefix in ["1bronze/", "2silver/"]:
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, MaxKeys=1)
        assert "ResponseMetadata" in response
```

---

## CT-02: Lambda

```python
# test_lambda_config.py
import boto3
import pytest

REGION = "us-east-2"
FUNCTION_NAME = "popular-books-tracker-scraper"


def get_function_config():
    client = boto3.client("lambda", region_name=REGION)
    return client.get_function_configuration(FunctionName=FUNCTION_NAME)


def test_lambda_exists():
    config = get_function_config()
    assert config["FunctionName"] == FUNCTION_NAME


def test_lambda_timeout_is_sufficient():
    config = get_function_config()
    assert config["Timeout"] >= 180, (
        f"Timeout too low: {config['Timeout']}s. Minimum recommended: 180s"
    )


def test_lambda_memory_is_sufficient():
    config = get_function_config()
    assert config["MemorySize"] >= 512, (
        f"Insufficient memory: {config['MemorySize']}MB. Minimum recommended: 512MB"
    )


def test_lambda_runtime_is_python313():
    config = get_function_config()
    assert config["Runtime"] == "python3.13"


def test_lambda_has_layer():
    config = get_function_config()
    layers = config.get("Layers", [])
    assert len(layers) > 0, "Lambda has no layer configured"


def test_lambda_handler_is_correct():
    config = get_function_config()
    assert config["Handler"] == "lamda_function.lambda_handler"


def test_lambda_role_is_configured():
    config = get_function_config()
    role_arn = config.get("Role", "")
    assert "arn:aws:iam" in role_arn
```

---

## CT-03: Glue Jobs

```python
# test_glue_config.py
import boto3
import pytest

REGION = "us-east-2"
BUCKET = "<your-bucket>"
JOBS = {
    "bronze-to-silver": {
        "min_workers": 2,
        "max_timeout": 60,
        "required_args": ["--BUCKET", "--model_id"]
    },
    "silver-to-gold": {
        "min_workers": 2,
        "max_timeout": 30,
        "required_args": []
    }
}


def get_job(name):
    client = boto3.client("glue", region_name=REGION)
    return client.get_job(JobName=name)["Job"]


@pytest.mark.parametrize("job_name", list(JOBS.keys()))
def test_glue_job_exists(job_name):
    job = get_job(job_name)
    assert job["Name"] == job_name


@pytest.mark.parametrize("job_name", list(JOBS.keys()))
def test_glue_job_script_exists_in_s3(job_name):
    job = get_job(job_name)
    script_location = job["Command"]["ScriptLocation"]
    assert script_location.startswith("s3://")

    s3 = boto3.client("s3", region_name=REGION)
    path = script_location.replace("s3://", "").split("/", 1)
    bucket, key = path[0], path[1]
    try:
        s3.head_object(Bucket=bucket, Key=key)
    except Exception:
        pytest.fail(f"Script not found in S3: {script_location}")


@pytest.mark.parametrize("job_name,config", JOBS.items())
def test_glue_job_has_enough_workers(job_name, config):
    job = get_job(job_name)
    workers = job.get("NumberOfWorkers", 0)
    assert workers >= config["min_workers"], (
        f"{job_name}: configured workers ({workers}) < minimum ({config['min_workers']})"
    )


def test_glue_catalog_database_exists():
    client = boto3.client("glue", region_name=REGION)
    response = client.get_database(Name="db_books")
    assert response["Database"]["Name"] == "db_books"
```

---

## CT-04: RDS PostgreSQL

```python
# test_rds_config.py
import psycopg2
import boto3
import pytest

REGION = "us-east-2"
RDS_IDENTIFIER = "popular-books-tracker-db"
RDS_DB = "books_gold"
RDS_USER = "booksadmin"
RDS_PASSWORD = "<password>"

EXPECTED_TABLES = ["metadata_repeticiones", "repeticiones_libros", "repeticiones_generos"]


def get_rds_endpoint():
    client = boto3.client("rds", region_name=REGION)
    instance = client.describe_db_instances(DBInstanceIdentifier=RDS_IDENTIFIER)
    return instance["DBInstances"][0]["Endpoint"]["Address"]


def test_rds_instance_available():
    client = boto3.client("rds", region_name=REGION)
    instance = client.describe_db_instances(DBInstanceIdentifier=RDS_IDENTIFIER)
    status = instance["DBInstances"][0]["DBInstanceStatus"]
    assert status == "available", f"RDS is not available: {status}"


def test_rds_not_publicly_accessible():
    client = boto3.client("rds", region_name=REGION)
    instance = client.describe_db_instances(DBInstanceIdentifier=RDS_IDENTIFIER)
    assert instance["DBInstances"][0]["PubliclyAccessible"] is False


@pytest.mark.parametrize("table", EXPECTED_TABLES)
def test_rds_table_exists(table):
    host = get_rds_endpoint()
    conn = psycopg2.connect(host=host, dbname=RDS_DB, user=RDS_USER, password=RDS_PASSWORD)
    cur = conn.cursor()
    cur.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
        (table,)
    )
    exists = cur.fetchone()[0]
    conn.close()
    assert exists, f"Table '{table}' not found in database {RDS_DB}"


def test_rds_foreign_keys_exist():
    host = get_rds_endpoint()
    conn = psycopg2.connect(host=host, dbname=RDS_DB, user=RDS_USER, password=RDS_PASSWORD)
    cur = conn.cursor()
    cur.execute("""
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name IN ('repeticiones_libros', 'repeticiones_generos');
    """)
    fks = cur.fetchall()
    conn.close()
    assert len(fks) >= 2, f"Expected at least 2 FK constraints, found {len(fks)}"
```

---

## CT-05: Amazon Bedrock

```python
# test_bedrock_config.py
import boto3
import pytest

REGION = "us-east-2"
MODEL_ID = "amazon.nova-lite-v1:0"


def test_bedrock_model_accessible():
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": "Say hello"}]}],
            inferenceConfig={"maxTokens": 10}
        )
        assert response["output"]["message"]["content"][0]["text"]
    except bedrock.exceptions.AccessDeniedException:
        pytest.fail(f"No access to model {MODEL_ID}. Request access in the Bedrock console.")
    except Exception as e:
        pytest.fail(f"Unexpected error invoking Bedrock: {e}")
```

---

## CT-06: Step Functions

```python
# test_stepfunctions_config.py
import boto3

REGION = "us-east-2"
SF_NAME = "popular-books-tracker-pipeline"


def get_state_machine():
    client = boto3.client("stepfunctions", region_name=REGION)
    machines = client.list_state_machines()["stateMachines"]
    match = [m for m in machines if m["name"] == SF_NAME]
    assert len(match) == 1, f"State machine '{SF_NAME}' not found"
    return client.describe_state_machine(stateMachineArn=match[0]["stateMachineArn"])


def test_state_machine_exists():
    sm = get_state_machine()
    assert sm["name"] == SF_NAME


def test_state_machine_is_active():
    sm = get_state_machine()
    assert sm["status"] == "ACTIVE"


def test_state_machine_has_both_states():
    import json
    sm = get_state_machine()
    definition = json.loads(sm["definition"])
    states = definition.get("States", {})
    assert "Scrap books data" in states
    assert "bronze-to-silver" in states
```

---

## CT-07 and CT-08: IAM and EventBridge

```python
# test_iam_eventbridge_config.py
import boto3

REGION = "us-east-2"
RULE_NAME = "popular-books-tracker-weekly-trigger"


def test_eventbridge_rule_enabled():
    client = boto3.client("events", region_name=REGION)
    rules = client.list_rules(NamePrefix=RULE_NAME)["Rules"]
    assert len(rules) == 1, f"Rule '{RULE_NAME}' not found"
    assert rules[0]["State"] == "ENABLED"


def test_eventbridge_rule_has_target():
    client = boto3.client("events", region_name=REGION)
    rules = client.list_rules(NamePrefix=RULE_NAME)["Rules"]
    targets = client.list_targets_by_rule(Rule=rules[0]["Name"])["Targets"]
    assert len(targets) > 0, "EventBridge rule has no configured targets"
    sf_target = [t for t in targets if "stateMachine" in t.get("Arn", "")]
    assert len(sf_target) > 0, "EventBridge target does not point to a Step Function"


def test_eventbridge_cron_expression():
    client = boto3.client("events", region_name=REGION)
    rules = client.list_rules(NamePrefix=RULE_NAME)["Rules"]
    schedule = rules[0].get("ScheduleExpression", "")
    assert "MON" in schedule or "1" in schedule, (
        f"Cron expression does not appear to be weekly: {schedule}"
    )
```

---

## Running Configuration Tests

```bash
# Install dependencies
pip install pytest boto3 psycopg2-binary

# Run all configuration tests
pytest tests/configuration/ -v

# Run only S3 and Lambda checks (fastest)
pytest tests/configuration/test_s3_config.py tests/configuration/test_lambda_config.py -v

# Generate HTML report
pytest tests/configuration/ -v --html=tests/configuration/report.html
```

### Expected output

```
tests/configuration/test_s3_config.py::test_bucket_exists                PASSED
tests/configuration/test_s3_config.py::test_bucket_blocks_public_access  PASSED
tests/configuration/test_s3_config.py::test_can_write_to_bronze_prefix   PASSED
tests/configuration/test_lambda_config.py::test_lambda_exists            PASSED
tests/configuration/test_lambda_config.py::test_lambda_timeout_...       PASSED
...
```

If any test fails, consult the [Deployment Guide](../../deploy/README.md) to resolve the detected configuration issue.
