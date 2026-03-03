# This file has been modified with the assistance of Bob

# Use minimal Python base image
FROM python:3.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c

# Set work directory
WORKDIR /app

# Install dependencies from requirements.txt
COPY auth/agent-oauth-secret/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common utilities from unified context
COPY common/ ./common/

# Copy the script
COPY auth/agent-oauth-secret/agent_oauth_secret.py .

# Create non-root user for runtime security
RUN useradd -u 1001 -m appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER 1001

# Run the agent OAuth setup
CMD ["python", "agent_oauth_secret.py"]