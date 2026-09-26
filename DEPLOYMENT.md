# Deploying to Railway

This app is ready to deploy as-is: production settings, static file serving,
and Postgres support are all wired up via environment variables (see
`.env.example`) and only kick in when those variables are actually set, so
local development is unaffected.

## 1. Create the project

1. Push this repo to GitHub if it isn't already there.
2. At [railway.app](https://railway.app), create a new project and choose
   "Deploy from GitHub repo" -- select this repo.
3. Railway will detect the `Procfile` and use it: the `release` line runs
   migrations and `collectstatic` on every deploy, and the `web` line starts
   the app with gunicorn.

## 2. Add Postgres

1. In the Railway project, click "New" -> "Database" -> "Add PostgreSQL".
2. Railway automatically injects a `DATABASE_URL` variable into your web
   service's environment -- `settings.py` picks this up on its own the next
   time the app starts. Nothing else to configure.

## 3. Set environment variables

On the web service, open the "Variables" tab and add:

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | A long random string -- generate one locally with `python -c "import secrets; print(secrets.token_urlsafe(50))"` and never reuse the dev fallback in `settings.py` |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | The domain Railway gives you, e.g. `your-app.up.railway.app` (add your own domain too if you attach one later) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Same domain with the scheme, e.g. `https://your-app.up.railway.app` |

Redeploy after setting these (Railway does this automatically when variables change).

Sanity-check the production settings locally before deploying, with Django's
own deployment checklist:

```
DJANGO_DEBUG=False DJANGO_SECRET_KEY=<a real generated key> DJANGO_ALLOWED_HOSTS=example.com python manage.py check --deploy
```

It'll flag a couple of optional hardening steps this project intentionally
leaves off by default (e.g. HSTS) since misconfiguring them can lock out an
otherwise-working site -- worth reading through once things are live over
HTTPS, not required to launch.

## 4. Create an admin user

Railway's dashboard has a "Shell" tab on the web service (or use the Railway
CLI: `railway run python manage.py createsuperuser`). Run:

```
python manage.py createsuperuser
```

## 5. Run the first ingestion

Same shell, one-time:

```
python manage.py update_procurement_promises --all-counties
```

This populates the registry from live PPRA data. See step 6 to keep it
current automatically from here on.

## 6. Schedule the ingestion (the "someone has to remember to run it" gap)

Railway supports Cron Jobs as a service type, run on their own schedule
against your same codebase and database:

1. In the project, click "New" -> "Cron Job".
2. Point it at the same GitHub repo/branch as the web service.
3. Set the schedule -- daily is reasonable given PPIP publishes daily, e.g.
   `0 3 * * *` (03:00 UTC every day).
4. Set the command to:
   ```
   python manage.py update_procurement_promises --all-counties
   ```
5. It shares the same environment variables and database as the web
   service automatically (same Railway project).

The command is safe to run repeatedly: it never overwrites a promise's
status once a human has verified it (see the comment in
`update_procurement_promises.py`), it only adds new awards and refreshes
source-derived fields on existing ones.

If you'd rather not add a second Railway service, a plain system cron
running the same command works identically on any host that has one.

## What's NOT automated

- **Quarterly verification** (assigning green/amber/red to a promise) stays
  a manual, human step by design -- see `PromiseVerification` in the admin.
  Automating this would defeat the point of independent verification.
- **API keys** for `/api/open-data/` are issued by hand in the admin
  (`ApiKey` model) after a request comes in via the contact email on the
  data access page -- there's no self-serve signup.
