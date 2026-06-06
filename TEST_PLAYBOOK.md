# Loan Navigator Agent Suite: UI Testing Playbook

Use this playbook to verify and test all agents, SQL database tools, financial calculator modules, and RAG search operations from the Streamlit UI.

---

## 📊 Category 1: SQL Analyst Agent (`sql_agent`)
Tests database query translation, custom parameter processing (extracting numeric IDs from prefixes), and empty state results.

### Test Case 1.1: Standard Account Inquiry with ID Cleanse
* **Prompt:** `Show my loan details for loan ID LN2003`
* **Expected Behavior:** 
  - The Supervisor routes the query to `sql_agent`.
  - The SQL Agent cleanses `LN2003` to `2003` [10], executes the query on `loan_data` [10], and passes the output to the synthesizer.
  - The response is nicely synthesized, showing the exact loan details and formatting all amounts using the Indian Rupee (**₹**) symbol [11].

### Test Case 1.2: Dynamic Balance Math Conversion
* **Prompt:** `What is my outstanding balance for customer 101?`
* **Expected Behavior:**
  - The agent executes a subtraction logic `(loan_amount - amount_paid)` against customer ID `101` [10].
  - Synthesizer prints the exact balance remaining on their account in natural language with a **₹** prefix [11].

### Test Case 1.3: Top-up Eligibility Query
* **Prompt:** `Am I eligible for a top-up on loan LN2003?`
* **Expected Behavior:**
  - Queries the `topup_eligible` flag in the database [10].
  - Generates a clear confirmation of top-up status.

### Test Case 1.4: Zero Results Fallback (Non-existent Record)
* **Prompt:** `What is the outstanding balance for customer 9999?`
* **Expected Behavior:**
  - No customer `9999` is found [12].
  - The agent triggers the `no_db_results` fallback metrics event [12].
  - Streamlit UI displays a polite request from the **Clarification Node** asking you to verify your loan details [13].

---

## 📄 Category 2: Chief Compliance & Policy Advisor (`policy_agent`)
Tests document search similarity thresholds, multi-turn vector-store rewrites, and PDF citing compliance.

### Test Case 2.1: Success Path (RAG Citation Compliance)
* **Prompt:** `Can I prepay early on my BlueLoans4all loan?`
* **Expected Behavior:**
  - Core system triggers document retrieval [14].
  - Policy Agent identifies matching chunks (similarity distance <= 0.75) [14].
  - Streamlit displays policy guidelines citing specific PDF file sources and page numbers [14].

### Test Case 2.2: Multi-turn Policy Query Rewrite
* **Prompt:** `Tell me about loan rules.`
* **Expected Behavior:**
  - **Turn 1:** The query is too vague, resulting in poor search match distances (> 0.75) [14].
  - **Turn 2:** The Supervisor node catches the retry [15], calls Gemini to rewrite the query into a broader, optimized format [15], and queries Chroma again [14, 15].
  - **Turn 3:** If matching chunks are resolved, they are synthesized with sources [14]. If it fails a second time, it routes safely to the Clarification Node [14].

### Test Case 2.3: Strict Grounding & Out-of-Scope Request (Negative Test)
* **Prompt:** `What is the company policy regarding loan deferrals for international students studying abroad?`
* **Expected Behavior:**
  - The vector database fails to find high-confidence matches (all distance scores > 0.75) for this out-of-scope scenario.
  - The agent redirects to the **Clarification Node**.
  - The UI output polite states that this specific scenario is not covered by the current policy manuals.

### Test Case 2.4: Comprehensive Criteria Extraction
* **Prompt:** `What are the documentation and behavioral requirements for a Top-up loan?`
* **Expected Behavior:**
  - The system retrieves relevant chunks from your top-up manuals.
  - The policy advisor formats the answer with clear bullet points outlining mandatory conditions, behavioral factors, and documentation needs.
  - The output cleanly cites PDF filenames and page numbers.

---

## 🧮 Category 3: Financial Prepayment Simulator (`calculator_agent`)
Tests high-fidelity extraction parameters, input validations, zero-interest fallbacks, and amortization summary layouts.

### Test Case 3.1: Standard Prepayment Math Verification
* **Prompt:** `Prepay 10,000 on 75,000 outstanding balance at 12% interest for 12 months`
* **Expected Behavior:**
  - Parameters parsed: Principal=75000, Interest Rate=12.0%, Tenure=12, Prepayment=10000 [16].
  - Amortization calculation executes two side-by-side scenarios [17]:
    - **Option A (Reduce EMI):** New EMI should be exactly **₹5,775.17** [17].
    - **Option B (Reduce Tenure):** Calculates saved months [17].
  - Amortization summary renders cleanly in Streamlit [16].

### Test Case 3.2: Partial Data Extractions (Assumed Defaults)
* **Prompt:** `What happens if I make a prepayment of 15,000?`
* **Expected Behavior:**
  - Prepayment parsed as `15000` [16].
  - System automatically uses fallback defaults: Principal=100,000, Interest=10%, Tenure=24 months [16].
  - Math runs and presents Options A and B [16].

### Test Case 3.3: Validation Boundary Trigger (Over-Prepayment)
* **Prompt:** `I want to prepay 60,000 on a 50,000 loan balance at 10% rate for 12 months`
* **Expected Behavior:**
  - Prepayment amount (60,000) exceeds principal (50,000) [16].
  - The agent catches the boundary breach, rejects execution [16], records a metrics warning, and routes to the **Clarification Node** [16].
  - Streamlit prints: *"Validation Error: The prepayment amount cannot exceed your outstanding principal..."* [16]

### Test Case 3.4: Zero Interest Support (Edge Case)
* **Prompt:** `Prepay 2,000 on a interest-free loan of 12,000 for 12 months`
* **Expected Behavior:**
  - Calculator processes a `0.0%` interest rate successfully [18].
  - Original EMI calculates to exactly **₹1,000.00** [18], presenting error-free schedules.

---

## 🛡️ Category 4: Conversational Orchestration & Zero-Trust
Tests chat router context, generic prompts, and invalid authorization checks.

### Test Case 4.1: End Conversation (Simple Greetings)
* **Prompt:** `Hi, thank you!`
* **Expected Behavior:**
  - Supervisor classifies destination as `end_conversation` [19].
  - The Synthesizer generates a friendly, warm closing statement without executing any database or PDF lookup tools [20].

### Test Case 4.2: Security Authorization Test (Simulating Bad Client)
* *To test this, make a raw terminal curl query with an invalid header:*
* **Command:** 
  ```bash
  curl -X POST "https://loan-navigator-api-456822750436.us-central1.run.app/api/v1/query" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: WRONG_TOKEN_abc123" \
    -d '{"query": "Show my loan details"}'
  ```
* **Expected Behavior:**
  - The gateway immediately blocks execution with:
    `{"detail": "Could not validate credentials: Invalid X-API-Key."}` [21]
  - Ensures zero resource/billing leakage on your Vertex AI engines [21]!
```

### How to use this file:
1. Save the above code block. It will write the playbook to your local folder.
2. Open your Streamlit frontend URL (`https://loan-navigator-ui-456822750436.us-central1.run.app`).
3. Copy prompts from each category, run them, and verify that the outputs match the expected behaviors listed in the playbook. 
4. This playbook makes an excellent addition to your project documentation and is a great asset to present to the grading panel during your capstone defense.

<!--
[PROMPT_SUGGESTION]How can I check my Google Cloud Monitoring metrics dashboard to see the logged agent_invocation events?[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]How can we run the full pytest suite locally again to ensure no code changes broke existing tests?[/PROMPT_SUGGESTION]
