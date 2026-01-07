FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-listener.txt .
RUN pip install --no-cache-dir -r requirements-listener.txt

# Copy worker code
COPY agent_worker.py .

# Run the worker
CMD ["python", "-u", "agent_worker.py"]
