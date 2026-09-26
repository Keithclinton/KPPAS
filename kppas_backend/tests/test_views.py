from django.test import TestCase
from django.urls import reverse

from kppas_backend.models.promise_registry import PromiseComment
from kppas_backend.tests.test_models import make_promise


class PromiseRegistryViewTests(TestCase):
    def test_returns_200_with_no_promises(self):
        response = self.client.get(reverse('promise_registry'))
        self.assertEqual(response.status_code, 200)

    def test_lists_a_county_with_promises(self):
        make_promise(county='Testland')
        response = self.client.get(reverse('promise_registry'))
        self.assertContains(response, 'Testland')

    def test_national_promise_surfaces_as_national_card_not_a_county_row(self):
        make_promise(county='')
        response = self.client.get(reverse('promise_registry'))
        self.assertContains(response, 'National government')


class CountyPromisesViewTests(TestCase):
    def test_national_url_segment_maps_to_blank_county(self):
        make_promise(county='', text='A national promise')
        response = self.client.get(reverse('county_promises', args=['national']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A national promise')
        self.assertContains(response, 'National Government')

    def test_county_page_does_not_show_national_promises(self):
        make_promise(county='', text='A national promise')
        make_promise(county='Testland', text='A county promise')
        response = self.client.get(reverse('county_promises', args=['Testland']))
        self.assertContains(response, 'A county promise')
        self.assertNotContains(response, 'A national promise')

    def test_status_filter_narrows_the_table_only(self):
        make_promise(county='Testland', status='delivered', text='Delivered one')
        make_promise(county='Testland', status='pending', text='Pending one')
        response = self.client.get(reverse('county_promises', args=['Testland']), {'status': 'delivered'})
        self.assertContains(response, 'Delivered one')
        self.assertNotContains(response, 'Pending one')


class PromiseDetailViewTests(TestCase):
    def test_get_shows_the_promise(self):
        promise = make_promise(county='Testland')
        response = self.client.get(reverse('promise_detail', args=['Testland', promise.id]))
        self.assertContains(response, promise.text)

    def test_post_creates_a_top_level_comment_and_redirects(self):
        promise = make_promise(county='Testland')
        response = self.client.post(
            reverse('promise_detail', args=['Testland', promise.id]),
            {'name': 'Jane', 'text': 'Still not done as of today.'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(promise.comments.count(), 1)
        comment = promise.comments.first()
        self.assertEqual(comment.name, 'Jane')
        self.assertIsNone(comment.parent)

    def test_reply_links_to_its_parent(self):
        promise = make_promise(county='Testland')
        parent = PromiseComment.objects.create(promise=promise, name='Jane', text='First')
        self.client.post(
            reverse('promise_detail', args=['Testland', promise.id]),
            {'name': 'Bob', 'text': 'Replying', 'parent_id': parent.id},
        )
        reply = promise.comments.get(name='Bob')
        self.assertEqual(reply.parent_id, parent.id)

    def test_tampered_parent_id_from_another_promise_is_dropped(self):
        promise = make_promise(county='Testland')
        other_promise = make_promise(county='Otherland', text='Unrelated')
        foreign_comment = PromiseComment.objects.create(promise=other_promise, name='X', text='Not related')
        self.client.post(
            reverse('promise_detail', args=['Testland', promise.id]),
            {'name': 'Bob', 'text': 'Sneaky reply', 'parent_id': foreign_comment.id},
        )
        reply = promise.comments.get(name='Bob')
        self.assertIsNone(reply.parent)


class CountyBriefViewTests(TestCase):
    def test_returns_200_for_a_county_with_no_promises(self):
        response = self.client.get(reverse('county_brief', args=['Nowhereland']))
        self.assertEqual(response.status_code, 200)

    def test_flags_broken_promises(self):
        make_promise(county='Testland', status='broken', text='A broken one')
        response = self.client.get(reverse('county_brief', args=['Testland']))
        self.assertContains(response, 'A broken one')
