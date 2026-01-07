FROM python:3.11-slim

WORKDIR /app

COPY requirements-listener.txt .
RUN pip install --no-cache-dir -r requirements-listener.txt

COPY slack_listener.py .

CMD ["python", "-u", "slack_listener.py"]

