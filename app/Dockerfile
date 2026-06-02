FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app folder
COPY ./app /app/app
# Note: we don't copy local data/. Cloud Run will mount Cloud Storage for the DB.

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
