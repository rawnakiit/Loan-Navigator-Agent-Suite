# Architecture: Loan Navigator Agent Suite

## System Overview

The **Loan Navigator Agent Suite** is a multi-agent system designed to act as a smart "Loan Navigator" for BlueLoans4all. It automates responses to repetitive customer queries related to EMI status, prepayment scenarios, and top-up eligibility while ensuring compliance with RBI norms.

The solution is hosted on **Google Cloud Platform (GCP)**, deployed as a containerized application via **Cloud Run**, and leverages **Google Vertex AI** for Gemini models. 

## High-Level Architecture

```text
+-------------------------------------------------------------+
|               Customer / Support Staff                      |
+-----------------------------+-------------------------------+
                              |
                              v
+-----------------------------+-------------------------------+
|                     FastAPI Gateway                         |
|             (IAM & Secret Manager Secured)                  |
+-----------------------------+-------------------------------+
                              |
                              v
+-----------------------------+-------------------------------+
|               Supervisor Agent (LangGraph)                  |
|         (Logs to Observability - Langfuse/MLflow)           |
+-------------+---------------+---------------+---------------+
              |               |               |
              v               v               v
      +-------+-------+ +-----+-------+ +-----+---------+
      |  SQL Analyst  | | Policy Guru | |   What-If     |
      |     Agent     | |    Agent    | |  Calculator   |
      +-------+-------+ +-----+-------+ +---------------+
              |               |                 
              v               v                 
      +-------+-------+ +-----+-------+ 
      |  SQLite Loan  | |  Vector DB  | 
      |   Database    | |  (Chroma)   | 
      +-------+-------+ +-----+-------+ 
              |               |                 
              v               v                 
      +-------+-------+ +-----+-------+ 
      | 1000+ Loan    | | Policy Docs |
      |   Records     | |    (PDF)    |
      +---------------+ +-------------+
```

## Agent Design

The system employs a multi-agent architecture orchestrated by a supervisor. We use **LangGraph** (or CrewAI) to manage the state and control flow between these agents.

1. **Supervisor Agent**: 
   - Acts as the central orchestrator.
   - Classifies user intent and routes tasks to the appropriate specialized sub-agents.
   - Merges responses, ensures consistent tone, and manages clarification/fallback chains.

2. **SQL Analyst Agent**:
   - Converts natural language queries into secure, parameter-whitelisted SQL queries.
   - Fetches structured data from the internal SQLite Loan Database.
   - Flags failed or empty results to the Supervisor.

3. **Policy Guru Agent**:
   - Executes RAG (Retrieval-Augmented Generation) pipelines against the Vector Database.
   - Synthesizes answers from retrieved chunks with citations.
   - Includes confidence scoring to trigger fallbacks if the retrieval quality is low (< 0.75).

4. **What-If Calculator Agent**:
   - A stateless Python function/agent performing financial and amortization simulations (e.g., prepayments, EMIs).
   - Implements input validation and structured error reporting.

## Infrastructure & Security (GCP)

- **Compute**: Google Cloud Run (Serverless, Autoscaling, Docker-based).
- **Models**: Gemini Models accessed via Vertex AI API.
- **Storage**:
  - Cloud Storage (GCS) for SQLite database.
  - Persistent volume on Cloud Run for Chroma DB (if used) or external Vector DB SaaS (Pinecone/Weaviate).
- **Security**: 
  - Google Secret Manager for all credentials, API keys, and URIs.
  - Google Cloud IAM & Identity-Aware Proxy (IAP) for endpoint security.
- **Observability**: Google Cloud's Operations Suite, supplemented by Langfuse or MLflow for detailed LLM metrics (token usage, latency, agent decisions).
- **CI/CD**: Google Cloud Build or GitHub Actions to Artifact Registry.

## Data Flow

1. User sends a query via the secure FastAPI REST endpoint.
2. The `Supervisor Agent` evaluates the intent.
3. Depending on the intent:
   - Queries involving loan balance, terms, or EMI status are routed to the `SQL Analyst Agent`.
   - Queries involving rules, regulations, or eligibility policies are routed to the `Policy Guru Agent`.
   - Queries involving future scenarios ("what-if I pay 10,000 extra?") are routed to the `What-If Calculator Agent`.
4. The agents interact with their respective backend systems (SQLite, Vector DB, Amortization Engine) and return raw answers.
5. The `Supervisor Agent` compiles the final answer, ensuring accuracy and regulatory compliance, and returns it to the user. All steps are traced and logged.
