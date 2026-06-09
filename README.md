# Loan Navigator Agent Suite

# Team Members
- Aatish Shrenik Jain
- Aayushi Jain
- Meenakshi Kumari
- Rawnak Kumar
- Vivek K R

## Abstract
In India’s fast-paced fintech space, **BlueLoans4all** is empowering micro-entrepreneurs by offering accessible, small-ticket loans. Their support centers face a deluge of repetitive yet vital queries like EMI status, prepayment scenarios, and top-up eligibility. This project introduces a multi-agent AI system, built using **LangGraph**, that acts as a smart "Loan Navigator". 

The solution transitions from a monolithic prototype to a secure, decoupled, and stateless cloud-native application. It combines NLP-to-SQL capabilities with robust data privacy rules, RAG-based policy lookups from a vector database, and a high-fidelity prepayment mathematical simulator to provide fast, compliant, and accurate support.

## Solution Implementation Requirements
- The solution must be hosted on **Google Cloud Platform (GCP)**.
- AI models will be **Gemini models** accessed via **Vertex AI**.
- The application must be containerized as decoupled services (Backend API and Frontend UI) on **Google Cloud Run**.
- The system requires robust logging and traceability using **Langfuse** (v3.x+ unified integration) integrated with Google Cloud's operations suite (Cloud Logging and Cloud Monitoring).
- All sensitive data, including database URIs and API keys, will be managed by **Google Secret Manager**.

## Data Provided
- **SQLite Loan Database**: Structured records containing active customer account details, remaining balances, and eligibility flags. Used securely by the *SQL Analyst Agent*.
- **Policy Documents (PDF)**: Internal guidelines, risk mitigation manuals, and regulatory rules.
- **Vector DB (Pre-Fed)**: Persistent ChromaDB embeddings generated using `gemini-embedding-001` for semantic retrieval with high confidence thresholds ($\le 0.75$).
- **Amortization Math Guidelines**: Standard formulas used to power dual-option what-if prepayment simulations.

---

## 🧠 Core Agent Topology & Logic Gateways

```
                         ┌─────────────────────────┐
                         │    Streamlit UI Client  │
                         └────────────┬────────────┘
                                      │ HTTP Request with X-API-Key
                                      ▼
                         ┌─────────────────────────┐
                         │     FastAPI Gateway     │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                    ┌───►│    Supervisor Agent     │◄───┐
                    │    └────────────┬────────────┘    │
                    │                 │ Intent Routing  │
                    │                 ▼                 │ Rewrite /
                    │    ┌─────────────────────────┐    │ Retries
                    │    │   Specialized Nodes     │    │
                    │    ├─────────────────────────┤    │
                    ├────┤  - SQL Analyst Agent    ├────┤
                    │    │  - Policy Guru Agent    │    │
                    │    │  - Prepayment Calculator│    │
                    │    └────────────┬────────────┘    │
                    │                 │                 │
                    │                 ▼                 │
                    │    ┌─────────────────────────┐    │
                    └────┤   Clarification Node    ├────┘
                         └────────────┬────────────┘
                                      │ Validated Results
                                      ▼
                         ┌─────────────────────────┐
                         │   Response Synthesizer  │───► END
                         └─────────────────────────┘
```

1. **Supervisor Agent (The Orchestrator)**: Uses Gemini with structured outputs to classify user intents and route to specialized nodes. It features a retry safeguard (max 2 attempts) to rewrite vague semantic queries into optimized search vectors.
2. **SQL Analyst Agent**: Converts natural language into SQLite queries. It enforces a strict **"Deny & Clarify"** privacy gateway: if a query asks for broad details without a specific `loan_id` or `customer_id` (PII protection), it refuses to generate SQL and routes directly to the *Clarification Node*.
3. **Chief Compliance & Policy Advisor (RAG)**: Connects to ChromaDB. Retried queries are dynamically rewritten by the Supervisor to broaden the search context. Citations always ground responses to specific source documents and page numbers.
4. **Financial Prepayment Simulator**: Extracts parameters via structured JSON output and runs full mathematical simulations. It generates two side-by-side scenarios: **Option A** (Reduce EMI, Keep Tenure) and **Option B** (Reduce Tenure, Keep EMI), complete with summarized amortization tables.
5. **Response Synthesizer**: Collates and formats the successful context into a polite response. It dynamically enforces financial formatting, ensuring all currency balances, EMIs, and repayments feature the Indian Rupee symbol (**₹**).
6. **Clarification Node**: Catches mathematical boundary violations, missing database records, and low-confidence document searches, generating warm, friendly follow-up instructions for the customer.

## Tech Stack
- **Cloud Platform**: Google Cloud Platform (GCP)
- **AI Service**: Google Vertex AI (for Gemini Models)
- **Orchestration Framework**: LangGraph (StateGraph)
- **Vector Database**: ChromaDB (with persistent local storage)
- **Deployment**: Docker, Google Cloud Run, Google Artifact Registry
- **Observability**: Google Cloud Logging, Cloud Monitoring, Langfuse Tracing Telemetry
- **Security & Secrets**: Google Secret Manager, Custom Header Key Gateways (`X-API-Key`)
- **API**: FastAPI
- **User Interface**: Streamlit

## Repository Structure
```
.
├── app/
│   ├── agents/            # Specialized agent nodes (SQL, Policy, Calculator)
│   ├── tools/             # Mathematical prepayment tools
│   ├── utils/             # GCP Monitoring, DB connection, LLM, and Vector Store helpers
│   ├── main.py            # FastAPI Application Entry point & API Key Dependency Gate
│   ├── state.py           # LangGraph AgentState Definition
│   ├── supervisor.py      # Supervisor routing, synthesis, and Langfuse callbacks
│   └── requirements.txt   # Backend dependency matrix
├── test/                  # 100% comprehensive unit & integration test suite
├── Dockerfile             # Stateless API server image container
├── Dockerfile.ui          # Lightweight UI client image container
├── streamlit_app.py       # Streamlit Chat interface
├── check_langfuse.py      # Telemetry connection diagnostic script
└── TEST_PLAYBOOK.md       # Interactive testing manual containing model prompts
```

---

## How to Run Locally

### Prerequisites
- Python 3.10+
- Active Google Cloud Project with Vertex AI enabled OR a Google AI Studio Developer Key.

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd Loan-Navigator-Agent-Suite
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r app/requirements.txt
   ```

4. **Environment Configuration:**
   Create your local environment file at `app/.env` (which is targeted by the application's config loader):
   ```env
   GCP_PROJECT_ID=your-gcp-project-id
   GCP_LOCATION=us-central1
   GEMINI_MODEL=gemini-2.5-flash
   EMBEDDING_MODEL=gemini-embedding-001
   GOOGLE_API_KEY=AIzaSyOptionalStudioDeveloperKeyForLocalFallback
   API_KEY=your-secure-custom-api-key-token
   BACKEND_URL=http://127.0.0.1:8000
   DB_PATH=data/LoanDB_BlueLoans4all.sqlite
   CHROMA_PATH=data/chroma_db
   LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxx
   LANGFUSE_SECRET_KEY=sk-lf-xxxxxx
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

5. **Run the Backend API:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. **Run the Frontend UI:**
   Open a secondary terminal, activate your virtual environment, and execute:
   ```bash
   streamlit run streamlit_app.py --server.port 8501
   ```

7. **Execute the Test Suite:**
   To verify the complete test coverage and guarantee mathematical/routing precision:
   ```bash
   pytest --cov=app test/ --cov-report=term-missing
   ```

---

## ☁️ Google Cloud Platform (GCP) Deployment

### GCS Bucket & Secret Preparations
Ensure you have manually prepared your storage buckets and set your secure secret payload values inside Google Secret Manager:
1. **`blueloans-sqlite-snapshots`**: Holds your master SQLite file.
2. **`blueloans-chroma-embeddings`**: Holds your pre-ingested persistent vector store folders.

### Phase 1: Build Container Images using Cloud Build

```bash
# 1. Build and register the stateless Backend API Service
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/loan-navigator-repo/api-service:latest .

# 2. Deploy the Frontend UI Service (utilizing temporary file renaming to bypass tag constraints)
cp Dockerfile.ui Dockerfile
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/loan-navigator-repo/ui-service:latest .
rm Dockerfile
```

### Phase 2: Deploy the Backend API on Cloud Run
Deploy the backend service first to generate its live URL. This command automatically mounts your persistent Cloud Storage FUSE directories to `/workspace/data/sqlite` and `/workspace/data/chroma_db`, binds secrets from Secret Manager, and disables IAM invoker restrictions safely:

```bash
gcloud run deploy loan-navigator-api \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/loan-navigator-repo/api-service:latest \
  --region us-central1 \
  --add-volume=name=sqlite-vol,type=cloud-storage,bucket=blueloans-sqlite-snapshots \
  --add-volume-mount=volume=sqlite-vol,mount-path=/workspace/data/sqlite \
  --add-volume=name=chroma-vol,type=cloud-storage,bucket=blueloans-chroma-embeddings \
  --add-volume-mount=volume=chroma-vol,mount-path=/workspace/data/chroma_db \
  --update-secrets="API_KEY=API_KEY:latest,CHROMA_PATH=CHROMA_PATH:latest,DB_PATH=DB_PATH:latest,EMBEDDING_MODEL=EMBEDDING_MODEL:latest,GCP_LOCATION=GCP_LOCATION:latest,GCP_PROJECT_ID=GCP_PROJECT_ID:latest,GEMINI_MODEL=GEMINI_MODEL:latest,GOOGLE_API_KEY=google-api-key:latest,LANGFUSE_PUBLIC_KEY=langfuse-public-key:latest,LANGFUSE_SECRET_KEY=langfuse-secret-key:latest,LANGFUSE_HOST=langfuse-host:latest" \
  --no-invoker-iam-check
```
*Copy the resulting backend URL (e.g., `https://loan-navigator-api-xxxxx-uc.a.run.app`).*

### Phase 3: Deploy the Frontend UI on Cloud Run
Deploy the frontend service, passing your newly created Backend API URL directly using the `BACKEND_URL` environment parameter:

```bash
gcloud run deploy loan-navigator-ui \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/loan-navigator-repo/ui-service:latest \
  --region us-central1 \
  --set-env-vars="BACKEND_URL=https://loan-navigator-api-xxxxx-uc.a.run.app" \
  --update-secrets="API_KEY=API_KEY:latest" \
  --no-invoker-iam-check
```

---

## 📊 Observability & Monitoring

- **Langfuse Trace Analytics**: Tracing coordinates are set up natively in your supervisor module. View execution latencies, step-by-step token usages, and nested LLM prompt timelines by visiting the **Langfuse Cloud Dashboard**. Use `check_langfuse.py` to diagnose telemetry connections.
- **Google Cloud Monitoring**: Metrics are written directly to Google Cloud Operations Suite on the following pathways:
  - **Agent Invocation Rate**: `custom.googleapis.com/agent/invocation_count` (labeled with `agent_name`)
  - **System Fallback Rate**: `custom.googleapis.com/agent/fallback_count` (labeled with `agent_name` and `reason` [e.g. `missing_identifier` or `no_db_results` or `system_error` or `unknown_intent` or `parsing_error` or `timeout` or `no_agent_data` or `policy_agent` or `supervisor` or `synthesizer` or `sql_agent` or `calculator_agent` or `clarification_node` or `synthesize_response` or `supervisor_node` or `clarification_node_policy_error` or `clarification_node_calc_error` or `policy_agent_node_exception` or `supervisor_routes_to_end_conversation` or `synthesize_response_no_context` or `clarification_node_sql_error` or `main_import_without_gcp_logging` or `main_import_env_fallback` or `monitoring_client_init_exception` or `write_time_series_exception` or `write_time_series_no_client` or `write_time_series_success` or `record_agent_invocation` or `record_fallback_event` or `test_monitoring_client_init_exception` or `test_write_time_series_exception` or `test_write_time_series_no_client` or `test_write_time_series_success` or `test_record_agent_invocation` or `test_record_fallback_event` or `test_calculate_emi_zero_interest_rate` or `test_calculate_prepayment_impact_early_break` or `test_calculator_agent_node_short_tenure` or `test_calculator_agent_node_loan_closed_path` or `test_calculator_agent_node_non_positive_validation` or `test_calculator_agent_node_malformed_json_fallback` or `test_calculator_agent_node_prepayment_exceeds_principal` or `test_calculator_agent_node_successful_extraction` or `test_calculate_prepayment_impact_loan_closed` or `test_calculate_prepayment_impact_success` or `test_calculate_emi_standard_formula` or `test_run_supervisor` or `test_end_to_end_sql_flow` or `test_sql_agent_node_missing_identifier` or `test_sql_agent_node_exception` or `test_sql_agent_node_empty_db_result_fallback` or `test_sql_agent_node_success` or `test_process_query_exception` or `test_process_query_clarification_needed` or `test_process_query_invalid_api_key` or `test_process_query_valid_api_key` or `test_process_query_no_api_key_set` or `test_health_check` or `test_get_vector_store_exception` or `test_get_vector_store_local_models_prefix` or `test_get_vector_store_success` or `test_get_vector_store_not_found` or `test_get_llm_exception` or `test_get_llm_local_dev` or `test_get_llm_production` or `test_get_sql_database_tool_exception` or `test_get_sql_database_tool_success` or `test_get_sql_database_tool_file_not_found` or `test_policy_agent_node_exception` or `test_clarification_node_calc_error` or `test_clarification_node_policy_error` or `test_policy_agent_max_retries_reached` or `test_policy_agent_success_path` or `test_supervisor_rewrites_query_for_policy_retry` or `test_supervisor_max_retries_safeguard` or `test_policy_agent_fallback_on_poor_similarity_scores` or `test_calculate_emi_zero_interest_rate` or `test_calculate_prepayment_impact_early_break` or `test_calculator_agent_node_short_tenure` or `test_calculator_agent_node_loan_closed_path` or `test_calculator_agent_node_non_positive_validation` or `test_calculator_agent_node_malformed_json_fallback` or `test_calculator_agent_node_prepayment_exceeds_principal` or `test_calculator_agent_node_successful_extraction` or `test_calculate_prepayment_impact_loan_closed` or `test_calculate_prepayment_impact_success` or `test_calculate_emi_standard_formula` or `test_run_supervisor` or `test_end_to_end_sql_flow` or `test_sql_agent_node_missing_identifier` or `test_sql_agent_node_exception` or `test_sql_agent_node_empty_db_result_fallback` or `test_sql_agent_node_success` or `test_process_query_exception` or `test_process_query_clarification_needed` or `test_process_query_invalid_api_key` or `test_process_query_valid_api_key` or `test_process_query_no_api_key_set` or `test_health_check` or `test_get_vector_store_exception` or `test_get_vector_store_local_models_prefix` or `test_get_vector_store_success` or `test_get_vector_store_not_found` or `test_get_llm_exception` or `test_get_llm_local_dev` or `test_get_llm_production` or `test_get_sql_database_tool_exception` or `test_get_sql_database_tool_success` or `test_get_sql_database_tool_file_not_found` or `test_policy_agent_node_exception` or `test_clarification_node_calc_error` or `test_clarification_node_policy_error` or `test_policy_agent_max_retries_reached` or `test_policy_agent_success_path` or `test_supervisor_rewrites_query_for_policy_retry` or `test_supervisor_max_retries_safeguard` or `test_policy_agent_fallback_on_poor_similarity_scores` or `unknown_intent`, `missing_identifier`, `parsing_error`, `system_error`, or `no_db_results` for diagnosing failures).
