import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
import logging

# ====================================================================
# GOOGLE CLOUD OPERATIONS SUITE (LOGGING & MONITORING) INTEGRATION
# ====================================================================

try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    
    # 1. Initialize the Google Cloud Logging Client
    log_client = google.cloud.logging.Client()
    cloud_handler = CloudLoggingHandler(log_client)
    
    # 2. Configure the root logger to send log outputs to BOTH the local terminal and GCP
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logging.getLogger().addHandler(cloud_handler)

    logging.info("System Boot: Successfully attached Google Cloud Logging!")
except Exception as e:
    # Fallback to standard logging if running locally without GCP credentials
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.warning(f"Running with standard local logging. GCP logger not attached: {e}")

# --- CRITICAL: Load environment variables at the very top ---
# This ensures all API keys and configurations are available to the agents.
env_path = find_dotenv(filename="app/.env")
if env_path:
    load_dotenv(env_path)
else:
    # If the .env file is in the root, find_dotenv() without args might work
    load_dotenv(find_dotenv())

import requests

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Loan Navigator Agent Suite",
    layout="centered"
)

st.title("Loan Navigator Agent Suite")
st.write(
    "Welcome to BlueLoans4all! I am your AI-powered Loan Navigator. "
    "You can ask me about your loan balance, our company policies, or run a 'what-if' prepayment simulation."
)

# --- Session State for Chat History ---
# This is crucial to maintain the conversation history.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you today?"}
    ]

# --- Display Chat History ---
# Loop through the existing messages in the session state and display them.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- User Input and Agent Interaction ---
# The st.chat_input widget gets user input and handles the "send" action.
if prompt := st.chat_input("Ask about your loan, policies, or run a simulation..."):
    
    # 1. Add user's message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Get the agent's response
    with st.chat_message("assistant"):
        # Show a "thinking" spinner while the agent processes the query
        with st.spinner("Thinking..."):
            try:
                backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
                api_key = os.getenv("API_KEY", "")
                
                headers = {"X-API-Key": api_key} if api_key else {}
                payload = {"query": prompt, "user_id": "streamlit_user_01"}
                
                response_http = requests.post(
                    f"{backend_url}/api/v1/query",
                    json=payload,
                    headers=headers,
                    timeout=60
                )
                
                if response_http.status_code == 200:
                    data = response_http.json()
                    response = data.get("response", "No response found in server payload.")
                elif response_http.status_code == 403:
                    response = "Access Denied: The client failed to authorize against the agent gateway."
                else:
                    response = f"Backend Service Error: Received code {response_http.status_code} - {response_http.text}"
                    
            except Exception as e:
                st.error(f"An error occurred: {e}")
                response = "I'm having some trouble connecting to my systems right now. Please try again later."
        
        # Display the agent's response
        st.markdown(response)

    # 3. Add agent's response to the chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
