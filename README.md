# Aegis: Real-Time Event Monitoring & Alerting Platform

A backend platform for ingesting events, detecting anomalies, and creating alerts.

## Architecture

- **API Service** (port 8000) - User auth, project management, event/alert queries
- **Ingestion Service** (port 8001) - Receives events, publishes to message queue
- **Analytics Service** (port 8002) - Consumes events, runs alert rules

## Tech Stack

- Python 3.12 + FastAPI
- PostgreSQL 18
- RabbitMQ
- Docker + Docker Compose

## Project Status

🚧 **Under Development**

## Quick Start

```bash
# Start all services
docker compose up --build

# Run database migrations (after first start)
docker compose exec api_service alembic upgrade head
```

## Services

| Service | URL |
|---------|-----|
| API Docs | http://localhost:8000/docs |
| Ingestion Docs | http://localhost:8001/docs |
| RabbitMQ Management | http://localhost:15672 |

## Documentation

See [SPEC.md](./SPEC.md) for the full technical specification.

