# Use minimal Python base image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy your script
COPY keycloak_client.py .

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "keycloak_client.py"]