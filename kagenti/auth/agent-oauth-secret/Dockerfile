# Use minimal Python base image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy your script
COPY agent_oauth_secret.py .

# Add a non-root user and switch to it
RUN useradd -m -u 1001 appuser
USER appuser
CMD ["python", "agent_oauth_secret.py"]