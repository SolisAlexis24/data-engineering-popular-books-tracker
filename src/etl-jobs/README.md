# ETL jobs and database definition
This directory holds the ETL jobs used to move the data between layers

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


**Warning:** ```model_id``` and ```BUCKET``` variables are left empty and they must be configured at runtime.

## Gold layer database definition
For storing gold layer information, an RDS database was created and populated with the tables from ```tables.sql``` script. This script defines 3 tables, one for storing metadata about the execution, one for storing appearances for books and another for genres.

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
