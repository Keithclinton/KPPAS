from datetime import date, timedelta

from django.test import TestCase

from kppas_backend.models.promise_registry import (
    CountyProcurementActivity, Promise, PromiseSource, PromiseVerification,
)


def make_promise(**kwargs):
    source = PromiseSource.objects.create(source_type='ppra', title='Test source')
    defaults = {
        'text': 'Build a thing',
        'source': source,
        'date_made': date(2026, 1, 1),
        'responsible_actor': 'Test County Government',
        'county': 'Testland',
        'category': 'Other',
    }
    defaults.update(kwargs)
    return Promise.objects.create(**defaults)


class PromiseVerificationStatusSyncTests(TestCase):
    def test_green_verification_moves_status_to_in_progress(self):
        promise = make_promise(status='pending', stated_deadline=date.today() + timedelta(days=30))
        PromiseVerification.objects.create(promise=promise, quarter='Q1', year=2026, score='green')
        promise.refresh_from_db()
        self.assertEqual(promise.status, 'in_progress')

    def test_red_verification_past_deadline_marks_broken(self):
        promise = make_promise(status='pending', stated_deadline=date.today() - timedelta(days=1))
        PromiseVerification.objects.create(promise=promise, quarter='Q1', year=2026, score='red')
        promise.refresh_from_db()
        self.assertEqual(promise.status, 'broken')

    def test_only_the_newest_quarter_drives_status(self):
        promise = make_promise(status='pending', stated_deadline=date.today() + timedelta(days=30))
        PromiseVerification.objects.create(promise=promise, quarter='Q1', year=2026, score='red')
        promise.refresh_from_db()
        self.assertEqual(promise.status, 'delayed')
        # Creating an OLDER quarter afterwards must not undo the newer
        # quarter's effect on status -- this is the whole point of ordering
        # by (-year, -quarter) inside PromiseVerification.save().
        PromiseVerification.objects.create(promise=promise, quarter='Q4', year=2025, score='green')
        promise.refresh_from_db()
        self.assertEqual(promise.status, 'delayed')


class CountyProcurementActivityTests(TestCase):
    def test_award_gap_flagged_above_threshold_with_zero_awards(self):
        activity = CountyProcurementActivity.objects.create(
            county='Testland', year=2026, tenders_published=15, awards_recorded=0,
        )
        self.assertTrue(activity.has_award_gap)

    def test_no_gap_below_threshold(self):
        activity = CountyProcurementActivity.objects.create(
            county='Testland', year=2026, tenders_published=5, awards_recorded=0,
        )
        self.assertFalse(activity.has_award_gap)

    def test_no_gap_when_awards_exist(self):
        activity = CountyProcurementActivity.objects.create(
            county='Testland', year=2026, tenders_published=20, awards_recorded=3,
        )
        self.assertFalse(activity.has_award_gap)
