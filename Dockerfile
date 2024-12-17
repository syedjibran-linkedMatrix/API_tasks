FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY api_task ./api_task
COPY myapp ./myapp

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
