FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything
COPY . .

# Railway sets PORT automatically, but we define a default fallback
ENV PORT=8000

# ✅ Use sh -c so ${PORT} gets expanded properly
CMD ["sh", "-c", "uvicorn gateway.app.main:app --host 0.0.0.0 --port ${PORT}"]
