# Statement of Work (SOW)
## Popular Books Tracker — MISAMO inc.

**Version**: 1.0  
**Date**: 2026-05-24  
**Document**: Statement of Work  
**Organization**: MISAMO inc.  
**Project**: Data Lake Implementation for Tracking Popular Books and Genres

---

## 1. Introduction and Purpose

This document defines the scope, deliverables, acceptance criteria, and working terms for the **Popular Books Tracker** project. Its purpose is to formalize the agreement between the technology team (MISAMO inc.) and the business stakeholders regarding what will be built, what is out of scope, and how success will be measured.

---

## 2. Background

Retail booksellers face the challenge of deciding which books to purchase for inventory without objective, up-to-date information on current trends. Today, buyers rely on publisher catalogs (updated quarterly), buyer intuition, or social media trends that do not accurately reflect actual reading behavior.

Goodreads publishes a weekly list of the 50 most-read books by its community of millions of users. This information is publicly available and not currently being systematically exploited. This project automates its capture, enrichment, and presentation in an actionable format for the purchasing team.

---

## 3. Project Scope

### 3.1 In Scope

| # | Deliverable |
|---|-------------|
| 1 | Automated AWS ETL pipeline: weekly Goodreads extraction (Lambda) |
| 2 | Raw data storage in S3 (Bronze layer) partitioned by year/week |
| 3 | Data enrichment with Amazon Bedrock: review summaries and Spanish descriptions |
| 4 | Curated data storage in S3 Parquet (Silver layer) + Glue Data Catalog |
| 5 | Calculation of Top 10 books and Top 20 genres over a 5-week window (Gold layer) |
| 6 | Persistence of Gold metrics in Amazon RDS PostgreSQL |
| 7 | Full orchestration with AWS Step Functions + weekly scheduling with EventBridge |
| 8 | System documentation: functional, technical, architecture, deployment |
| 9 | Commented source code and unit tests for the scraping module |
| 10 | Infrastructure as Code template (CloudFormation) |

### 3.2 Out of Scope

| # | Exclusion | Justification |
|---|-----------|---------------|
| 1 | BI dashboard development (Tableau / Power BI) | Requires licenses and specialized profiles; handled by the business team |
| 2 | Integration with the bookstore's ERP or POS systems | Outside the current pilot scope |
| 3 | User-facing mobile or web application | Consumption occurs through existing BI tools |
| 4 | Scraping additional sources (Amazon, NYT Best Sellers) | Possible future extension; not in current scope |
| 5 | Historical data retroactive to before go-live | The system begins accumulating data from the first execution |
| 6 | Automated email or Slack alerts | Manual monitoring in CloudWatch; possible future improvement |

---

## 4. Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| **D-01** Source code | Git repository with Lambda, Glue jobs, and SQL code | Reviewed code, no exposed credentials, README per component |
| **D-02** Deployed infrastructure | All AWS services configured and functional | Pipeline runs end-to-end without errors |
| **D-03** Bronze data | At least 2 weeks of JSON data in S3 | Files accessible with correct structure |
| **D-04** Silver data | Parquet tables in S3 with updated Glue Catalog | Queries from Athena/Glue return correct results |
| **D-05** Gold data | Records in RDS with Top 10 and Top 20 | SQL query returns data consistent with Silver data |
| **D-06** Documentation | Functional, technical, architecture, SOW, RFP docs | Complete documents reviewed by stakeholders |
| **D-07** Unit tests | Tests for the scraper module | Coverage ≥ 80% of `scraper.py` module |
| **D-08** CloudFormation | IaC template to replicate the infrastructure | Template deploys in a new AWS account without errors |
| **D-09** Deployment guide | Step-by-step instructions to replicate the project | A new team can deploy by following the guide |

---

## 5. Technical Out of Scope

- No personally identifiable information (PII) from Goodreads users is stored or processed.
- No paid Goodreads APIs are used; only publicly accessible data.
- The system does not modify data in any external source.

---

## 6. Schedule

| Phase | Activities | Estimated Duration |
|-------|------------|-------------------|
| **Phase 1** — Design | Architecture definition, AWS service selection, schema design | 1 week |
| **Phase 2** — Development | Lambda scraper, Glue jobs, Step Functions implementation | 2 weeks |
| **Phase 3** — Integration | VPC, IAM roles, RDS, EventBridge configuration | 1 week |
| **Phase 4** — Testing | Unit tests, end-to-end pipeline test, Gold data validation | 1 week |
| **Phase 5** — Documentation | Functional, technical, architecture, SOW, RFP documents | 1 week |
| **Phase 6** — Delivery | Final review, knowledge transfer, go-live | 3 days |

**Total estimated duration**: 6–7 weeks

---

## 7. Assumptions

1. An active AWS account is available with access to: Lambda, S3, Glue, Bedrock, RDS, Step Functions, EventBridge.
2. The Amazon Nova Lite model is available in region `us-east-2` and access has been requested in the Bedrock console.
3. Goodreads maintains the current HTML structure of its `most_read` page; interface changes may require scraper updates.
4. The business team holds a Tableau or Power BI license to consume Gold data.
5. The project runs in a development/staging environment before production deployment.

---

## 8. Constraints

- The scraper only accesses public Goodreads data; no user credentials or private APIs are used.
- RDS credentials must be migrated to AWS Secrets Manager before a production deployment.
- The system operates in region `us-east-2`; changing regions requires adjustments to Bedrock scripts.

---

## 9. Project Acceptance Criteria

The project will be considered successfully completed when:

1. The pipeline runs automatically without manual intervention for at least **2 consecutive weekly cycles** without errors.
2. Gold layer data correctly answers the question: *"What are the Top 10 books and Top 20 genres of the last 5 weeks?"*
3. Documentation is complete and understandable by an engineer who did not participate in development.
4. Unit tests pass successfully in a clean environment.
5. The CloudFormation template deploys the infrastructure in a new account without additional manual steps.

---

## 10. Responsibilities

| Responsibility | Team |
|----------------|------|
| Code development and maintenance | MISAMO inc. — Data Engineering Team |
| AWS infrastructure and security | MISAMO inc. — AWS Administration Team |
| Business requirements definition | MISAMO inc. — Purchasing / Inventory Team |
| Dashboard consumption and analysis | MISAMO inc. — Business Team |
| Deliverable approval | MISAMO inc. — Project Management |

---

*Document prepared by MISAMO inc. — Internal use only*
