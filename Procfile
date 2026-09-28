release: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py bootstrap_admin
web: gunicorn kppas_backend.wsgi --log-file -
