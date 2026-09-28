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

exec gunicorn kppas_backend.wsgi --log-file -
