# Deployment guide

Deploys ThreadCraft entirely on free tiers. Budget **45–60 minutes** the first time.

| Piece | Service | Why |
|---|---|---|
| Frontend | **Vercel** Hobby | Free, PR previews, auto-deploy from GitHub |
| API | **Render** free web service | The only genuinely free, no-card FastAPI host left |
| Database | **Neon** free Postgres | **Never expires**, no card, sub-second wake |
| Models | **Hugging Face Hub** | Already published |
| Mockups | **Cloudflare Workers AI** (optional) | 10k free neurons/day |

> **Do this in order.** The API needs the database URL, and the frontend needs the API URL.

---

## 1. Database — Neon (~5 min)

1. Sign up at <https://neon.tech> (GitHub login, no card)
2. **Create project** — name `threadcraft`, region closest to you (Singapore for Sri Lanka)
3. On the dashboard, copy the **Pooled connection** string. It looks like:
   ```
   postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
   ```

**You must change the scheme.** SQLAlchemy needs the driver named:

```
postgresql://…       ->  postgresql+psycopg2://…
```

So the value you'll paste into Render is:

```
postgresql+psycopg2://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
```

Use the **pooled** endpoint (the one with `-pooler`), not the direct one — Render's free instance opens and drops connections as it sleeps and wakes.

> Neon's free plan does not expire. Avoid Render's own free Postgres: it is **hard-deleted 44 days after creation**, regardless of use.

---

## 2. API — Render (~20 min)

1. Sign up at <https://render.com> with GitHub
2. **New → Blueprint**, pick the `threadcraft` repo. Render reads `render.yaml` from the
   repository root and leaves **Blueprint Path** blank.
3. Fill in the env vars it prompts for:

| Variable | Value |
|---|---|
| `DATABASE_URL` | the `postgresql+psycopg2://…` string from step 1 |
| `CORS_ORIGINS` | `https://threadcraft.vercel.app` — update to your real Vercel URL after step 3 |
| `CORS_ORIGIN_REGEX` | `https://threadcraft-.*\.vercel\.app` (allows preview deploys) |
| `ADMIN_EMAIL` | your admin login |
| `ADMIN_PASSWORD` | a real password — this seeds the admin account |
| `DEMO_PASSWORD` | password for the demo customer you'll show in the viva |
| `JWT_SECRET` | leave it — Render generates one |

Optional, for real AI mockups instead of the placeholder:

| Variable | Where from |
|---|---|
| `CF_ACCOUNT_ID` | Cloudflare dashboard → right sidebar |
| `CF_API_TOKEN` | Cloudflare → My Profile → API Tokens → **Workers AI** template |
| `HF_TOKEN` | huggingface.co → Settings → Access Tokens (fallback provider) |

4. **Create**. First build takes ~5 minutes (it installs scikit-learn and pandas for the models).

The start command runs `alembic upgrade head && python -m app.db.seed` before uvicorn. Both are idempotent, so restarts never duplicate data.

5. Verify:
   ```bash
   curl https://YOUR-APP.onrender.com/health
   curl https://YOUR-APP.onrender.com/api/catalog/cloth-types
   curl https://YOUR-APP.onrender.com/api/ml/status
   ```
   `/api/ml/status` should list your three models. Interactive docs: `/docs`.

---

## 3. Frontend — Vercel (~10 min)

1. Sign up at <https://vercel.com> with GitHub
2. **Add New → Project**, import `threadcraft`
3. Configure:
   - **Root Directory**: `frontend` ← easy to miss, and nothing works without it
   - Framework: Vite (auto-detected)
4. **Environment Variables** — add before the first deploy:

| Name | Value |
|---|---|
| `VITE_API_URL` | `https://threadcraft-api-bczq.onrender.com` — no trailing slash |

5. **Deploy**

6. **Turn off Deployment Protection.** Vercel → Project → **Settings → Deployment Protection** → set **Vercel Authentication** to **Disabled**, then Save.

   Left on, every visitor is bounced to a Vercel login page — including your marker. It is on by default for new projects and gives a `302` to `vercel.com/sso-api`, which looks like a broken deploy rather than a permission setting.

7. Note your **production domain** from Project → Domains. It is the short one (`threadcraft-<scope>.vercel.app`), not the long per-deployment hash URL — the hash changes on every push, so pinning CORS to it will break at the next commit.

> **`VITE_*` variables are inlined at build time.** Changing `VITE_API_URL` in the dashboard does nothing until you **redeploy**. This is the single most common confusion here.

8. Go back to Render → **Environment** and set **three** variables to that production domain:

| Name | Value | Why |
|---|---|---|
| `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` | A bare origin, a comma-separated list, or a JSON array all work |
| `CHECKOUT_SUCCESS_URL` | `https://YOUR-APP.vercel.app/success` | Where Stripe returns after payment |
| `CHECKOUT_CANCEL_URL` | `https://YOUR-APP.vercel.app/success` | Where Stripe returns if the customer backs out |

The two `CHECKOUT_*` variables default to `localhost:5173`. Leaving them means Stripe sends a paying customer to a page that doesn't exist and **the payment is never confirmed** — the order sits at `pending` forever. This is silent: nothing in the UI reports it.

Render redeploys automatically after each change.

---

## 4. Keep the API awake

Render's free tier sleeps after **15 minutes** idle and takes **~50 s** to wake. `.github/workflows/keep-warm.yml` pings `/health` every 10 minutes.

Enable it: **GitHub repo → Settings → Secrets and variables → Actions → Variables → New**

| Name | Value |
|---|---|
| `API_URL` | `https://threadcraft-api-bczq.onrender.com` |

Without the variable the job exits quietly instead of failing every 10 minutes.

Before a demo, also hit **Actions → Keep API warm → Run workflow** manually, and load the site once yourself.

---

## 5. Verify the whole thing

Open your Vercel URL and walk the journey:

1. `/` loads
2. `/design` → garments load **from the API** (not hardcoded)
3. Pick a garment → material → step 4 → **"Estimate my measurements"** returns values
4. Type a wrong waist (e.g. 176) → it gets **flagged**
5. Step 5 → prices are itemised and change with your choices
6. Step 6 → a mockup appears
7. Confirm → you land on `/success` with a real order number
8. Payment shows **paid** (simulated mode) or you're sent to Stripe Checkout and back
9. **Refresh that page** — it must still work (this is the SPA-rewrite check)
10. `/track/YOUR-ORDER-NUMBER` shows the timeline

Then sign in as your admin, open `/admin`, and check **Settings → System health**: it reports which mode each integration is actually in. Simulated payments and console email are invisible from the customer UI, so this page is the only place they surface.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Frontend loads, every API call fails | `VITE_API_URL` wrong or not baked in | Check it's set, then **redeploy** — build-time only |
| CORS error in the browser console | Vercel URL not in `CORS_ORIGINS` | `curl https://YOUR-API.onrender.com/health` reports the **effective** origin list. Set the exact origin; a bare URL, a comma-separated list and a JSON array are all accepted |
| Deploy crash-loops with `SettingsError: error parsing value for field "cors_origins"` | An older build required strict JSON | Fixed — any of the three spellings now works. Redeploy |
| Vercel URL redirects to a Vercel login page | Deployment Protection is on | Vercel → Project → Settings → **Deployment Protection** → set Vercel Authentication to **Disabled**. Otherwise only you can open the site |
| Refreshing `/design` gives 404 | Missing SPA rewrite | `frontend/vercel.json` handles this — confirm Root Directory is `frontend` |
| First request takes ~50 s | Free-tier cold start | Expected. Set up keep-warm; pre-warm before a demo |
| `psycopg2` / SSL errors on boot | Scheme or endpoint wrong | Must be `postgresql+psycopg2://`, pooled endpoint, `?sslmode=require` |
| `/api/ml/status` shows `error` | sklearn version mismatch | Artefacts were trained on **1.6.1**; `requirements-ml.txt` pins it. Don't bump it without retraining |
| `ModuleNotFoundError: dill` | Missing unpickle dependency | Already in `requirements-ml.txt` — confirm the build used it |
| Mockups are always placeholders | No image provider configured | Set `CF_ACCOUNT_ID` + `CF_API_TOKEN`; check `/api/mockup/status` |
| Uploaded images vanish after redeploy | Render's disk is ephemeral | Expected on free tier. Configure R2 for persistence, or accept it for the demo |
| Order stays `pending` after paying | `CHECKOUT_SUCCESS_URL` still points at localhost | Set it to your Vercel `/success` URL and redeploy |
| Admin → Settings shows "Payments: simulated" | No `STRIPE_SECRET_KEY` | Expected without a Stripe account. Orders are marked paid without a charge — never present this as a real payment |

---

## Known free-tier limitations (state these in the report)

- **Cold starts.** ~50 s after 15 minutes idle. Mitigated by a cron ping, not eliminated.
- **Ephemeral filesystem.** Generated mockups and uploads don't survive a redeploy unless R2 is configured. The app falls back to local disk deliberately so it runs with no third-party accounts.
- **Vercel Hobby is non-commercial.** Fine for an academic project; a real launch would need a paid plan.
- **Classifier disabled in production.** `ML_ENABLE_CLASSIFIER=false` because it needs torch (~800 MB), over the free instance's memory. The two scikit-learn models run fine.
