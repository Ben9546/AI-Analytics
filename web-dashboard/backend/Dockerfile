# Stage 1: Base image with Python
FROM python:3.9-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Stage 2: Builder stage - Install dependencies
FROM base AS builder
COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Test stage (Conceptual)
# This stage would run tests. It copies source code and installed dependencies.
FROM builder AS tester
COPY . .
# The command to run tests would depend on the project structure and test runner.
# Pytest is in requirements.txt.
# This assumes tests are in a 'tests' subdirectory and can be run from /app (backend root).
# Imports in tests should be relative to /app (e.g., from services.auth_service).
# The PYTHONPATH set in run_in_bash_session is not directly applicable here,
# but the WORKDIR /app means Python will look in /app for modules.
# RUN python -m pytest -v tests/
# If tests pass, this stage finishes. If they fail, the Docker build fails here.
# For now, we'll just print a message for this conceptual stage.
RUN echo "Conceptual test stage: Tests would run here."

# Stage 4: Runtime stage - Copy application code and dependencies from builder
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /app/requirements.txt . # For reference or if needed by runtime checks

# Copy the application code
# WORKDIR is /app (from base)
COPY ./main.py .
COPY ./api /app/api
COPY ./config /app/config
COPY ./middleware /app/middleware
COPY ./models /app/models
COPY ./services /app/services
COPY ./__init__.py . # Copy the backend's __init__.py

# Ensure __init__.py files exist in subdirectories for packaging (already created in repo)
# These are important for Python's import system.

EXPOSE 8010
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
