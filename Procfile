release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
web: gunicorn kppas_backend.wsgi --log-file -
