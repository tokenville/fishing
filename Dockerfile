# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Faster, cleaner Python logs and no .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Run the bot (token is provided via Fly secret TELEGRAM_BOT_TOKEN)
CMD ["python", "main.py"]
