
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies with retries for temporary network timeouts.
# Keep this layer cached when requirements.txt has not changed.
RUN pip install --no-cache-dir \
    --retries 5 \
    --timeout 120 \
    -r requirements.txt \
    && pip install --no-cache-dir \
    --retries 5 \
    --timeout 120 \
    "psycopg[binary]" google-genai

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
