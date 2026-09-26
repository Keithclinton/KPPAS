from datetime import date, timedelta

from django.test import SimpleTestCase

from etl import procurement_etl as etl


class ExtractCountyTests(SimpleTestCase):
    def test_matches_county_government_suffix(self):
        self.assertEqual(etl._extract_county('Nakuru County Government'), 'Nakuru')

    def test_case_insensitive_suffix_match(self):
        # Regression guard: an earlier bug compared a lowercased suffix
        # against a not-fully-lowercased lookup, silently dropping every match.
        self.assertEqual(etl._extract_county('nakuru county government'), 'nakuru')
        self.assertEqual(etl._extract_county('NAKURU COUNTY GOVERNMENT'), 'NAKURU')

    def test_non_county_buyer_returns_none(self):
        self.assertIsNone(etl._extract_county('Ministry of Health'))
        self.assertIsNone(etl._extract_county('Kenya Revenue Authority'))

    def test_blank_buyer_returns_none(self):
        self.assertIsNone(etl._extract_county(''))
        self.assertIsNone(etl._extract_county(None))


class ExtractNationalEntityTests(SimpleTestCase):
    def test_matches_state_department_prefix(self):
        self.assertEqual(
            etl._extract_national_entity('State Department of East Africa Community'),
            'State Department of East Africa Community',
        )

    def test_matches_ministry_of_prefix(self):
        self.assertEqual(etl._extract_national_entity('Ministry of Health'), 'Ministry of Health')

    def test_matches_curated_allowlist_case_insensitively(self):
        self.assertEqual(etl._extract_national_entity('The Judiciary'), 'The Judiciary')
        self.assertEqual(etl._extract_national_entity('the judiciary'), 'the judiciary')

    def test_county_government_is_not_national(self):
        self.assertIsNone(etl._extract_national_entity('Nakuru County Government'))

    def test_unrecognised_agency_returns_none(self):
        self.assertIsNone(etl._extract_national_entity('Nairobi Technical Training Institute'))


class GuessCategoryTests(SimpleTestCase):
    def test_matches_a_sector_keyword(self):
        self.assertEqual(etl._guess_category('Construction of a new dispensary', None), 'Health')

    def test_infrastructure_override_beats_landmark_keyword(self):
        # Regression guard: "Borehole Area" as a landmark name inside a
        # floodlight project's title used to get mis-tagged as Water.
        title = 'Supply and installation of solar floodlights near Borehole Area, Chepseon'
        self.assertEqual(etl._guess_category(title, None), 'Infrastructure')

    def test_falls_back_to_works_procurement_category(self):
        self.assertEqual(etl._guess_category('Some unlabelled project', 'works'), 'Infrastructure')

    def test_falls_back_to_other_with_no_signal(self):
        self.assertEqual(etl._guess_category('Some unlabelled project', 'goods'), 'Other')


class InferLifecycleStatusTests(SimpleTestCase):
    def test_future_start_is_pending(self):
        future = date.today() + timedelta(days=30)
        self.assertEqual(etl.infer_lifecycle_status(future, future + timedelta(days=60)), 'pending')

    def test_past_end_is_in_progress_not_delivered_or_broken(self):
        past_start = date.today() - timedelta(days=100)
        past_end = date.today() - timedelta(days=10)
        self.assertEqual(etl.infer_lifecycle_status(past_start, past_end), 'in_progress')

    def test_ongoing_contract_is_in_progress(self):
        past_start = date.today() - timedelta(days=10)
        future_end = date.today() + timedelta(days=100)
        self.assertEqual(etl.infer_lifecycle_status(past_start, future_end), 'in_progress')

    def test_no_dates_at_all_is_pending(self):
        self.assertEqual(etl.infer_lifecycle_status(None, None), 'pending')


class NormalizeAwardsTests(SimpleTestCase):
    def test_extracts_award_fields_from_a_release(self):
        release = {
            'ocid': 'ocds-abc-1',
            'date': '2026-01-01T00:00:00Z',
            'buyer': {'name': 'Nakuru County Government'},
            'tender': {'title': 'Fallback title', 'mainProcurementCategory': 'works'},
            'contracts': [{'awardID': 'award-1', 'dateSigned': '2026-02-15T00:00:00Z'}],
            'awards': [{
                'id': 'award-1',
                'title': 'Construction of a borehole',
                'value': {'amount': 500000, 'currency': 'KES'},
                'suppliers': [{'name': 'Acme Contractors'}],
                'contractPeriod': {'startDate': '2026-03-01', 'endDate': '2026-09-01'},
            }],
        }
        [award] = list(etl._normalize_awards(release))
        self.assertEqual(award['ocid'], 'ocds-abc-1')
        self.assertEqual(award['award_id'], 'award-1')
        self.assertEqual(award['title'], 'Construction of a borehole')
        self.assertEqual(award['buyer_name'], 'Nakuru County Government')
        self.assertEqual(award['amount'], 500000)
        self.assertEqual(award['supplier_name'], 'Acme Contractors')
        self.assertEqual(award['contract_start'], date(2026, 3, 1))
        self.assertEqual(award['contract_end'], date(2026, 9, 1))
        # dateSigned from contracts[] should win over the release-level date.
        self.assertEqual(award['date_made'], date(2026, 2, 15))
        self.assertEqual(award['category'], 'Water')

    def test_falls_back_to_release_date_when_no_contract_signed_date(self):
        release = {
            'ocid': 'ocds-abc-2',
            'date': '2026-01-01T00:00:00Z',
            'buyer': {'name': 'Kisumu County Government'},
            'tender': {'title': 'Roadworks'},
            'awards': [{'id': 'award-2', 'title': 'Roadworks'}],
        }
        [award] = list(etl._normalize_awards(release))
        self.assertEqual(award['date_made'], date(2026, 1, 1))

    def test_no_awards_yields_nothing(self):
        release = {'ocid': 'x', 'buyer': {'name': 'Y'}, 'awards': []}
        self.assertEqual(list(etl._normalize_awards(release)), [])
