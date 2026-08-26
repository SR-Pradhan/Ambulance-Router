# Deployment

Three pieces, three providers, all free:

| Piece | Provider | Why |
|---|---|---|
| Database | **Neon** | Free plan is permanent. Render's free Postgres is deleted 30 days after creation, and only one is allowed per account. |
| Backend | **Render** | Free web service, 512 MB RAM. This app uses ~34 MB. |
| Frontend | **Vercel** | Static build, 396 KB. |

Nothing here needs a credit card.

---

## Before you start

Know these two limits, because they bite later rather than immediately:

- **Render gives 750 free instance-hours per month across your WHOLE workspace**, not per service. Sleeping services consume nothing, but if the pool runs out, Render suspends *every* free service on the account. Check Dashboard → Billing before adding a service.
- **Free Render services sleep after 15 minutes idle.** The first request after that takes roughly 50 seconds. Open the link a minute before demoing it.

---

## 1. Database on Neon

1. Sign up at <https://neon.com> and create a project. Any region near you.
2. Copy the connection string. It looks like:
   `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`
3. Seed it **from your laptop**, pointing the seed script at Neon instead of localhost:

   ```bash
   cd backend
   DATABASE_URL="postgresql://...your neon string..." python seed_data.py
   ```

   This creates the tables and loads the real OpenStreetMap road network. It
   should print `Seeded 433 real road junctions, 643 road segments`.

Keep that connection string; the backend needs it next.

> The seed script is destructive: it truncates every table and rebuilds. Running
> it again against production wipes any emergency requests created through the UI.

---

## 2. Backend on Render

1. Dashboard → **New** → **Web Service**, connect the GitHub repo.
2. Settings:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

   `--host 0.0.0.0` is not optional. The default binds to localhost only, and
   Render's router would never reach it. `$PORT` is injected by Render; hardcoding
   a port fails.

3. Environment variables:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon connection string from step 1 |
   | `PYTHON_VERSION` | `3.13.0` |
   | `ADMIN_KEY` | a secret you generate (see below) |

   Generate the admin key with:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(24))"
   ```

   This gates the two destructive endpoints (changing bed counts, completing a
   trip). **Without it those endpoints return 503 rather than running
   unprotected** — the check fails closed on purpose, so a forgotten variable is
   loud instead of silently leaving production open. Everything else, including
   creating a request, stays public so the demo works for visitors.

   Leave `ALLOWED_ORIGINS` for now; you do not know the Vercel URL yet.

4. Deploy, then check `https://your-service.onrender.com/docs` loads.

---

## 3. Frontend on Vercel

1. **Add New** → **Project**, import the same repo.
2. Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (detected automatically)
3. Environment variable:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://your-service.onrender.com` (no trailing slash) |

   Vite inlines this at **build** time, not run time. Changing it later means
   triggering a redeploy, not just a restart.

4. Deploy. Note the URL, e.g. `https://ambulance-router.vercel.app`.

---

## 4. Close the CORS loop

The frontend now knows the backend, but the backend does not yet trust the
frontend, so every request will be blocked by the browser.

Back in **Render** → Environment:

| Key | Value |
|---|---|
| `ALLOWED_ORIGINS` | `https://ambulance-router.vercel.app` |

No trailing slash. Comma separate if you have several. Save, which redeploys.

---

## 5. Verify

```bash
curl https://your-service.onrender.com/
curl "https://your-service.onrender.com/route?source=1&dest=400&hour=3"
```

Then open the Vercel URL. The map should load with 12 hospital markers. If the
UI shows "Cannot reach the API", the cause is almost always one of:

| Symptom | Cause |
|---|---|
| CORS error in the browser console | `ALLOWED_ORIGINS` missing, misspelled, or has a trailing slash |
| Requests go to `localhost:8001` | `VITE_API_URL` was not set at build time; redeploy the frontend |
| First request hangs ~50s then works | Normal. The free service was asleep. |
| 500 from the API | `DATABASE_URL` wrong, or the database was never seeded |
| Admin buttons give 503 | `ADMIN_KEY` not set on Render |
| Admin buttons give 401 | Wrong key typed into the dashboard's Unlock control |

---

## Costs and what to watch

Everything above is free. The things that could change that:

- **Render instance-hours.** Dashboard → Billing shows the month's usage against
  750. The frontend polls `/ambulances/live` every 2 seconds while the Map tab is
  visible, and pauses when hidden, so an abandoned tab no longer keeps the
  backend awake. That pause is the main protection for the shared pool.
- **Neon compute-hours.** 100 per project per month, scaling to zero after five
  minutes idle. A portfolio project uses a small fraction.

## Updating after the first deploy

Both providers redeploy automatically when you push to `main`. Schema changes
are the exception: this project has no migration tool, so a new column needs an
`ALTER TABLE` run against Neon by hand, or a reseed (which wipes data).
