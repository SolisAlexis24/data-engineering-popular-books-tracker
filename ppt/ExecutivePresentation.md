# Executive Presentation
## Popular Books Tracker
### MISAMO inc. — 2026

> This document contains the script and content for the project executive presentation.  
> Convert to PowerPoint (.pptx) using tools such as Marp, Pandoc, or import manually into Google Slides / PowerPoint.

---

## SLIDE 1 — Cover

**Title**: Popular Books Tracker  
**Subtitle**: Data Lake Implementation for Tracking Popular Books and Genres  
**Organization**: MISAMO inc.  
**Date**: May 2026

---

## SLIDE 2 — The Problem

**Title**: The bookseller's purchasing challenge

**Key points**:
- Purchasing teams make inventory decisions without objective, up-to-date data
- Publisher catalogs are updated quarterly — the market changes weekly
- Overstocking low-demand titles directly impacts profitability
- Opportunities in emerging genres are missed due to lack of visibility

**Suggested image**: Chart of unsold vs. out-of-stock books

---

## SLIDE 3 — The Opportunity

**Title**: Goodreads: 150M users, public data, updated weekly

**Key points**:
- Goodreads publishes the **Top 50 most-read books** every week from its community
- Reflects real reading behavior — not just sales or advertising
- Includes reviews and ratings that reveal reader sentiment
- This information is not currently being systematically exploited

**Highlighted figure**: *"50 books × 52 weeks = continuous signal of market trends"*

---

## SLIDE 4 — The Solution

**Title**: Popular Books Tracker — Automated data pipeline

**Key points**:
- Fully **automated** weekly extraction of the 50 most-read books
- Enrichment with **generative AI** (Spanish-language review summaries)
- Identification of the **Top 10 books** and **Top 20 genres** with sustained demand
- Results ready to consume in business tools (Tableau, Power BI)

**Suggested image**: Simplified architecture diagram (Bronze → Silver → Gold)

---

## SLIDE 5 — Architecture (Simplified)

**Title**: Medallion Architecture on AWS

```
Goodreads
    │
    ▼
[Lambda] Weekly extraction
    │
    ▼
[S3 Bronze] Raw JSON
    │
    ▼
[Glue + Bedrock] AI enrichment
    │
    ▼
[S3 Silver] Curated data
    │
    ▼
[Glue] Aggregations
    │
    ▼
[RDS Gold] Top 10 books · Top 20 genres
    │
    ▼
[Tableau / Power BI] Executive dashboard
```

**Automation**: EventBridge → Step Functions (every Sunday at 18:00)

---

## SLIDE 6 — Key Technologies

**Title**: AWS technology stack — 100% serverless

| Component | Technology | Benefit |
|-----------|-----------|---------|
| Extraction | AWS Lambda (Python) | No servers, pay-per-use |
| Transformation | AWS Glue (PySpark) | Automatic scaling |
| Generative AI | Amazon Bedrock Nova Lite | Spanish summaries, low cost |
| Storage | Amazon S3 (Parquet) | Economical, analytics-optimized |
| Database | Amazon RDS PostgreSQL | BI-compatible, SQL queries |
| Orchestration | AWS Step Functions | Robust flow with retries |
| Scheduling | Amazon EventBridge | Automated weekly execution |

---

## SLIDE 7 — The Value of AI Enrichment

**Title**: From raw data to business intelligence

**Before (raw data)**:
```
Genres: ["Romance", "Fiction", "Contemporary"]
Reviews: "Amazing book! Couldn't put it down..." (142 likes)
         "A beautiful love story..." (89 likes)
```

**After (AI-enriched)**:
```
Description: "A captivating contemporary love story that
              wins the heart with deeply human characters."

Sentiment: "Readers highlight an emotional and irresistible
            narrative that generates high engagement."
```

**Impact**: The buyer understands the book in seconds, in their language.

---

## SLIDE 8 — Results

**Title**: What does the system deliver?

**Top 10 Most Repeated Books (last 5 weeks)**:

| # | Book | Appearances |
|---|------|------------|
| 1 | Example: "The Women" | 5/5 weeks |
| 2 | Example: "Intermezzo" | 4/5 weeks |
| ... | ... | ... |

**Top 20 Most Frequent Genres**:
- Romance · Fiction · Mystery · Thriller · Historical Fiction · ...

**Visualization**: See [img/graphic.png](../img/graphic.png) — Power BI example

---

## SLIDE 9 — Business Benefits

**Title**: Expected operational impact

| Area | Before | With Popular Books Tracker |
|------|--------|---------------------------|
| Purchase decision | Intuition + quarterly catalogs | Objective weekly data |
| Analysis time | Hours of manual research | Automatic results every Monday |
| Trend coverage | Local / subjective | 150M Goodreads users |
| Information language | English (original source) | Spanish (AI-generated summaries) |
| Analysis cost | Person-hours | ~USD $10–30/month in AWS |

---

## SLIDE 10 — Estimated Operating Cost

**Title**: Cost model — Pay-per-use

| Service | Estimated monthly usage | Estimated cost |
|---------|------------------------|---------------|
| AWS Lambda | 4 invocations × 3 min | ~$0.01 |
| AWS Glue | 4 jobs × 2 DPU × ~30 min | ~$5.00 |
| Amazon Bedrock Nova Lite | ~200 new books × 2 calls | ~$2.00 |
| Amazon S3 | <1 GB storage | ~$0.03 |
| Amazon RDS (t3.micro) | 730 hours | ~$15.00 |
| Other (Step Functions, EventBridge) | Minimal | ~$0.01 |
| **TOTAL ESTIMATED** | | **~$22/month** |

*Note: Approximate costs for current volume. RDS can be paused off-hours to reduce costs.*

---

## SLIDE 11 — Roadmap

**Title**: Next steps

**Phase 2 — Security and Operations**:
- [ ] Migrate RDS credentials to AWS Secrets Manager
- [ ] Enable S3 encryption at rest (SSE-KMS)
- [ ] Set up CloudWatch alarms + SNS notifications

**Phase 3 — Data Enrichment**:
- [ ] Add additional sources (Amazon Best Sellers, NYT)
- [ ] Historical trend analysis (more than 52 weeks)
- [ ] Segmentation by market or region

**Phase 4 — Integration**:
- [ ] Direct connection to bookstore ERP or POS system
- [ ] Dedicated Tableau dashboard with automatic alerts
- [ ] REST API for programmatic queries

---

## SLIDE 12 — Conclusion

**Title**: Popular Books Tracker — Data that creates value

**Key messages**:
1. **Full automation**: From Goodreads to executive dashboard without manual intervention
2. **AI applied to business**: Spanish summaries that accelerate purchasing decisions
3. **Low cost**: ~$22/month for weekly market intelligence
4. **Scalable**: AWS serverless architecture that grows with the business
5. **Available today**: System deployed and running in production

**Call to action**: *"Connect your BI tool to the Gold data and start making decisions based on real trends."*

---

## Presenter Notes

- **Target audience**: Purchasing managers, business executives, technology team
- **Suggested duration**: 15–20 minutes + 5 minutes for Q&A
- **Emphasis**: Focus on slide 9 (benefits) and the dashboard demo (slide 8)
- **Live demo**: If possible, show the Power BI dashboard with real data (see `img/graphic.png`)
- **Frequently asked questions**:
  - *Is scraping legal?* → Only public data, no PII, respects Goodreads ToS
  - *What if Goodreads changes its design?* → The scraper requires maintenance; HTML structure monitoring can be added
  - *Can it be extended to other sources?* → Yes, the medallion architecture is designed for that

---

> **Conversion to PowerPoint instructions**:
> ```bash
> # Option 1: Pandoc (recommended)
> pandoc ppt/ExecutivePresentation.md -o ppt/ExecutivePresentation.pptx
>
> # Option 2: Marp (with styles)
> marp ppt/ExecutivePresentation.md --pptx -o ppt/ExecutivePresentation.pptx
> ```
