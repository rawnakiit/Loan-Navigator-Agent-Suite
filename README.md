# Loan Navigator Agent Suite

## Abstract
In India’s fast-paced fintech space, **BlueLoans4all** is empowering micro-entrepreneurs by offering accessible, small-ticket loans. Their support centers face a deluge of repetitive yet vital queries like EMI status, prepayment scenarios, and top-up eligibility. This project introduces a multi-agent AI system, built using **LangGraph**, that acts as a smart "Loan Navigator". 

The solution combines NLP-to-SQL capabilities, RAG-based policy lookups from a vector database, and a what-if simulation engine to provide accurate, secure, and compliant answers to customer queries. By automating these interactions, the system enhances the borrower experience, reduces operational load, and ensures regulatory adherence.

## Solution Implementation Requirements
- The solution must be hosted on **Google Cloud Platform (GCP)**.
- AI models will be **Gemini models** accessed via **Vertex AI**.
- The application must be containerized and deployable on **Google Cloud Run**.
- The system requires robust logging and traceability using **Langfuse or MLflow** integrated with Google Cloud's operations suite.
- All sensitive data, including database URIs and API keys, will be managed by **Google Secret Manager**.

## Data Provided
- **SQLite Loan Database**: Structured records for approximately 1000 loans (loan_amount, tenure, interest_rate, topup_eligible). Used by the *SQL Analyst Agent*.
- **Policy Documents (PDF)**: Internal policies, risk guidelines, and regulatory mandates for the *Policy Guru Agent*.
- **Vector DB (Pre-Fed)**: Contains embeddings of the policy documents, enabling fast semantic search.
- **Amortization Schedule & Documents**: Technical documents outlining EMI formulas and prepayment logic for the *What-If Calculator Agent*.

## Solution Design
The solution is built in 5 phases:
1. **Phase 1: Foundation & Data Infrastructure**: GCP Setup, Database & Storage, Security, Agent Framework Scaffolding.
2. **Phase 2: Core Agent Development & Logic**: Building the SQL Analyst Agent, Policy Guru Agent, and What-If Calculator Agent.
3. **Phase 3: Multi-Agent Orchestration**: Implementing the Supervisor Agent using LangGraph for intent classification and response synthesis.
4. **Phase 4: API & UI Development and Deployment**: Creating a FastAPI wrapper, containerizing via Docker, and deploying to Cloud Run.
5. **Phase 5: Observability, Testing & Governance**: Integrating tracing (Langfuse/MLflow), testing, and setting up CI/CD.

## Expected Deliverables
- **Deployment Artifacts**: Containerized services for all four agents deployed on Google Cloud Run via Artifact Registry. Secure FastAPI endpoints.
- **Documentation**: OpenAPI specification, agent interaction diagrams (see `architecture.md`), prompt templates, and a setup runbook.
- **Monitoring & Observability**: Dashboard in Google Cloud Monitoring and Langfuse/MLflow for traceability.

## Tech Stack
- **Cloud Platform**: Google Cloud Platform (GCP)
- **AI Service**: Google Vertex AI (for Gemini Models)
- **Orchestration Framework**: LangGraph (or CrewAI)
- **Vector Database**: Chroma / Pinecone / Weaviate
- **Deployment**: Docker, Google Cloud Run, Google Artifact Registry
- **Observability**: Google Cloud's operations suite, Langfuse or MLflow
- **Security & Secrets**: Google Secret Manager, Google Cloud IAM
- **API**: FastAPI

## Repository Structure
Please refer to the `app/` directory for the application's source code and components.
- `app/main.py`: FastAPI application entry point.
- `app/supervisor.py`: LangGraph supervisor orchestrator.
- `app/agents/`: Specialized agent implementations (SQL, Policy, Calculator).
- `app/utils/`: Shared utilities (Database, LLM, Vector Store).

## How to Run Locally

### Prerequisites
- Python 3.10+
- A Google Cloud Project with Vertex AI enabled.
- A Service Account JSON key with Vertex AI User permissions.

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd Loan-Navigator-Agent-Suite
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r app/requirements.txt
   ```

4. **Environment Variables:**
   Copy the example environment file and fill in your GCP credentials and project details.
   ```bash
   cp app/.env.example app/.env
   ```
   *Make sure to update `GOOGLE_APPLICATION_CREDENTIALS` and `GCP_PROJECT_ID` in your `.env` file.*

5. **Run the Application:**
   Start the FastAPI development server using Uvicorn.
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the API:**
   - Swagger UI Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`
