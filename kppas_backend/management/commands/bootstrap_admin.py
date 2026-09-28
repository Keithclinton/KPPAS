import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Creates one superuser from DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD env
    vars, but only if no user with that username already exists -- unlike
    `createsuperuser --noinput`, which errors on a duplicate. Meant to sit in
    the Procfile's release phase so a first admin account exists on a
    platform with no interactive shell access, without erroring out (and
    blocking the deploy) on every run after the first."""

    help = 'Idempotently creates a superuser from DJANGO_SUPERUSER_* env vars.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write('DJANGO_SUPERUSER_USERNAME/PASSWORD not set -- skipping.')
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Superuser "{username}" already exists -- skipping.')
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Created superuser "{username}".'))
