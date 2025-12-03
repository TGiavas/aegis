# Aegis: Real-Time Event Monitoring & Alerting Platform

Design document to implement a small but realistic backend system that demonstrates:

- Python + FastAPI backend proficiency  
- REST APIs and simple microservice separation  
- SQL database modeling and access  
- Basic auth/security  
- Real-time-ish event ingestion and alerting logic  
- Docker-based local deployment
- Message queue integration (RabbitMQ)

Use this as the spec for implementation.

---

## 1. High-Level Overview

### 1.1 Goal

Build a **backend-only** platform that:

- Ingests "events" from external systems (simulated).
- Stores events in a relational DB.
- Applies simple rules to detect anomalies (error spikes, high latency).
- Creates alerts when rules are triggered.
- Exposes REST APIs to:
  - Manage users and projects.
  - Ingest events.
  - View events and alerts.

Split into **three services**:

1. **API Service** (`api_service`):
   - User auth (JWT).
   - CRUD for projects and API keys.
   - Read-only access for events and alerts.

2. **Ingestion Service** (`ingestion_service`):
   - HTTP endpoint to receive events.
   - Validate payload & authenticate via project API key.
   - Publish events to message queue.

3. **Analytics Service** (`analytics_service`):
   - Consume events from message queue.
   - Persist events to DB.
   - Apply rules & create alerts.

All services talk to the same PostgreSQL instance. Ingestion and Analytics communicate via RabbitMQ.

---

## 2. Technology Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **DB Layer:** SQLAlchemy (ORM) + Alembic
- **Database:** PostgreSQL
- **Message Broker:** RabbitMQ
- **Auth:** JWT (access token) + API keys (ingestion)
- **Containerization:** Docker + docker-compose
- **Testing:** pytest
- **Config:** `.env` + Pydantic settings
- **Lint/Format:** ruff, black

Requirements:

- Type hints everywhere.
- Pydantic models for request/response.
- Dependency injection with `Depends`.
- All timestamps stored in **UTC**.
- JSON structured logging with correlation IDs.

---

## 3. System Architecture

### 3.1 Services

#### 3.1.1 `api_service`

Responsibilities:

- User management:
  - Register user.
  - Login, issue JWT.
- Project management:
  - Create/List/Get projects.
- API key management:
  - Create/List/Revoke API keys for projects.
- Read-only queries:
  - List/query events.
  - List/query alerts.
- Auth protection using JWT.
- Health check endpoint.

Listens on port `8000`.

Base URL: `http://localhost:8000/api/v1`

#### 3.1.2 `ingestion_service`

Responsibilities:

- Expose `POST /ingest/events` to receive events.
- Expose `POST /ingest/events/batch` for bulk ingestion.
- Validate payload with Pydantic.
- Authenticate requests via `X-API-Key` header.
- Publish validated events to RabbitMQ queue.
- Health check endpoint.

Listens on port `8001`.

Base URL: `http://localhost:8001/api/v1`

#### 3.1.3 `analytics_service`

Responsibilities:

- Consume events from RabbitMQ queue `events.raw`.
- Persist events to DB.
- Run rule checks after insert:
  - Error spike rule (with deduplication).
  - High latency rule.
- Insert alerts into DB when rules trigger.
- Health check endpoint.

Listens on port `8002` (for health checks only).

### 3.2 Message Flow

```
Client → ingestion_service → RabbitMQ (events.raw) → analytics_service → PostgreSQL
                                                                              ↓
                                                     api_service ← reads ← events/alerts
```

---

## 4. Domain Model (PostgreSQL)

Use a single schema. Integer PKs for simplicity. All timestamps are `timestamptz` stored in UTC.

### 4.1 Tables

#### 4.1.1 `users`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | serial | PK |
| `email` | varchar(255) | UNIQUE, NOT NULL |
| `password_hash` | varchar(255) | NOT NULL |
| `role` | varchar(20) | NOT NULL, DEFAULT `'USER'` |
| `created_at` | timestamptz | NOT NULL, DEFAULT `now()` |

Role enum values: `"ADMIN"`, `"USER"`

#### 4.1.2 `projects`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | serial | PK |
| `name` | varchar(100) | UNIQUE, NOT NULL |
| `description` | text | NULLABLE |
| `owner_id` | integer | FK → `users.id`, NOT NULL |
| `created_at` | timestamptz | NOT NULL, DEFAULT `now()` |

#### 4.1.3 `api_keys`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | serial | PK |
| `project_id` | integer | FK → `projects.id`, NOT NULL |
| `key_hash` | varchar(255) | NOT NULL |
| `key_prefix` | varchar(8) | NOT NULL |
| `name` | varchar(100) | NOT NULL |
| `created_at` | timestamptz | NOT NULL, DEFAULT `now()` |
| `revoked_at` | timestamptz | NULLABLE |

Notes:
- `key_prefix` stores the first 8 chars of the key for identification (e.g., `aegis_ab`).
- Full key is shown only once at creation time.
- Keys are hashed with bcrypt before storage.

Indexes:
- `(key_hash)` — for lookup during authentication

#### 4.1.4 `events`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | serial | PK |
| `project_id` | integer | FK → `projects.id`, NOT NULL |
| `source` | varchar(100) | NOT NULL |
| `event_type` | varchar(50) | NOT NULL |
| `severity` | varchar(20) | NOT NULL |
| `latency_ms` | integer | NULLABLE |
| `payload` | jsonb | NOT NULL, DEFAULT `'{}'` |
| `created_at` | timestamptz | NOT NULL, DEFAULT `now()` |

Severity enum values: `"INFO"`, `"WARN"`, `"ERROR"`

Event type examples: `"METRIC"`, `"LOG"`, `"TRACE"`

Indexes:
- `(project_id, created_at)`
- `(project_id, severity, created_at)`

#### 4.1.5 `alerts`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | serial | PK |
| `project_id` | integer | FK → `projects.id`, NOT NULL |
| `rule_name` | varchar(50) | NOT NULL |
| `message` | text | NOT NULL |
| `level` | varchar(20) | NOT NULL |
| `created_at` | timestamptz | NOT NULL, DEFAULT `now()` |
| `resolved_at` | timestamptz | NULLABLE |

Level enum values: `"LOW"`, `"MEDIUM"`, `"HIGH"`

Rule names: `"error_spike"`, `"high_latency"`

Indexes:
- `(project_id, created_at)`
- `(project_id, resolved_at)` — for filtering open alerts
- `(project_id, rule_name, resolved_at)` — for duplicate alert checks

---

## 5. REST API Design – `api_service`

Base URL: `http://localhost:8000/api/v1`

Use Swagger/OpenAPI (FastAPI default) at `/docs`.

### 5.1 Standard Error Response

All error responses follow this format:

```json
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE",
  "field_errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

Common error codes:
- `VALIDATION_ERROR` — request validation failed
- `UNAUTHORIZED` — missing or invalid credentials
- `FORBIDDEN` — insufficient permissions
- `NOT_FOUND` — resource not found
- `CONFLICT` — resource already exists

### 5.2 Health Check

#### `GET /health`

No authentication required.

Response:
```json
{
  "status": "healthy",
  "service": "api_service",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### 5.3 Auth

#### `POST /auth/register`

- Body:
  - `email: str`
  - `password: str` (min 8 chars)
- Behavior:
  - Create user with hashed password.
- Response:
  - User info: `id`, `email`, `role`, `created_at`.
- Errors:
  - `409 Conflict` if email already exists.

#### `POST /auth/login`

- Body:
  - `email: str`
  - `password: str`
- Behavior:
  - Validate credentials.
  - Issue JWT (HS256).
- Response:
  - `{ "access_token": "<jwt>", "token_type": "bearer" }`
- Errors:
  - `401 Unauthorized` if credentials invalid.

JWT used via `Authorization: Bearer <token>`.

### 5.4 Projects

All endpoints below require valid JWT.

#### `GET /projects`

- Query:
  - `owner_only: bool = false` (optional)
- Behavior:
  - If `owner_only=true`: return only projects where `owner_id` = current user.
  - If `owner_only=false`: return all projects accessible to user (MVP: same as owner_only=true).
- Response:
  - List of project objects.

#### `POST /projects`

- Body:
  - `name: str`
  - `description: Optional[str]`
- Behavior:
  - Create project; `owner_id` = current user.
- Response:
  - Created project object.
- Errors:
  - `409 Conflict` if name already exists.

#### `GET /projects/{project_id}`

- Behavior:
  - Return project if current user is owner.
- Response:
  - Project object.
- Errors:
  - `404 Not Found` if project doesn't exist or user is not owner.

### 5.5 API Keys

All endpoints require valid JWT. User must be project owner.

#### `GET /projects/{project_id}/api-keys`

- Behavior:
  - List all API keys for the project (excluding revoked).
- Response:
  - List of key objects: `id`, `name`, `key_prefix`, `created_at`.

#### `POST /projects/{project_id}/api-keys`

- Body:
  - `name: str` (e.g., "production-sensor")
- Behavior:
  - Generate a new API key (format: `aegis_<32-char-random>`).
  - Store hash in DB.
- Response:
  - `{ "id": 1, "name": "...", "key": "aegis_abc123...", "created_at": "..." }`
- Note: The full `key` is returned **only once** at creation.

#### `DELETE /projects/{project_id}/api-keys/{key_id}`

- Behavior:
  - Set `revoked_at = now()` for the key.
- Response:
  - `204 No Content`

### 5.6 Events (read-only)

#### `GET /events`

- Query params:
  - `project_id: int` (required)
  - `severity: Optional[str]`
  - `event_type: Optional[str]`
  - `source: Optional[str]`
  - `from_ts: Optional[datetime]`
  - `to_ts: Optional[datetime]`
  - `limit: int = 50` (max 100)
  - `offset: int = 0`
- Behavior:
  - Verify user owns the project.
  - Return filtered, paginated events.
- Response:
  - `{ "items": [...], "total": int, "limit": int, "offset": int }`

### 5.7 Alerts

#### `GET /alerts`

- Query params:
  - `project_id: int` (required)
  - `only_open: bool = false`
  - `level: Optional[str]`
  - `rule_name: Optional[str]`
  - `limit: int = 50` (max 100)
  - `offset: int = 0`
- Behavior:
  - Verify user owns the project.
  - If `only_open=true`, select alerts where `resolved_at IS NULL`.
- Response:
  - `{ "items": [...], "total": int, "limit": int, "offset": int }`

#### `POST /alerts/{alert_id}/resolve`

- Behavior:
  - Verify user owns the project associated with the alert.
  - Set `resolved_at = now()` for alert.
- Response:
  - Updated alert object.
- Errors:
  - `404 Not Found` if alert doesn't exist or user doesn't own the project.
  - `409 Conflict` if alert already resolved.

---

## 6. REST API Design – `ingestion_service`

Base URL: `http://localhost:8001/api/v1`

### 6.1 Authentication

All ingestion endpoints require an `X-API-Key` header:

```
X-API-Key: aegis_abc123def456...
```

The service:
1. Hashes the provided key.
2. Looks up the hash in `api_keys` table.
3. Verifies `revoked_at IS NULL`.
4. Extracts `project_id` from the key record.

### 6.2 Rate Limiting

Rate limits are applied per API key:

- **Single event endpoint:** 100 requests/second
- **Batch endpoint:** 10 requests/second (max 100 events per batch)

Rate limit headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704110400
```

### 6.3 Health Check

#### `GET /health`

No authentication required.

Response:
```json
{
  "status": "healthy",
  "service": "ingestion_service",
  "timestamp": "2025-01-01T12:00:00Z",
  "rabbitmq": "connected"
}
```

### 6.4 Event Ingestion

#### `POST /ingest/events`

- Headers:
  - `X-API-Key: <api_key>` (required)
- Body (JSON):

```json
{
  "source": "sensor-1",
  "event_type": "METRIC",
  "severity": "ERROR",
  "latency_ms": 1200,
  "payload": {
    "cpu": 0.85,
    "memory": 0.9
  }
}
```

Note: `project_id` is derived from the API key, not provided in the body.

- Behavior:
  1. Validate the request body using Pydantic schema.
  2. Authenticate via `X-API-Key` header.
  3. Publish message to RabbitMQ queue `events.raw`.
- Response:
  - `202 Accepted`
  - `{ "status": "accepted", "message_id": "<uuid>" }`

#### `POST /ingest/events/batch`

- Headers:
  - `X-API-Key: <api_key>` (required)
- Body (JSON):

```json
{
  "events": [
    {
      "source": "sensor-1",
      "event_type": "METRIC",
      "severity": "INFO",
      "latency_ms": 50,
      "payload": {}
    },
    {
      "source": "sensor-2",
      "event_type": "LOG",
      "severity": "ERROR",
      "latency_ms": null,
      "payload": {"message": "Connection failed"}
    }
  ]
}
```

- Constraints:
  - Maximum 100 events per batch.
- Behavior:
  - Validate all events.
  - Publish each as a separate message to RabbitMQ.
- Response:
  - `202 Accepted`
  - `{ "status": "accepted", "count": 2, "message_ids": ["<uuid>", "<uuid>"] }`
- Errors:
  - `422 Unprocessable Entity` if any event fails validation (entire batch rejected).

---

## 7. Message Queue Schema

### 7.1 Queue Configuration

- **Queue name:** `events.raw`
- **Exchange:** `aegis.events` (direct exchange)
- **Routing key:** `raw`
- **Message persistence:** enabled

### 7.2 Message Schema

```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": 1,
  "source": "sensor-1",
  "event_type": "METRIC",
  "severity": "ERROR",
  "latency_ms": 1200,
  "payload": {
    "cpu": 0.85,
    "memory": 0.9
  },
  "ingested_at": "2025-01-01T12:00:00Z"
}
```

---

## 8. Rule Logic

All rule logic is implemented inside the `analytics_service` in the `rules/` module.

Rules run **synchronously** after each event insertion.

### 8.1 Error Spike Rule

**Description:**

Triggers when a project receives **5 or more ERROR severity events** in the past **5 minutes**.

**Algorithm:**

1. Only evaluate when the new event has `severity = 'ERROR'`.
2. Query:
   ```sql
   SELECT COUNT(*)
   FROM events
   WHERE project_id = :project_id
     AND severity = 'ERROR'
     AND created_at >= now() - interval '5 minutes';
   ```
3. If the count ≥ 5:
   - **Check for duplicate:** Query for an existing unresolved alert:
     ```sql
     SELECT id FROM alerts
     WHERE project_id = :project_id
       AND rule_name = 'error_spike'
       AND resolved_at IS NULL
       AND created_at >= now() - interval '5 minutes';
     ```
   - If no such alert exists, create a new alert with:
     - `rule_name = "error_spike"`
     - `level = "HIGH"`
     - `message = "High error rate detected: {count} errors in the last 5 minutes."`

### 8.2 High Latency Rule

**Description:**

Triggers when an event has a latency above **1000 ms**.

**Algorithm:**

1. If `latency_ms` is not null and > 1000:
   - Insert alert:
     - `rule_name = "high_latency"`
     - `level = "MEDIUM"`
     - `message = "High latency event detected: {latency_ms} ms from source '{source}'."`

---

## 9. Project Structure

A single mono-repo with explicitly separated services. Shared code is duplicated across services with a note to keep in sync (acceptable for MVP; a shared package can be extracted later).

```
aegis/
├── docker-compose.yml
├── README.md
├── .env.example
│
├── services/
│   ├── api_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       └── 001_initial.py
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes_auth.py
│   │   │   │   ├── routes_projects.py
│   │   │   │   ├── routes_api_keys.py
│   │   │   │   ├── routes_events.py
│   │   │   │   ├── routes_alerts.py
│   │   │   │   └── routes_health.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   ├── db.py
│   │   │   │   ├── dependencies.py
│   │   │   │   └── logging.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── project.py
│   │   │   │   ├── api_key.py
│   │   │   │   ├── event.py
│   │   │   │   └── alert.py
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── user.py
│   │   │       ├── project.py
│   │   │       ├── api_key.py
│   │   │       ├── event.py
│   │   │       ├── alert.py
│   │   │       └── common.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── test_auth.py
│   │       ├── test_projects.py
│   │       ├── test_api_keys.py
│   │       └── test_events_alerts.py
│   │
│   ├── ingestion_service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes_ingest.py
│   │   │   │   └── routes_health.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py
│   │   │   │   ├── db.py
│   │   │   │   ├── rabbitmq.py
│   │   │   │   ├── rate_limit.py
│   │   │   │   └── logging.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── project.py
│   │   │   │   └── api_key.py
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       └── ingest.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       └── test_ingest.py
│   │
│   └── analytics_service/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── .env.example
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── consumer.py
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   └── routes_health.py
│       │   ├── core/
│       │   │   ├── __init__.py
│       │   │   ├── config.py
│       │   │   ├── db.py
│       │   │   ├── rabbitmq.py
│       │   │   └── logging.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── project.py
│       │   │   ├── event.py
│       │   │   └── alert.py
│       │   ├── schemas/
│       │   │   ├── __init__.py
│       │   │   └── message.py
│       │   └── rules/
│       │       ├── __init__.py
│       │       ├── base.py
│       │       ├── error_spike.py
│       │       └── high_latency.py
│       └── tests/
│           ├── __init__.py
│           ├── conftest.py
│           ├── test_consumer.py
│           └── test_rules.py
│
└── scripts/
    ├── simulate_events.py
    └── seed_data.py
```

---

## 10. Configuration

All services load configuration via Pydantic `BaseSettings`.

### 10.1 Shared Environment Variables

```bash
# Database
DATABASE_URL=postgresql+psycopg://aegis:aegis@db:5432/aegis

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 10.2 API Service Specific

```bash
# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS (comma-separated origins, or * for all)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Database pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

### 10.3 Ingestion Service Specific

```bash
# Rate limiting
RATE_LIMIT_SINGLE=100
RATE_LIMIT_BATCH=10
```

### 10.4 Analytics Service Specific

```bash
# Consumer
CONSUMER_PREFETCH_COUNT=10
```

---

## 11. Docker & docker-compose

### 11.1 Services

The `docker-compose.yml` declares:

- **db**
  - PostgreSQL 16
  - Persistent volume
  - Port `5432` (internal)

- **rabbitmq**
  - RabbitMQ 3 with management plugin
  - Persistent volume
  - Ports: `5672` (AMQP), `15672` (management UI)

- **api_service**
  - Build from `services/api_service/Dockerfile`
  - Depends on `db`
  - Port `8000`
  - Health check configured

- **ingestion_service**
  - Build from `services/ingestion_service/Dockerfile`
  - Depends on `db`, `rabbitmq`
  - Port `8001`
  - Health check configured

- **analytics_service**
  - Build from `services/analytics_service/Dockerfile`
  - Depends on `db`, `rabbitmq`
  - Port `8002` (health check only)
  - Health check configured

### 11.2 Usage

```bash
# Start all services
docker compose up --build

# Run migrations (first time or after model changes)
docker compose exec api_service alembic upgrade head

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### 11.3 Service URLs

| Service | URL |
|---------|-----|
| API Docs | http://localhost:8000/docs |
| Ingestion Docs | http://localhost:8001/docs |
| RabbitMQ Management | http://localhost:15672 |

---

## 12. Testing

Use pytest across all services. Each service has its own test suite.

### 12.1 API Service Tests

- **Auth:**
  - Register user → success, returns user info.
  - Register same email twice → `409 Conflict`.
  - Login with valid credentials → JWT returned.
  - Login with invalid credentials → `401 Unauthorized`.

- **Projects:**
  - Create project → OK when authorized.
  - Create project with duplicate name → `409 Conflict`.
  - List projects → returns user's projects.
  - Get project → returns project if owner.
  - Get project → `404` if not owner.

- **API Keys:**
  - Create API key → returns full key once.
  - List API keys → returns keys without full key.
  - Revoke API key → key no longer works.

- **Events:**
  - Query with valid project → returns events.
  - Query with invalid project → `404`.
  - Pagination works correctly.
  - Filters (severity, date range) apply correctly.

- **Alerts:**
  - Query alerts → returns alerts.
  - `only_open=true` → returns only unresolved.
  - Resolve alert → sets `resolved_at`.
  - Resolve already resolved → `409 Conflict`.

### 12.2 Ingestion Service Tests

- **Authentication:**
  - Valid API key → accepted.
  - Invalid API key → `401 Unauthorized`.
  - Revoked API key → `401 Unauthorized`.
  - Missing API key → `401 Unauthorized`.

- **Single Event:**
  - Valid payload → `202 Accepted`, message published.
  - Invalid payload → `422 Unprocessable Entity`.
  - Missing required fields → `422`.

- **Batch Events:**
  - Valid batch → `202 Accepted`, all messages published.
  - One invalid event → entire batch rejected with `422`.
  - Batch exceeds 100 events → `422`.

### 12.3 Analytics Service Tests

- **Consumer:**
  - Valid message → event inserted into DB.
  - Invalid message → logged and skipped (no crash).

- **Error Spike Rule:**
  - Insert 5 ERROR events in 5 minutes → HIGH alert created.
  - Insert 6th ERROR event → no duplicate alert created.
  - Resolve alert, then 5 more errors → new alert created.

- **High Latency Rule:**
  - Event with `latency_ms > 1000` → MEDIUM alert created.
  - Event with `latency_ms = 1000` → no alert.
  - Event with `latency_ms = null` → no alert.

---

## 13. Implementation Order

1. Set up project structure and Docker configuration.
2. Implement shared DB models (users, projects, api_keys, events, alerts).
3. Add Alembic migrations in `api_service`.
4. Implement `api_service`:
   - Health check
   - Auth (register/login)
   - Projects CRUD
   - API keys management
   - Events listing
   - Alerts listing + resolve
5. Implement `ingestion_service`:
   - Health check
   - API key authentication
   - Single event ingestion (publish to RabbitMQ)
   - Batch event ingestion
   - Rate limiting
6. Implement `analytics_service`:
   - Health check
   - RabbitMQ consumer
   - Event persistence
   - Rule engine with deduplication
7. Create event simulator script.
8. Write tests for all services.
9. Add README with setup and usage instructions.

---

## 14. Deliverables Checklist

- [ ] `docker-compose.yml`
- [ ] `.env.example` files for all services
- [ ] `api_service` with:
  - [ ] FastAPI app with health check
  - [ ] Auth (register/login with JWT)
  - [ ] Projects CRUD
  - [ ] API keys management
  - [ ] Events listing with filters
  - [ ] Alerts listing + resolve
  - [ ] Alembic migrations
  - [ ] Tests
- [ ] `ingestion_service` with:
  - [ ] FastAPI app with health check
  - [ ] API key authentication
  - [ ] Single event ingestion
  - [ ] Batch event ingestion
  - [ ] RabbitMQ publisher
  - [ ] Rate limiting
  - [ ] Tests
- [ ] `analytics_service` with:
  - [ ] RabbitMQ consumer
  - [ ] Event persistence
  - [ ] Rule engine (error_spike, high_latency)
  - [ ] Duplicate alert prevention
  - [ ] Tests
- [ ] Shared DB schema (PostgreSQL)
- [ ] RabbitMQ configuration
- [ ] `simulate_events.py` script
- [ ] Complete `README.md` with:
  - [ ] Project overview
  - [ ] Setup instructions
  - [ ] API documentation links
  - [ ] Example usage

---

## 15. Future Enhancements (Out of Scope)

These items are explicitly out of scope for the MVP but noted for potential future work:

- **Shared project access:** Allow multiple users to access a project.
- **Soft deletes:** Add `deleted_at` columns for audit trails.
- **Event deduplication:** Prevent duplicate events based on content hash.
- **More alert rules:** Custom rules, configurable thresholds.
- **Notifications:** Email/Slack/webhook notifications for alerts.
- **Metrics & dashboards:** Prometheus metrics, Grafana dashboards.
- **API rate limiting by tier:** Different limits for different subscription tiers.
- **Event replay:** Ability to replay events from a specific point in time.
- **Shared code package:** Extract common models/utilities to a shared package.
