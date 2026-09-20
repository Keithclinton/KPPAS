from django.conf import settings
from django.db import models

from ..scoring import infer_status_from_verification

PROMISE_CATEGORY_CHOICES = [
    ('Infrastructure', 'Infrastructure'),
    ('Health', 'Health'),
    ('Agriculture', 'Agriculture'),
    ('Housing', 'Housing'),
    ('Roads', 'Roads'),
    ('Water', 'Water'),
    ('Education', 'Education'),
    ('Budget', 'Budget'),
    ('Governance', 'Governance'),
    ('Other', 'Other'),
]


class PromiseSource(models.Model):
    SOURCE_TYPE_CHOICES = [
        ('gazette', 'Kenya Gazette'),
        ('hansard', 'Parliamentary/County Assembly Hansard'),
        ('ppra', 'PPRA Procurement Portal'),
        ('budget', 'Budget Document/Speech'),
        ('press_release', 'Press Release/Official Social Media'),
        ('cidp', 'County Integrated Development Plan'),
        ('cob', 'Controller of Budget Report'),
        ('auditor_general', 'Auditor-General Report'),
        ('other', 'Other'),
    ]

    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    title = models.CharField(
        max_length=300,
        help_text="e.g. 'Kenya Gazette Vol. CXXVIII No. 95' or 'National Assembly Hansard, 12 Mar 2026'",
    )
    reference = models.CharField(
        max_length=200, blank=True,
        help_text="Gazette notice number, Hansard column, tender ID, etc.",
    )
    url = models.URLField(blank=True)
    published_date = models.DateField(null=True, blank=True)
    excerpt = models.TextField(blank=True, help_text="The exact quoted text this entry is drawn from")
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='added_promise_sources'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Promise(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
        ('delayed', 'Delayed'),
        ('broken', 'Broken'),
    ]

    text = models.TextField(help_text="The exact commitment, in the government's own words")
    source = models.ForeignKey(PromiseSource, on_delete=models.PROTECT, related_name='promises')
    date_made = models.DateField()
    responsible_actor = models.CharField(max_length=200, help_text='Ministry, county, or named official')
    county = models.CharField(max_length=100, blank=True, help_text='Blank for national-level promises')
    category = models.CharField(max_length=20, choices=PROMISE_CATEGORY_CHOICES)
    stated_deadline = models.DateField(null=True, blank=True)
    deadline_text = models.CharField(
        max_length=200, blank=True,
        help_text="Free-text timeframe when no exact date was given, e.g. 'within FY2026/27'",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='logged_promises'
    )
    logged_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:60]} ({self.responsible_actor})"


class PromiseVerification(models.Model):
    SCORE_CHOICES = [
        ('green', 'Green'),
        ('amber', 'Amber'),
        ('red', 'Red'),
    ]

    promise = models.ForeignKey(Promise, on_delete=models.CASCADE, related_name='verifications')
    quarter = models.CharField(max_length=10, help_text="e.g. Q1")
    year = models.IntegerField()
    evidence_source = models.ForeignKey(
        PromiseSource, null=True, blank=True, on_delete=models.SET_NULL, related_name='verifications'
    )
    score = models.CharField(max_length=10, choices=SCORE_CHOICES)
    notes = models.TextField(blank=True)
    right_of_reply_sent_at = models.DateTimeField(null=True, blank=True)
    right_of_reply_response = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_promises'
    )
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('promise', 'quarter', 'year')
        ordering = ['-year', '-quarter']

    def __str__(self):
        return f"{self.promise} - {self.quarter} {self.year}: {self.score}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Roll the *newest* quarter on record onto the promise's lifecycle
        # status, so editing an older quarter here can't undo a more recent
        # one. Lives here (not in admin.py) so any creation path -- admin,
        # a future bulk-import command, a shell session -- stays in sync,
        # not just the admin forms this was first wired up through.
        latest = self.promise.verifications.order_by('-year', '-quarter').first()
        if latest is None:
            return
        new_status = infer_status_from_verification(latest.score, self.promise.stated_deadline)
        if new_status and self.promise.status != new_status:
            Promise.objects.filter(pk=self.promise_id).update(status=new_status)


class PromiseComment(models.Model):
    """Public discussion on a single promise -- a citizen can comment
    directly on the commitment ('this borehole still isn't built') and
    others can reply, like a comment thread under a post. Separate from
    PublicFeedback (a free-text comment per county/sector, no rating): this
    is threaded and tied to one specific promise rather than a whole sector
    -- and it's exactly the kind of on-the-ground evidence an analyst doing
    quarterly verification should be reading right here."""
    promise = models.ForeignKey(Promise, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies'
    )
    name = models.CharField(max_length=100, blank=True, default='Anonymous')
    text = models.TextField(max_length=2000)
    posted_at = models.DateTimeField(auto_now_add=True)
    # No login is required to post (matches the USSD/PublicFeedback posture
    # already taken elsewhere in the app), so this is the only moderation
    # lever -- an admin can hide a comment without deleting it outright.
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['posted_at']

    def __str__(self):
        return f'{self.name or "Anonymous"} on {self.promise}: {self.text[:40]}'


class CountyProcurementActivity(models.Model):
    """Per-county, per-year tender/award tallies from PPRA/PPIP -- covers
    *every* published tender, not just the ones that became a logged Promise
    (which only happens once a tender is awarded). Exists so a county with
    real procurement activity but zero awards shows up as a flagged gap
    instead of silently looking identical to a county with no activity at
    all. Refetching PPRA live on every page view isn't viable (a multi-MB
    download + full parse), so update_procurement_promises populates this
    alongside the Promise records it creates.
    """
    # Below this many tenders, zero awards isn't remarkable -- most counties
    # simply haven't published much yet. Above it, silence starts looking
    # like a reporting gap worth a question, not noise.
    AWARD_GAP_TENDER_THRESHOLD = 10

    county = models.CharField(max_length=100)
    year = models.IntegerField()
    tenders_published = models.IntegerField(default=0)
    awards_recorded = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('county', 'year')
        verbose_name_plural = 'county procurement activity'

    def __str__(self):
        return f'{self.county} {self.year}: {self.tenders_published} tenders, {self.awards_recorded} awarded'

    @property
    def has_award_gap(self):
        return self.tenders_published >= self.AWARD_GAP_TENDER_THRESHOLD and self.awards_recorded == 0
