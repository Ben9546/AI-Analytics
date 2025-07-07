# Stage 1: Base image with Python
FROM python:3.9-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Stage 2: Builder stage - Install dependencies
FROM base AS builder
COPY ./requirements.txt .
# Ensure requirements.txt exists in api-service/ with relevant dependencies:
# fastapi, uvicorn[standard], pydantic, pydantic-settings, python-jose[cryptography], passlib[bcrypt], pytest, httpx
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Test stage (Conceptual)
FROM builder AS tester
COPY . .
# This assumes tests are in a 'tests' subdirectory and can be run from /app (api-service root).
# Imports in tests should be relative to /app (e.g., from endpoints.data_ingestion).
# The WORKDIR /app means Python will look in /app for modules.
# RUN python -m pytest -v tests/
RUN echo "Conceptual test stage for api-service: Tests would run here."

# Stage 4: Runtime stage - Copy application code and dependencies from builder
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /app/requirements.txt .

# Copy the application code
COPY ./main.py .
COPY ./endpoints /app/endpoints
COPY ./models /app/models       # If models directory is used
COPY ./middleware /app/middleware # If middleware directory is used
COPY ./__init__.py . # Copy the api-service's __init__.py

# Ensure __init__.py files exist in subdirectories for packaging (already created in repo)

# Standard port for this API service (e.g., 8020 as used in conceptual run commands)
EXPOSE 8020
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8020"]
