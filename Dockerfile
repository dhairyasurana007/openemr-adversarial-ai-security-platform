FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
RUN addgroup --system agentforge && adduser --system --ingroup agentforge agentforge

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
RUN chown -R agentforge:agentforge /app

USER agentforge

CMD ["python", "start_server.py"]
