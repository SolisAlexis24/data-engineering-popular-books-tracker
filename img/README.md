# img/

Visual assets for the project.

| File | Description |
|------|-------------|
| `architecture.jpg` | AWS architecture diagram for the pipeline |
| `stepfunctions_graph.png` | Step Functions execution flow graph |
| `graphic.png` | Power BI visualization example (popular genres) |

## Screenshots to add

To evidence the AWS implementation, include screenshots of:

- Lambda console — scraper function deployed
- S3 console — bucket with Bronze/Silver folder structure
- Glue console — `bronze-to-silver` and `silver-to-gold` jobs executed successfully
- Step Functions console — full pipeline execution
- RDS console — PostgreSQL instance active
- EventBridge console — weekly rule configured
- RDS Query — results from `repeticiones_libros` and `repeticiones_generos` tables
