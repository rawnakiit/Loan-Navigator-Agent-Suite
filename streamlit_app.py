import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv

# --- CRITICAL: Load environment variables at the very top ---
# This ensures all API keys and configurations are available to the agents.
env_path = find_dotenv(filename="app/.env")
if env_path:
    load_dotenv(env_path)
else:
    # If the .env file is in the root, find_dotenv() without args might work
    load_dotenv(find_dotenv())

# Now that environment is set, we can import our application logic
from app.supervisor import run_supervisor

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
                # Call the main supervisor function with the user's query
                result = run_supervisor(prompt)
                
                # The final, user-friendly response is in the 'final_response' key
                response = result.get("final_response", "Sorry, I encountered an error and couldn't process your request.")
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
                response = "I'm having some trouble connecting to my systems right now. Please try again later."
        
        # Display the agent's response
        st.markdown(response)

    # 3. Add agent's response to the chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

