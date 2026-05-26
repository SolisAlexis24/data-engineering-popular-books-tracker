# Functional Documentation
## Popular Books Tracker — MISAMO inc.

**Version**: 1.0  
**Date**: 2026-05-24  
**Document**: Functional Documentation  
**Organization**: MISAMO inc.

---

## 1. General Description

**Popular Books Tracker** is a data engineering solution built on AWS infrastructure that tracks and analyzes the most popular books and literary genres on a weekly basis. The primary data source is the public [Goodreads Top 50 Most Read Books](https://www.goodreads.com/book/most_read) list, updated every week.

The system fully automates the ETL (Extract, Transform, Load) cycle, applying a medallion architecture (Bronze → Silver → Gold) and enriching data with generative AI before making it available to business analytics tools.

---

## 2. Business Objective

Provide **retail booksellers** with actionable information to:

- **Optimize inventory**: Identify which books and genres have sustained demand over recent weeks.
- **Anticipate trends**: Detect emerging genres and authors before they peak.
- **Reduce inventory risk**: Avoid overstocking titles with declining demand.
- **Accelerate decisions**: Access a weekly executive summary without manual research.

---

## 3. Stakeholders

| Role | Responsibility | System Interaction |
|------|----------------|-------------------|
| Data Analyst | Operates and monitors the pipeline | AWS Console, Glue, Step Functions, CloudWatch |
| Inventory / Purchasing Manager | Consumes trend reports for stock decisions | Tableau / Power BI (Gold layer) |
| AWS Administrator | Maintains and scales infrastructure | Full AWS account access |
| Technology Team (MISAMO inc.) | Develops and maintains source code | Code repository, CI/CD |

---

## 4. Functional Requirements

### FR-01 — Automated Weekly Extraction
- The system must automatically extract the 50 most-read books from Goodreads every week without manual intervention.
- The extraction must capture: title, author, description, genres, average rating, first publication date, and user reviews with their like counts.
- In the event of connection failures, the system must automatically retry up to 3 times with exponential backoff.

### FR-02 — Raw Data Storage (Bronze)
- Extracted data must be stored in JSON format in Amazon S3.
- The storage path must follow the convention: `1bronze/year={YYYY}/week={WW}/{YYYY-MM-DD}.json`.
- Each JSON file must contain the full array of books with their reviews for the processed week.

### FR-03 — AI Enrichment (Silver)
- The system must generate, using a large language model (Amazon Bedrock – Nova Lite), a **Spanish-language review sentiment summary** of no more than 30 words per book.
- The system must generate an **attractive Spanish-language book description** of no more than 50 words, based on genres and the original description.
- Reviews must be weighted by their like count when building the LLM prompt.

### FR-04 — Silver Layer Persistence
- Enriched data must be stored in partitioned Parquet format in S3.
- Two tables must be maintained in the Glue Data Catalog:
  - `book_data`: enriched book metadata (one record per unique book).
  - `book_appearances`: weekly appearance record for each book (id, year, week).
- A book must not be duplicated in `book_data`; it is only recorded the first time it appears.

### FR-05 — Business Metrics Generation (Gold)
- The system must calculate the **Top 10 books** by number of appearances over a sliding window of 5 ISO weeks.
- The system must calculate the **Top 20 genres** by number of distinct books appearing in the same window.
- Results must be persisted in a PostgreSQL database (Amazon RDS) including execution metadata (date, week window).

### FR-06 — Scheduling and Orchestration
- The full pipeline (Bronze → Silver) must run automatically every week (Sunday at 18:00 GMT-6) via Amazon EventBridge.
- The Silver → Gold job must be executable on-demand by the analyst when required.
- AWS Step Functions must orchestrate the execution sequence, guaranteeing the order: Lambda → Glue Bronze-to-Silver.

### FR-07 — Observability and Traceability
- All components must generate logs in Amazon CloudWatch.
- The Step Function must record the result of each state (success/failure).
- Glue jobs must emit `[INFO]`, `[OK]`, and `[ERROR]` messages to facilitate diagnosis.

### FR-08 — Data Visualization
- Gold layer data must be exportable as CSV or directly connectable from BI tools (Tableau, Power BI).
- The system must produce at minimum: most repeated books and most frequent genres.

---

## 5. Non-Functional Requirements

| ID | Category | Description | Metric |
|----|----------|-------------|--------|
| NFR-01 | Availability | The pipeline must complete successfully every week | ≥ 95% of executions successful |
| NFR-02 | Scalability | Support volume increases without architecture changes | Configurable Glue workers |
| NFR-03 | Security | Service-to-service communication via least-privilege IAM roles | No hardcoded credentials in prod |
| NFR-04 | Cost | Maximize serverless service usage to minimize baseline cost | No permanent EC2 servers |
| NFR-05 | Maintainability | Documented and modular code | README per component |
| NFR-06 | Auditability | Record all executions with date, week window, and results | CloudWatch logs + RDS metadata |
| NFR-07 | Privacy | Do not store personal information from Goodreads users | Only review text and likes |

---

## 6. Process Flow

```
┌───────────────────────────────────────────────────────────────┐
│                  AUTOMATED WEEKLY EXECUTION                    │
│                   (Sunday 18:00 GMT-6)                        │
└──────────────────────────┬────────────────────────────────────┘
                           │
                    EventBridge
                           │
                    Step Functions
                    ┌──────┴────────────────────────┐
                    │                               │
              [Step 1]                         [Step 2]
           Lambda Scraper               Glue: bronze-to-silver
           ─────────────                ───────────────────────
           Access Goodreads             Read JSON from S3 Bronze
           Extract 50 books             Invoke Bedrock (LLM)
           Generate JSON                  ├─ Review summary
           Upload to S3 Bronze            └─ Book description
           Return year/week              Write Parquet to Silver
                                         Update Glue Catalog

┌───────────────────────────────────────────────────────────────┐
│                    MANUAL / ON-DEMAND EXECUTION                │
└──────────────────────────┬────────────────────────────────────┘
                           │
                    Glue: silver-to-gold
                    ─────────────────────
                    Read last 5 weeks from Silver
                    Calculate Top 10 books
                    Calculate Top 20 genres
                    Insert into RDS PostgreSQL
                           │
                    BI Tool
                    (Tableau / Power BI)
```

---

## 7. System Inputs and Outputs

### 7.1 Inputs

| Source | Type | Format | Frequency |
|--------|------|--------|-----------|
| Goodreads – `most_read` | External (public web) | HTML | Weekly |
| Step Functions parameters | Internal | JSON (`year`, `week`) | Per execution |
| Glue environment variables | Configuration | String | Per deployment |

### 7.2 Outputs

| Destination | Format | Content | Update Frequency |
|-------------|--------|---------|-----------------|
| S3 Bronze | JSON | Raw data (books + reviews) | Weekly |
| S3 Silver – `book_data` | Parquet | Enriched book metadata | First appearance |
| S3 Silver – `book_appearances` | Parquet | Year-week record per book | Weekly |
| RDS Gold – `repeticiones_libros` | PostgreSQL | Top 10 books for the period | On-demand |
| RDS Gold – `repeticiones_generos` | PostgreSQL | Top 20 genres for the period | On-demand |
| BI Dashboard | Visual | Trend charts | On-demand |

---

## 8. Business Rules

| ID | Rule |
|----|------|
| BR-01 | A book's metadata is stored **only once** in `book_data`; appearances are tracked separately in `book_appearances`. |
| BR-02 | The analysis window for the Gold layer defaults to **5 ISO weeks** (configurable via the `CONTEO_SEMANAS` parameter). |
| BR-03 | The book ranking covers the **top 10** positions; the genre ranking covers the **top 20**. |
| BR-04 | Reviews are weighted by like count when building the LLM context. |
| BR-05 | **No personal information** from Goodreads users who write reviews is stored (only text and likes). |
| BR-06 | AI-generated summaries and descriptions are produced **in Spanish**, regardless of the original language. |
| BR-07 | A scraper failure stops the entire pipeline; Bronze→Silver does not execute without valid Bronze data. |

---

## 9. Use Cases

### UC-01: Automated Weekly Pipeline Execution
**Primary actor**: EventBridge (system)  
**Precondition**: Pipeline configured and active in AWS  
**Main flow**:
1. EventBridge triggers Step Functions every Sunday at 18:00 GMT-6.
2. Step Functions executes the Lambda scraper function.
3. Lambda extracts the 50 books from Goodreads and uploads them to S3 Bronze with a partitioned path.
4. Lambda returns `year` and `week` as output parameters.
5. Step Functions executes the `bronze-to-silver` Glue Job with the received parameters.
6. Glue reads the JSON, invokes Bedrock to enrich each book, and writes Parquet to Silver.

**Alternative flow (Lambda failure)**:
- If Lambda fails, Step Functions retries up to 3 times with exponential backoff.
- After 3 failed attempts, the execution reaches FAILED state and a CloudWatch alert is generated.

---

### UC-02: Gold Metrics Update
**Primary actor**: Data Analyst  
**Precondition**: At least 1 week of Silver data available  
**Main flow**:
1. Analyst manually executes the `silver-to-gold` Glue Job from the AWS console.
2. Glue reads appearances from Silver for the last 5 ISO weeks.
3. Glue calculates Top 10 books and Top 20 genres using Spark SQL queries.
4. Results are inserted into RDS tables with execution metadata.

---

### UC-03: Trend Consultation by Business Team
**Primary actor**: Inventory Manager  
**Precondition**: Gold data available in RDS PostgreSQL  
**Main flow**:
1. Manager connects a BI tool (Tableau / Power BI) to RDS PostgreSQL.
2. Views the Top 10 most repeated books of the period.
3. Views the Top 20 most frequent genres of the period.
4. Exports or downloads the data as CSV for offline analysis.
5. Makes purchasing and inventory decisions based on the trends.

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| Bronze | Raw, untransformed data layer (JSON in S3) |
| Silver | Curated and enriched data layer (Parquet in S3 + Glue Catalog) |
| Gold | Aggregated business metrics layer (PostgreSQL RDS) |
| LLM | Large Language Model (Bedrock Nova Lite) |
| ISO Week | Week of the year per ISO 8601 standard (Monday to Sunday) |
| ETL | Extract, Transform, Load — data pipeline process |
| Medallion Architecture | Data lake design pattern with Bronze, Silver, and Gold layers |
| Scraper | Python script that automatically extracts data from web pages |

---

*Document prepared by MISAMO inc. — Internal use only*
