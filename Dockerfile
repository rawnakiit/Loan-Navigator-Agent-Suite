# Use a lightweight, official Python runtime
FROM python:3.11-slim

# Set system environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set the working directory inside the container
WORKDIR /workspace

# Install system dependencies (rarely needed, but good practice)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# 1. Copy only the requirements file to leverage Docker's layer caching
# This path is correct because your file is at `app/requirements.txt`
COPY app/requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 2. Copy all your application code and data
# This copies the `app` folder (with all its .py files) into the container
COPY app/ /workspace/app/

# Expose the port Cloud Run will listen on
EXPOSE 8080

# The command to run your FastAPI API service
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
