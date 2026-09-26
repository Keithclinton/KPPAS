from django.test import TestCase
from django.urls import reverse

from kppas_backend.models.api_key import ApiKey
from kppas_backend.tests.test_models import make_promise


class OpenDataApiTests(TestCase):
    def test_no_key_returns_403(self):
        response = self.client.get(reverse('open_data_api'))
        self.assertEqual(response.status_code, 403)

    def test_wrong_key_returns_403(self):
        response = self.client.get(reverse('open_data_api'), {'api_key': 'nonsense'})
        self.assertEqual(response.status_code, 403)

    def test_inactive_key_returns_403(self):
        api_key = ApiKey.objects.create(label='revoked', is_active=False)
        response = self.client.get(reverse('open_data_api'), {'api_key': api_key.key})
        self.assertEqual(response.status_code, 403)

    def test_valid_key_via_query_param_returns_data(self):
        make_promise(county='Testland')
        api_key = ApiKey.objects.create(label='tester')
        response = self.client.get(reverse('open_data_api'), {'api_key': api_key.key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_valid_key_via_bearer_header_returns_data(self):
        make_promise(county='Testland')
        api_key = ApiKey.objects.create(label='tester')
        response = self.client.get(reverse('open_data_api'), HTTP_AUTHORIZATION=f'Bearer {api_key.key}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_county_filter(self):
        make_promise(county='Testland')
        make_promise(county='Otherland')
        api_key = ApiKey.objects.create(label='tester')
        response = self.client.get(reverse('open_data_api'), {'api_key': api_key.key, 'county': 'Testland'})
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['county'], 'Testland')

    def test_empty_county_param_filters_to_national_promises(self):
        make_promise(county='')
        make_promise(county='Testland')
        api_key = ApiKey.objects.create(label='tester')
        response = self.client.get(reverse('open_data_api'), {'api_key': api_key.key, 'county': ''})
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertIsNone(data['results'][0]['county'])

    def test_using_a_key_updates_last_used_at(self):
        api_key = ApiKey.objects.create(label='tester')
        self.assertIsNone(api_key.last_used_at)
        self.client.get(reverse('open_data_api'), {'api_key': api_key.key})
        api_key.refresh_from_db()
        self.assertIsNotNone(api_key.last_used_at)
