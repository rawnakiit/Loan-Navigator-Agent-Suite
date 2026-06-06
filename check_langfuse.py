import os
import logging
from dotenv import load_dotenv, find_dotenv
from langfuse.langchain import CallbackHandler
from app.utils.llm import get_llm

logging.basicConfig(level=logging.INFO)

# 1. Load environment variables
env_path = find_dotenv("app/.env")
if env_path:
    load_dotenv(env_path)
else:
    load_dotenv()

print("=== LANGFUSE CONNECTIVITY DIAGNOSTICS ===")
print("LANGFUSE_PUBLIC_KEY :", os.getenv("LANGFUSE_PUBLIC_KEY", "❌ Missing"))
secret_key = os.getenv("LANGFUSE_SECRET_KEY")
print("LANGFUSE_SECRET_KEY :", f"✅ Present ({secret_key[:8]}...)" if secret_key else "❌ Missing")
print("LANGFUSE_HOST       :", os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com (Default)"))

if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
    print("\n❌ Error: Langfuse environment variables are missing from your app/.env file!")
    exit(1)

print("\n2. Initializing Langfuse Callback Handler...")
try:
    handler = CallbackHandler()
    print("✅ CallbackHandler initialized cleanly!")
    
    print("\n3. Sending a test message through Gemini to verify connection...")
    llm = get_llm()
    llm.invoke("Hello, this is a connectivity check.", config={"callbacks": [handler], "run_name": "Diagnostics-Connection-Test"})
    
    print("\n🎉 SUCCESS! The trace was successfully sent. Verify 'Diagnostics-Connection-Test' is visible in your Langfuse dashboard.")
    
except Exception as e:
    print("\n❌ Connectivity Failed! Exception encountered during tracing operations:")
    print(str(e))