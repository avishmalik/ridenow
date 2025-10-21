FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project (for Docker build caching)
COPY . .

# Default command, overridden in docker-compose
CMD ["uvicorn", "gateway.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
