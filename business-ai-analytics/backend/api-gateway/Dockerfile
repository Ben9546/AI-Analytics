# Stage 1: Build stage - Install dependencies
FROM python:3.9-slim AS builder

WORKDIR /app

# Install poetry (or pip if using requirements.txt)
# Using pip for simplicity here, assuming a requirements.txt will be generated
# RUN pip install poetry
# COPY poetry.lock pyproject.toml ./
# RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

# For pip with requirements.txt:
COPY ./requirements.txt .
# Ensure httpx is in requirements.txt for this service
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage - Copy application code and installed dependencies
FROM python:3.9-slim

WORKDIR /app

# Copy installed dependencies from builder stage
# If using poetry:
# COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
# COPY --from=builder /app /app
# If using pip:
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /app/requirements.txt . # For reference, though packages are already installed

# Copy the application code
# Assuming the Dockerfile is in backend/api-gateway/ and main.py is in the same directory
COPY ./main.py .
# If there are other modules in this service, copy them too e.g.
# COPY ./app/ /app/

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# Ensure the main:app path matches your file structure if it's nested deeper
# For example, if main.py is inside an 'app' subdirectory of api-gateway, it would be app.main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
