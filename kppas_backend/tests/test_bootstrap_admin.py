import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class BootstrapAdminTests(TestCase):
    def test_does_nothing_without_env_vars(self):
        call_command('bootstrap_admin')
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_creates_a_superuser_from_env_vars(self):
        os.environ['DJANGO_SUPERUSER_USERNAME'] = 'TestAdmin'
        os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'Test@123456'
        os.environ['DJANGO_SUPERUSER_EMAIL'] = 'test@example.com'
        try:
            call_command('bootstrap_admin')
            user = get_user_model().objects.get(username='TestAdmin')
            self.assertTrue(user.is_superuser)
            self.assertTrue(user.is_staff)
            self.assertTrue(user.check_password('Test@123456'))
        finally:
            for key in ('DJANGO_SUPERUSER_USERNAME', 'DJANGO_SUPERUSER_PASSWORD', 'DJANGO_SUPERUSER_EMAIL'):
                os.environ.pop(key, None)

    def test_running_twice_does_not_error_or_duplicate(self):
        os.environ['DJANGO_SUPERUSER_USERNAME'] = 'TestAdmin'
        os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'Test@123456'
        try:
            call_command('bootstrap_admin')
            call_command('bootstrap_admin')  # must not raise on the duplicate
            self.assertEqual(get_user_model().objects.filter(username='TestAdmin').count(), 1)
        finally:
            for key in ('DJANGO_SUPERUSER_USERNAME', 'DJANGO_SUPERUSER_PASSWORD'):
                os.environ.pop(key, None)
