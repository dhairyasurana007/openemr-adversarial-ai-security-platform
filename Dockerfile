FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system agentforge && adduser --system --ingroup agentforge agentforge

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R agentforge:agentforge /app

USER agentforge
