# Technical Documentation
## Popular Books Tracker — MISAMO inc.

**Version**: 1.0  
**Date**: 2026-05-24  
**Document**: Technical Documentation  
**Organization**: MISAMO inc.

---

## 1. Technical Summary

The system is a serverless data pipeline deployed on AWS. It extracts Goodreads data via web scraping (Python), transforms it with PySpark in AWS Glue while enriching with an LLM (Amazon Bedrock), and persists aggregated metrics in Amazon RDS PostgreSQL. Orchestration is handled by AWS Step Functions, triggered weekly by Amazon EventBridge.

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Extraction | Python + BeautifulSoup4 + requests | Python 3.13 | Goodreads web scraping |
| Serverless compute | AWS Lambda | Python 3.13 runtime | Scraper execution |
| ETL | AWS Glue (PySpark) | Glue 4.0 / Spark 3.x | Data transformation and enrichment |
| Data Lake storage | Amazon S3 | — | Bronze and Silver layers |
| Generative AI | Amazon Bedrock – Nova Lite | `amazon.nova-lite-v1:0` | Text generation |
| Metadata catalog | AWS Glue Data Catalog | — | Silver table schemas |
| Relational database | Amazon RDS – PostgreSQL | PostgreSQL 13+ | Gold layer (metrics) |
| Orchestration | AWS Step Functions (Standard) | JSONata | Pipeline sequencing |
| Scheduling | Amazon EventBridge | Cron schedule | Weekly trigger |
| Dependency management | uv | 0.x | Lambda layer packaging |
| Visualization | Tableau / Power BI | — | Trend dashboards |

---

## 3. System Components

### 3.1 Scraper (`src/scraper/scraper.py`)

**Class**: `most_read_scraper`

| Attribute / Method | Type | Description |
|-------------------|------|-------------|
| `most_read_url_list` | `list[str]` | Book URLs retrieved from the most-read page |
| `max_conn_retries` | `int` | Maximum HTTP connection retries (default: 3) |
| `books_data` | `list[dict]` | Accumulated scraping results |
| `scrape()` | public method | Runs the full process: retrieves list and scrapes each book |
| `_get_books_list()` | private method | Retrieves URLs from the `most_read` page |
| `_scrape_book(URL)` | private method | Extracts metadata and reviews for a single book |
| `_get_book_data(soup, id)` | private method | Parses the book page HTML |
| `_get_reviews_data(soup)` | private method | Extracts reviews and like counts |
| `_get_response(session, url)` | private method | Performs HTTP request with retry logic |
| `_format_likes(likes_str)` | private method | Converts likes string (e.g. "1.2k") to integer |

**`books_data[i]` object structure**:
```json
{
  "book": {
    "id": 12345,
    "title": "Book Title",
    "author": "Author Name",
    "description": "Original description...",
    "genres": ["Fiction", "Drama"],
    "rating": 4.23,
    "date": "January 1 2020"
  },
  "reviews": [
    {"text": "Review text...", "likes": 142},
    {"text": "Another review...", "likes": 87}
  ]
}
```

**HTTP configuration**:
- Headers include a real browser `User-Agent` to prevent connection blocking.
- `timeout`: 10 seconds per request.
- `cooldown_s`: 10 seconds between retries.
- Book URL validation regex: `r"https://www.goodreads.com/book/show/(\d+)[\w.\-]+$"`

---

### 3.2 Lambda Handler (`src/scraper/lamda_function.py`)

**Function**: `lambda_handler(event, context)`

**Execution flow**:
1. Instantiates `most_read_scraper` and calls `scrape()`.
2. Serializes `books_data` to JSON and writes to `/tmp/{YYYY-MM-DD}.json`.
3. Uploads the file to S3 at path `1bronze/year={YYYY}/week={WW}/{YYYY-MM-DD}.json`.
4. Deletes the temporary file from `/tmp`.
5. Returns `statusCode`, `body`, `year`, and `week` for Step Functions to pass as arguments to the Glue job.

**Environment variables / configuration**:

| Variable | Location | Description |
|----------|----------|-------------|
| `BUCKET` | Hardcoded (line 13) | Target S3 bucket name |

> **Note**: In production, `BUCKET` should be configured as a Lambda environment variable or retrieved from AWS Systems Manager Parameter Store.

**IAM permissions required by the function**:
- `s3:PutObject` on `arn:aws:s3:::{BUCKET}/1bronze/*`
- `logs:CreateLogStream`, `logs:PutLogEvents`

**Minimum recommended configuration**:
- Timeout: 3 minutes (180 seconds)
- Memory: 512 MB
- Runtime: Python 3.13

**Lambda Layer dependencies**:

| Package | Version |
|---------|---------|
| beautifulsoup4 | ≥ 4.14.3 |
| requests | ≥ 2.33.0 |
| tqdm | ≥ 4.67.3 |
| boto3 | ≥ 1.42.78 |

---

### 3.3 Glue Job: Bronze → Silver (`src/etl-jobs/bronze-to-silver.py`)

**Type**: PySpark (AWS Glue 4.0)

**Input parameters**:

| Parameter | Type | Source | Description |
|-----------|------|--------|-------------|
| `--JOB_NAME` | string | Glue (automatic) | Job name |
| `--year` | int | Step Functions | ISO year of the scrape |
| `--week` | int | Step Functions | ISO week number of the scrape |
| `--BUCKET` | string | Job parameters | S3 bucket base path (e.g. `s3://my-bucket`) |
| `--model_id` | string | Job parameters | Bedrock model ID (e.g. `amazon.nova-lite-v1:0`) |

**Bedrock UDFs**:

| UDF | Input | Output | Prompt |
|-----|-------|--------|--------|
| `sumarize_reviews_udf` | String of reviews weighted by likes | Spanish sentiment summary ≤ 30 words | Sentiment analysis |
| `generate_description_udf` | Genres + original description | Attractive Spanish description ≤ 50 words | Commercial description |

**Bedrock configuration**:
- Region: `us-east-2`
- `maxTokens`: 512
- `temperature`: 0.5
- `topP`: 0.9

**Output tables**:

| S3 Table | Path | Write mode | Description |
|----------|------|------------|-------------|
| `book_data` | `{BUCKET}/2silver/book_data/` | append | Enriched metadata (new books only) |
| `book_appearances` | `{BUCKET}/2silver/book_appearances/` | append | Weekly appearance record |

**`book_data` schema**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | long | Unique book ID on Goodreads |
| `title` | string | Book title |
| `author` | string | Author name |
| `rating` | double | Average rating |
| `pub_date` | string | First publication date |
| `ai_reviews_summary` | string | Review summary generated by Bedrock |
| `ai_description` | string | Commercial description generated by Bedrock |
| `genres` | array\<string\> | List of genres |

**`book_appearances` schema**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | long | Book ID |
| `year` | int | ISO year of the week |
| `week` | int | ISO week number |

**Deduplication logic**:
Before enriching with Bedrock, the job checks whether a book already exists in `book_data` using a `left_anti join` on `id`. Only new books are enriched with AI, avoiding unnecessary costs.

**Required IAM permissions**:
- `s3:GetObject`, `s3:ListBucket` on `{BUCKET}/1bronze/*`
- `s3:PutObject` on `{BUCKET}/2silver/*`
- `bedrock:InvokeModel` on `arn:aws:bedrock:us-east-2::foundation-model/*`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Recommended worker configuration**:
- Worker type: `G.1X` (4 GB RAM, 1 DPU)
- Number of workers: 2–5
- Timeout: 60 minutes

---

### 3.4 Glue Job: Silver → Gold (`src/etl-jobs/silver-to-gold.py`)

**Type**: PySpark (AWS Glue 4.0)

**Input parameters**:

| Parameter | Type | Source | Description |
|-----------|------|--------|-------------|
| `--JOB_NAME` | string | Glue (automatic) | Job name |
| RDS credentials | Hardcoded (lines 27–31) | Source code | Host, port, database, user, password |

> **Security warning**: In production, RDS credentials must be stored in **AWS Secrets Manager** and retrieved with `boto3.client('secretsmanager')`.

**Configuration constant**:
- `CONTEO_SEMANAS = 5`: ISO week sliding window for aggregation (adjustable).

**Data sources (Glue Catalog)**:

| Catalog table | Database | Description |
|---------------|----------|-------------|
| `book_appearances` | `db_books` | Weekly appearances |
| `book_data` | `db_books` | Book metadata |

**SQL queries (Spark)**:

1. **Temporary view** `appearances_filtradas`: Filters appearances in the range `[current_week - 5, current_week]` of the current year.
2. **Top 10 books**: Groups by `id`, counts appearances, takes the top 10, joins with `book_data` to get the title.
3. **Top 20 genres**: Explodes the `genres` array with `LATERAL VIEW EXPLODE`, counts distinct books per genre, takes the top 20.

**RDS destination tables**:

| Table | Description |
|-------|-------------|
| `metadata_repeticiones` | One row per execution: date and week window |
| `repeticiones_libros` | Top 10 books with FK to metadata |
| `repeticiones_generos` | Top 20 genres with FK to metadata |

**RDS connection**:
- Library: `psycopg2`
- The job must run within the same VPC as RDS (Glue network configuration)
- Port: 5432 (PostgreSQL)
- Explicit transaction with rollback on error

**Required IAM permissions**:
- `glue:GetDatabase`, `glue:GetTable` for `db_books`
- `s3:GetObject`, `s3:ListBucket` on Silver table S3 paths
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Recommended worker configuration**:
- Worker type: `G.1X`
- Number of workers: 2
- Timeout: 30 minutes

---

### 3.5 Gold Database Schema (`src/etl-jobs/tables.sql`)

```sql
-- Execution metadata
CREATE TABLE metadata_repeticiones (
    id_metadata    SERIAL PRIMARY KEY,
    fecha_registro DATE    NOT NULL,
    conteo_semanas INTEGER NOT NULL
);

-- Top books per execution
CREATE TABLE repeticiones_libros (
    id           SERIAL PRIMARY KEY,
    id_metadata  INTEGER      NOT NULL REFERENCES metadata_repeticiones(id_metadata) ON DELETE CASCADE,
    titulo       VARCHAR(255) NOT NULL,
    repeticiones INTEGER      NOT NULL
);

-- Top genres per execution
CREATE TABLE repeticiones_generos (
    id           SERIAL PRIMARY KEY,
    id_metadata  INTEGER      NOT NULL REFERENCES metadata_repeticiones(id_metadata) ON DELETE CASCADE,
    genero       VARCHAR(150) NOT NULL,
    repeticiones INTEGER      NOT NULL
);
```

**Relationships**:
- `repeticiones_libros.id_metadata` → `metadata_repeticiones.id_metadata` (ON DELETE CASCADE)
- `repeticiones_generos.id_metadata` → `metadata_repeticiones.id_metadata` (ON DELETE CASCADE)

---

### 3.6 Orchestration: Step Functions

**State machine type**: Standard (JSONata)  
**Name**: `books-tracking-pipeline`

**Flow definition**:
```
Scrap books data (Lambda)
    ├─ Retry: up to 3 attempts, x2 backoff, FULL jitter
    └─ Success → passes {year, week} to next state

bronze-to-silver (Glue startJobRun.sync)
    ├─ Receives --year and --week as arguments
    └─ Success → END
```

**States**:

| State | Type | Resource | Description |
|-------|------|---------|-------------|
| `Scrap books data` | Task | `arn:aws:states:::lambda:invoke` | Invokes Lambda scraper |
| `bronze-to-silver` | Task | `arn:aws:states:::glue:startJobRun.sync` | Executes Glue job synchronously |

**Retry policy (Lambda)**:

| Parameter | Value |
|-----------|-------|
| ErrorEquals | `Lambda.ServiceException`, `Lambda.AWSLambdaException`, `Lambda.SdkClientException`, `Lambda.TooManyRequestsException`, `RuntimeError` |
| IntervalSeconds | 30 |
| MaxAttempts | 3 |
| BackoffRate | 2 |
| JitterStrategy | FULL |

---

### 3.7 Scheduling: EventBridge

**Rule**: `weekly-books-scraper`  
**Cron expression**: `cron(0 0 ? * MON *)` — Every Monday at 00:00 UTC (Sunday 18:00 GMT-6)  
**Target**: Step Functions `books-tracking-pipeline`

---

## 4. S3 Data Structure

```
s3://{BUCKET}/
├── 1bronze/
│   └── year={YYYY}/
│       └── week={WW}/
│           └── {YYYY-MM-DD}.json          ← Raw scraper data
└── 2silver/
    ├── book_data/
    │   └── part-*.parquet                 ← Enriched metadata (append)
    └── book_appearances/
        └── part-*.parquet                 ← Weekly appearances (append)
```

---

## 5. Required IAM Roles

| Role | Used by | Main permissions |
|------|---------|----------------|
| `LambdaScraperRole` | AWS Lambda | S3 PutObject (bronze), CloudWatch Logs |
| `GlueETLRole` | AWS Glue jobs | S3 Read/Write (bronze, silver), Bedrock InvokeModel, Glue Catalog, CloudWatch Logs, VPC (for RDS) |
| `StepFunctionsRole` | Step Functions | Lambda InvokeFunction, Glue StartJobRun, CloudWatch Logs |
| `EventBridgeRole` | EventBridge | Step Functions StartExecution |

---

## 6. Network Configuration

The `silver-to-gold` Glue Job requires connectivity to RDS PostgreSQL:

- Glue job configured with the same VPC and subnet as RDS.
- Glue security group must have an outbound rule to port 5432 on the RDS security group.
- RDS security group must have an inbound rule from the Glue security group on port 5432.
- VPC endpoints for S3 and Glue are recommended to avoid internet egress traffic.

---

## 7. Security Considerations

| Risk | Current mitigation | Recommended improvement |
|------|--------------------|------------------------|
| Hardcoded RDS credentials | Variables in source code | Use AWS Secrets Manager |
| Public S3 bucket | Private bucket by default | Explicit public-denial bucket policy |
| Bedrock access | Least-privilege IAM role | Restrict to specific model ARN |
| CloudWatch log access | Enabled on all jobs | Enable log encryption with KMS |
| S3 encryption at rest | No explicit configuration | Enable SSE-S3 or SSE-KMS on bucket |

---

## 8. Monitoring and Alerting

| Component | Where to monitor | What to check |
|-----------|-----------------|---------------|
| Lambda Scraper | CloudWatch Logs → `/aws/lambda/{name}` | Connection errors, timeouts, S3 upload |
| Glue bronze-to-silver | CloudWatch Logs → `/aws-glue/jobs/output` | Bedrock errors, AnalysisException |
| Glue silver-to-gold | CloudWatch Logs → `/aws-glue/jobs/output` | RDS connection errors, rollbacks |
| Step Functions | Step Functions console → Execution history | Status of each step, inputs/outputs |
| EventBridge | CloudWatch → Rules → Invocations | Whether the rule fired correctly |

---

## 9. Service Dependency Map

```
EventBridge
    └── Step Functions
            ├── Lambda (requires layer with dependencies)
            │       └── S3 (Bronze write)
            └── Glue bronze-to-silver
                    ├── S3 (Bronze read, Silver write)
                    ├── Bedrock Nova Lite
                    └── Glue Data Catalog (schema writes)

Glue silver-to-gold (manual)
    ├── Glue Data Catalog (read book_data, book_appearances)
    ├── S3 (Silver read)
    └── RDS PostgreSQL
```

---

*Document prepared by MISAMO inc. — Internal use only*
