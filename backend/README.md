# ThreadCraft — Backend

FastAPI + SQLAlchemy 2.0 + PostgreSQL (SQLite for local dev/tests).

## Develop

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m app.db.seed        # admin@threadcraft.lk / demo@threadcraft.lk — see .env.example
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

## Test

```bash
pytest -q --cov=app --cov-report=term-missing
ruff check .
ruff format --check .
```

## Structure

```
app/
├── main.py           # app factory: CORS, router registration
├── core/             # settings, JWT/bcrypt, auth dependencies
├── db/                # engine/session, declarative base, seed script
├── models/            # SQLAlchemy models
├── schemas/           # Pydantic request/response models
├── services/           # business logic — pricing and prompt-building are
│                        # pure functions with no DB/HTTP dependency
└── routers/            # one file per resource, admin/ for admin-only routes
```

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```
