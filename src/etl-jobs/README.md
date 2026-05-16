# ETL jobs and database definition

This directory holds the ETL jobs used to move the data between layers in the medallion architecture.

## Table of Contents

- [Bronze to Silver](#bronze-to-silver)
- [Silver to Gold](#silver-to-gold)
- [Gold Layer Database Definition](#gold-layer-database-definition)
- [Setup and Deployment](#setup-and-deployment)

## Bronze to silver

This AWS Glue ETL job enriches raw book data with AI-generated summaries and descriptions, then writes curated datasets to a Silver layer in a data lake. It processes weekly JSON dumps, invokes Amazon Bedrock for generative text, and updates two target tables: one with enriched book metadata and another tracking weekly book appearances.

### Key components

- Amazon Bedrock Integration: Two Python UDFs call the Bedrock converse API using a foundation model.

    - sumarize_reviews: Given a string of reviews weighted by "likes", it asks the model to output a Spanish sentiment summary in ≤30 words.
    - generate_description: Given genres and a raw description, it asks for an attractive Spanish description in ≤50 words.

- Input/Output:

    - Source: Multiline JSON files stored at ```{BUCKET}/1bronze/year={year}/week={week}/```.
    - Targets (Parquet, append mode):
        - ```{BUCKET}/2silver/book_data/``` – enriched book master data.
        - ```{BUCKET}/2silver/book_appearances/``` – book-year-week appearance records.

### Required IAM Permissions

**S3**
- **Read** from source bucket:  
  `s3:GetObject`, `s3:ListBucket` on `arn:aws:s3:::<BUCKET>` and `.../*`
- **Write** to Silver output prefixes:  
  `s3:PutObject` (and optionally `s3:DeleteObject` for temp cleanup) on  
  `arn:aws:s3:::<BUCKET>/2silver/*`

**Amazon Bedrock**
- `bedrock:InvokeModel` on the foundation model ARN (e.g., `arn:aws:bedrock:us-east-2::foundation-model/*`)

**CloudWatch Logs**
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` on  
  `arn:aws:logs:*:*:/aws-glue/jobs/*`

**AWS Glue (only if job bookmarks are used)**
- `glue:GetJob`, `glue:ResetJobBookmark`, `glue:UpdateJobBookmark` on  
  `arn:aws:glue:*:*:job/<JOB_NAME>`


**Warning:** `model_id` and `BUCKET` variables are left empty and they must be configured at runtime.

## Gold Layer Database Definition

For storing gold layer information, an RDS PostgreSQL database was created and populated with the tables from `tables.sql` script. This script defines 3 tables:
- `metadata_repeticiones` - Stores metadata about each execution (date, week count)
- `repeticiones_libros` - Stores top books by appearances
- `repeticiones_generos` - Stores top genres by distinct book count

## Silver to Gold
This Glue job aggregates book appearances from the Silver layer over the last 5 weeks, computes the top‑10 most repeated books and top‑20 most popular genres, and inserts the results into an RDS PostgreSQL database for reporting.

### Key Components

- **Source** (Glue Catalog tables):  
  - `db_books.book_appearances` – records of which book appeared in which week/year.  
  - `db_books.book_data` – enriched book metadata (title, genres, etc.).
- **Processing window** – last `CONTEO_SEMANAS` (5) full ISO weeks ending with the current week.
- **Aggregations**:  
  - **Top 10 books** by number of appearances.  
  - **Top 20 genres** by number of distinct books appearing in the period.
- **Target**: PostgreSQL RDS – three tables:  
  - `metadata_repeticiones` – run metadata (date, week count).  
  - `repeticiones_libros` – top books results (FK to metadata).  
  - `repeticiones_generos` – top genres results (FK to metadata).

## Required IAM Permissions

**AWS Glue Catalog**  
- `glue:GetDatabase` on `db_books`  
- `glue:GetTable` on `book_appearances`, `book_data`

**S3** (for Glue temporary storage and reading Catalog tables)  
- The underlying S3 paths of both Catalog tables must be accessible:  
  `s3:GetObject`, `s3:ListBucket` on those prefixes.  
- Glue temporary bucket: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`

**CloudWatch Logs**  
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` on `/aws-glue/jobs/*`

**AWS Glue Service** (if bookmarks are enabled)  
- `glue:GetJob`, `glue:ResetJobBookmark`, `glue:UpdateJobBookmark` on the job ARN

**RDS**  
- No IAM permissions needed; connectivity is handled via VPC & security groups.  
  *Recommendation*: store credentials in AWS Secrets Manager and add `secretsmanager:GetSecretValue`.

### Observations / Warnings
- The job relies on `date.today()`; schedule it to run weekly after the Silver job.
- `LATERAL VIEW EXPLODE` expects `genres` to be an array of strings.
- If the selected weeks contain no appearances, the job writes nothing and exits successfully, leaving the RDS tables unchanged.
- `MAX(title)` deduplicates possible duplicates from the Silver layer’s append‑only writes.

---

## Setup and Deployment

### Prerequisites

- AWS Account with Glue, S3, Bedrock, and RDS services enabled
- S3 bucket for data lake storage
- RDS PostgreSQL instance (for Gold layer)
- Python 3.10+ for local testing (optional)

### 1. Create RDS PostgreSQL Database

1. **Launch RDS Instance** (via AWS Console)
   - Go to RDS → Create database
   - Engine: PostgreSQL (version 13+)
   - Template: Free tier or Production (depending on your needs)
   - DB instance identifier: `books-tracking-db`
   - Master username/password: Save credentials securely
   - VPC settings: Note the VPC, subnet, and security group for Glue access

2. **Connect to RDS and Create Schema**
   ```bash
   psql -h <RDS_ENDPOINT> -U <MASTER_USERNAME> -d postgres
   
   # Create database
   CREATE DATABASE books_gold;
   \c books_gold
   
   # Run schema creation
   \i tables.sql
   ```

### 2. Setup Glue Data Catalog (for Silver Layer)

#### Option A: Using AWS Glue Crawler (Recommended)

1. **Navigate to AWS Glue Console** → Crawlers → Create crawler
2. **Name**: `silver-layer-crawler`
3. **Data source**: 
   - S3 path: `s3://your-bucket/2silver/`
   - Include paths: `book_data/`, `book_appearances/`
4. **IAM role**: Create or select role with S3 read permissions
5. **Target database**: Create database `db_books`
6. **Schedule**: On demand (run after first Silver job execution)
7. **Run crawler** to auto-detect schema

#### Option B: Manual Table Creation

```bash
aws glue create-database --database-input Name=db_books

# Create book_data table
aws glue create-table \
  --database-name db_books \
  --table-input file://book_data_schema.json

# Create book_appearances table  
aws glue create-table \
  --database-name db_books \
  --table-input file://book_appearances_schema.json
```

### 3. Configure Bronze → Silver Glue Job

1. **Navigate to AWS Glue Console** → ETL jobs → Visual with a source and target
   - Or choose **Script editor** for direct code upload

2. **Job Details**:
   - **Name**: `bronze-to-silver`
   - **IAM Role**: Create/select role with:
     - S3 read/write permissions on your bucket
     - Bedrock `InvokeModel` permission for `amazon.nova-lite-v1:0`
     - CloudWatch Logs permissions
   - **Type**: Spark
   - **Glue version**: 4.0
   - **Language**: Python 3

3. **Script Upload**:
   - Upload `bronze-to-silver.py` to S3
   - Set **Script path** to the S3 location

4. **Job Parameters** (under Advanced properties → Job parameters):
   - `--BUCKET` = `s3://your-bucket-name`
   - `--model_id` = `amazon.nova-lite-v1:0`

5. **Worker Configuration**:
   - Worker type: **G.1X** (4 GB memory, 1 DPU) - suitable for moderate data
   - Number of workers: **2-5** (adjust based on data volume)
   - Timeout: **60 minutes**

6. **Save** the job

### 4. Configure Silver → Gold Glue Job

1. **Navigate to AWS Glue Console** → ETL jobs → Script editor

2. **Job Details**:
   - **Name**: `silver-to-gold`
   - **IAM Role**: Same as Bronze→Silver job, plus:
     - Glue Catalog `GetDatabase`, `GetTable` permissions
   - **VPC Configuration**: 
     - Enable **Use a VPC**
     - Select same VPC/subnet as RDS
     - Security group: Allow outbound to RDS on port 5432
   - **Connections**: Create Glue connection to RDS (optional but recommended)

3. **Script Upload**:
   - Upload `silver-to-gold.py`
   - **Update credentials in script** (lines 27-31):
     ```python
     RDS_HOST     = "your-rds-endpoint.rds.amazonaws.com"
     RDS_PORT     = 5432
     RDS_DB       = "books_gold"
     RDS_USER     = "your_username"
     RDS_PASSWORD = "your_password"
     ```
   
   **Security Note**: For production, store credentials in AWS Secrets Manager and retrieve them using `boto3.client(‘secretsmanager’)`.

4. **Worker Configuration**:
   - Worker type: **G.1X**
   - Number of workers: **2**
   - Timeout: **30 minutes**

5. **Save** the job

### 5. Test Individual Jobs

Before orchestrating with Step Functions, test each job manually:

```bash
# Test Bronze → Silver
aws glue start-job-run \
  --job-name bronze-to-silver \
  --arguments ‘{"--year":"2026","--week":"20"}’

# Monitor job status
aws glue get-job-run --job-name bronze-to-silver --run-id <RUN_ID>

# Test Silver → Gold
aws glue start-job-run --job-name silver-to-gold

# Verify data in RDS
psql -h <RDS_ENDPOINT> -U <USER> -d books_gold -c "SELECT * FROM metadata_repeticiones;"
```

### 6. Grant Bedrock Model Access

If you encounter Bedrock permission errors:

1. Go to **Amazon Bedrock Console** → Model access
2. **Request access** for **Amazon Nova Lite** model
3. Wait for approval (usually instant for Nova models)
4. Verify IAM role has `bedrock:InvokeModel` permission

### Security Best Practices

- Store RDS credentials in **AWS Secrets Manager**
- Enable **S3 bucket encryption** (SSE-S3 or SSE-KMS)
- Use **VPC endpoints** for S3 and Glue to avoid internet egress charges
- Restrict **security groups** to allow only necessary traffic (Glue ↔ RDS)
- Enable **CloudWatch Logs** for job monitoring and debugging

### Troubleshooting

**Issue**: Glue job can’t connect to RDS  
**Solution**: Verify VPC/subnet/security group settings allow Glue to reach RDS on port 5432

**Issue**: Bedrock `AccessDeniedException`  
**Solution**: Check IAM role has `bedrock:InvokeModel` and model access is enabled in Bedrock console

**Issue**: `AnalysisException` on Silver layer read  
**Solution**: Run Glue Crawler to refresh table schema after first Bronze→Silver job execution

**Issue**: Parquet files not being created  
**Solution**: Check S3 bucket permissions and ensure `BUCKET` variable is correctly set
