# Request for Proposal (RFP)
## Data Engineering Solution for Popular Books Tracking

**Version**: 1.0  
**Date**: 2026-05-24  
**Document**: Request for Proposal  
**Organization**: MISAMO inc.  
**Project**: Popular Books Tracker

---

## 1. Introduction

MISAMO inc. issues this Request for Proposal (RFP) for the **implementation of a data engineering solution** that enables identifying and tracking trends in books and literary genres on a weekly automated basis.

This document describes the business context, technical and functional requirements, evaluation criteria, and expected delivery conditions for teams or vendors wishing to participate in this project.

---

## 2. Context and Problem Statement

### 2.1 Current Situation

MISAMO inc. operates retail bookstores whose purchasing and inventory teams make book acquisition decisions based primarily on:

- Printed publisher catalogs (updated quarterly).
- Personal judgment of buyers.
- Social media trends (not representative of actual reading behavior).

This lack of objective, up-to-date data results in:
- **Overstocking** titles that generate no sales.
- **Stockouts** on high-demand books.
- Missed business opportunities in emerging genres.

### 2.2 Identified Opportunity

The **Goodreads** platform, with more than 150 million registered users, publishes a weekly list of the 50 most-read books by its community. This information is publicly accessible and reliably reflects current reading behavior at a global scale.

The opportunity is to capture, structure, and analyze this data in an automated way to convert it into **actionable business intelligence**.

---

## 3. Project Objectives

1. **Automate** the weekly capture of the most popular books list from Goodreads.
2. **Enrich** data with review sentiment analysis and AI-generated commercial descriptions.
3. **Aggregate** historical metrics to identify books and genres with sustained demand.
4. **Present** results in a format consumable by business intelligence tools.

---

## 4. Functional Requirements

Proposals must contemplate the implementation of all requirements listed below:

### FR-01 — Automated Data Extraction
- Weekly automated capture of the 50 most-read books from Goodreads.
- Data to extract includes: title, author, description, genres, average rating, publication date, and user reviews with like scores.
- The process must be resilient to network failures with a retry policy.

### FR-02 — Layered Storage (Bronze / Silver / Gold)
- Raw data must be stored in a Bronze layer without transformation.
- Enriched data must be stored in a Silver layer with a typed schema and query-optimized format.
- Business metrics must be persisted in a Gold layer with a relational structure.

### FR-03 — Generative AI Enrichment
- The system must generate, using a large language model (LLM), a Spanish-language review sentiment summary (maximum 30 words per book).
- The system must generate an attractive Spanish-language commercial description (maximum 50 words).
- Generation costs must be minimized by avoiding reprocessing of already-known books.

### FR-04 — Trend Metrics
- Calculation of the Top 10 most repeated books over a configurable week window.
- Calculation of the Top 20 most frequent genres over the same window.
- Historical persistence of results to analyze trend evolution.

### FR-05 — Scheduling and Automation
- Full pipeline execution every week without manual intervention.
- Dependency management between steps (scraping → transformation → enrichment).
- Failure notification or logging at each stage.

### FR-06 — BI-Ready Data Access
- Gold layer data must be accessible from standard BI tools (Tableau, Power BI) via JDBC/ODBC or CSV export.

---

## 5. Technical Requirements

### 5.1 Infrastructure
- The solution must be implemented on **Amazon Web Services (AWS)**.
- A **serverless** approach is preferred to minimize baseline costs and operational overhead.
- All resources must be reproducible via an **infrastructure as code template** (CloudFormation, CDK, or Terraform).

### 5.2 Compute and ETL
- Scraping must be implemented as a serverless function (AWS Lambda or equivalent).
- Data transformations must support horizontal scaling (AWS Glue with PySpark or equivalent).

### 5.3 Storage
- **Data lake**: Amazon S3 with folder structure by layer and temporal partitioning.
- **Relational database**: Amazon RDS PostgreSQL or equivalent for the Gold layer.
- **Columnar format**: Silver data must be stored in Parquet or equivalent format.

### 5.4 Artificial Intelligence
- The LLM for enrichment must be accessible from the AWS VPC without internet exposure.
- **Amazon Bedrock** is preferred to keep data within the AWS ecosystem.

### 5.5 Security
- Service-to-service communication via IAM roles with least-privilege principle.
- No hardcoded credentials in production source code.
- Goodreads user data: only review text and likes; no PII.

### 5.6 Observability
- Logs from each component in Amazon CloudWatch.
- Execution traceability in the workflow orchestrator.

---

## 6. Documentation Requirements

Documentation deliverables must include:

| Document | Expected content |
|----------|-----------------|
| Functional Documentation | Requirements, use cases, business rules, process flows |
| Technical Documentation | Component specifications, schemas, APIs, configuration |
| Architecture Documentation | Diagrams, design decisions, technology stack |
| Deployment Guide | Step-by-step instructions to replicate the system from scratch |
| Tests | Unit tests, integration tests, and configuration tests |

---

## 7. Evaluation Criteria

Proposals will be evaluated according to the following criteria:

| Criterion | Weight |
|-----------|--------|
| Functional completeness (compliance with FR-01 through FR-06) | 30% |
| Technical quality and best practices (IaC, security, modularity) | 25% |
| Estimated monthly AWS operating cost | 20% |
| Documentation quality and completeness | 15% |
| Maintainability and extensibility | 10% |

---

## 8. Constraints and Considerations

- The project must respect [Goodreads Terms of Service](https://www.goodreads.com/about/terms); only public data is accessed.
- The solution must not perform aggressive scraping; delays between requests and HTTP 429 error handling are required.
- Estimated monthly AWS operating budget must not exceed **USD $50/month** for current volume (50 books/week).
- The solution must be operational within a maximum of **6 weeks** from project start.

---

## 9. Expected Deliverables

Upon project completion, the vendor or team must deliver:

1. Source code repository with structure organized by component.
2. Deployed and functional infrastructure in an AWS account.
3. Evidence of at least 2 successful pipeline executions (screenshots).
4. Complete documentation suite (see Section 6).
5. Knowledge transfer to MISAMO inc. technical team.

---

## 10. Response Process

Interested teams must present:

1. **Technical proposal**: Description of proposed architecture with diagram.
2. **Commercial proposal**: Estimate of development and monthly operating costs.
3. **Schedule**: Delivery milestones and estimated dates.
4. **Team**: Profiles and roles of the proposed team.

---

*Document prepared by MISAMO inc. — Internal use only*
