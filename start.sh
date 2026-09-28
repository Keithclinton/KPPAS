#!/usr/bin/env bash
# Runs on every container boot, not just once per "release" -- Railway's
# support for a Procfile's separate release phase turned out unreliable in
# practice (migrations were found unapplied after a deploy that should have
# run them), so these steps are guaranteed here instead by living directly
# in the process gunicorn is started from. All three are idempotent, so
# running them again on every boot is harmless.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py bootstrap_admin

# Bare `gunicorn kppas_backend.wsgi` defaults to a single worker with no
# request timeout -- one slow request (or the odd USSD webhook client that
# hangs) would block every other visitor. 3 workers is a reasonable default
# for a small single-instance deployment; WEB_CONCURRENCY overrides it if the
# instance size changes later.
exec gunicorn kppas_backend.wsgi --workers "${WEB_CONCURRENCY:-3}" --timeout 60 --log-file -
