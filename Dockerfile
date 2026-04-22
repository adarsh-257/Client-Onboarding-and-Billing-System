FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for psycopg2 and WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libgdk-pixbuf2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
