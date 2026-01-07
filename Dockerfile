FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and entry points
COPY src/ ./src/
COPY worker.py .
COPY skills/ ./skills/

# Run the worker
CMD ["python", "-u", "worker.py"]
