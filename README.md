# ThreadCraft

**An AI-powered custom clothing design and ordering web platform**, built as a final-year BSc (Hons) Software Engineering project (CL/BSCSD/33/79, ICBT Campus / Cardiff Metropolitan University).

Sri Lanka's domestic tailoring market is largely offline: customers visit tailors in person, communicate design ideas verbally, wait through several fitting sessions, and have no visibility into pricing or production status. ThreadCraft replaces that with a six-step guided web wizard — garment type → design tags & reference images → material & colour → measurements → itemised dynamic pricing → AI-generated mockup preview — backed by an admin dashboard for inventory, catalogue configuration, order fulfilment, and analytics.

> 📄 Full engineering plan: see [`docs/`](docs/) for the system design report, ERD, testing report, and architecture decision records.

## Live demo

| | URL |
|---|---|
| Frontend | _(added once deployed — Vercel)_ |
| API | _(added once deployed)_ |
| API docs (Swagger) | `<api-url>/docs` |
| ML models | _(added once published — Hugging Face)_ |

Demo credentials: `demo@threadcraft.lk` / see `docs/deployment/deployment-guide.md`.

## Monorepo layout

```
ThreadCraft/
├── frontend/     React 19 + Vite — customer wizard, dashboard, admin
├── backend/      FastAPI + SQLAlchemy + PostgreSQL
├── ml/           Kaggle training notebooks + Hugging Face model/Space source
├── docs/         Architecture, ERD, ADRs, testing & UAT reports
└── scripts/      Dev + tooling helper scripts
```

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, hand-written CSS design system |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL |
| AI mockups | Hosted diffusion inference (prompt-engineering pipeline over garment attributes) |
| ML | Garment attribute classifier + size/fit recommender, trained on Kaggle, published to Hugging Face |
| Payments | Stripe (test mode) |
| Email | Transactional email API |
| Deployment | Vercel (frontend) · free-tier host (API) · free-tier Postgres · Hugging Face (models) |

See `docs/architecture/adr/` for the reasoning behind each deviation from the original proposal (e.g. PostgreSQL over MySQL, FastAPI-based admin over Django admin).

## Local development

**Backend**
```bash
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # fill in DATABASE_URL etc.
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env.development
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so no CORS setup is needed locally.

## Testing

```bash
cd backend && pytest -q --cov=app
cd frontend && npm run lint && npm run build
```

## Project status

This repository is under active development as part of a graded academic submission. See open [issues](../../issues) and [pull requests](../../pulls) for current progress, and `docs/dissertation/evidence-index.md` for a requirement → PR → evidence trace.

## License

MIT — see [LICENSE](LICENSE). Academic project; not for commercial deployment as-is (test-mode payments, seeded demo data).
