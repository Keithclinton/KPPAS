from datetime import date

from django.test import SimpleTestCase

from kppas_backend.scoring import aggregate_promise_scores, infer_status_from_verification


class AggregatePromiseScoresTests(SimpleTestCase):
    def test_buckets_by_category_and_score(self):
        rows = aggregate_promise_scores([
            ('Water', 'green'),
            ('Water', 'amber'),
            ('Water', None),
            ('Roads', 'red'),
        ])
        by_category = {r['category']: r for r in rows}
        self.assertEqual(by_category['Water']['green'], 1)
        self.assertEqual(by_category['Water']['amber'], 1)
        self.assertEqual(by_category['Water']['red'], 0)
        self.assertEqual(by_category['Water']['unverified'], 1)
        self.assertEqual(by_category['Water']['total'], 3)
        self.assertEqual(by_category['Roads']['red'], 1)
        self.assertEqual(by_category['Roads']['total'], 1)

    def test_sorted_by_category_name(self):
        rows = aggregate_promise_scores([('Water', 'green'), ('Agriculture', 'green')])
        self.assertEqual([r['category'] for r in rows], ['Agriculture', 'Water'])

    def test_empty_input(self):
        self.assertEqual(aggregate_promise_scores([]), [])


class InferStatusFromVerificationTests(SimpleTestCase):
    def test_green_before_deadline_is_in_progress(self):
        self.assertEqual(infer_status_from_verification('green', date(2099, 1, 1)), 'in_progress')

    def test_green_with_no_deadline_is_in_progress(self):
        self.assertEqual(infer_status_from_verification('green', None), 'in_progress')

    def test_green_after_deadline_is_delivered(self):
        self.assertEqual(infer_status_from_verification('green', date(2000, 1, 1)), 'delivered')

    def test_amber_is_always_delayed(self):
        self.assertEqual(infer_status_from_verification('amber', None), 'delayed')
        self.assertEqual(infer_status_from_verification('amber', date(2099, 1, 1)), 'delayed')
        self.assertEqual(infer_status_from_verification('amber', date(2000, 1, 1)), 'delayed')

    def test_red_before_deadline_is_delayed_not_broken(self):
        self.assertEqual(infer_status_from_verification('red', date(2099, 1, 1)), 'delayed')

    def test_red_after_deadline_is_broken(self):
        self.assertEqual(infer_status_from_verification('red', date(2000, 1, 1)), 'broken')

    def test_red_with_no_deadline_is_delayed(self):
        self.assertEqual(infer_status_from_verification('red', None), 'delayed')

    def test_unscored_verification_returns_none(self):
        self.assertIsNone(infer_status_from_verification(None, None))
