from django.conf import settings
from django.db import models

# The 5 counties KPPAS is piloted in -- shared by the demo seed data,
# the real ETL commands, and the USSD county menu.
PILOT_COUNTIES = ['Nairobi', 'Kisumu', 'Mombasa', 'Nakuru', 'Garissa']


class Sector(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Subtopic(models.Model):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='subtopics')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.sector.name} - {self.name}"

class DashboardLink(models.Model):
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name='dashboards')
    url = models.URLField()
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=50, default='metabase', help_text='e.g., metabase, redash, etc.')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.type})"


class DataSource(models.Model):
    SOURCE_TYPE_CHOICES = [
        ("api", "API"),
        ("csv_upload", "CSV Upload"),
        ("manual_entry", "Manual Entry"),
        ("scrape", "Scrape"),
        ("citizen_survey", "Citizen Survey"),
    ]
    TRUST_TIER_CHOICES = [
        ("verified", "Verified"),
        ("provisional", "Provisional"),
        ("unverified", "Unverified"),
    ]

    label = models.CharField(max_length=200)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    trust_tier = models.CharField(max_length=20, choices=TRUST_TIER_CHOICES)
    origin_url = models.URLField(blank=True)
    file = models.FileField(upload_to="data_uploads/", blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    imported_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.label} ({self.source_type}, {self.trust_tier})"


class CountyScore(models.Model):
    county = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    value = models.FloatField()
    target = models.FloatField()
    score = models.FloatField()
    status = models.CharField(max_length=10)  # green, amber, red
    quarter = models.CharField(max_length=10)
    year = models.IntegerField()
    data_source = models.ForeignKey(
        DataSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="county_scores"
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="signed_scores"
    )

    class Meta:
        unique_together = ("county", "sector", "quarter", "year")

    @property
    def is_signed(self):
        return self.signed_at is not None


class RemediationAction(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]

    county_score = models.ForeignKey(CountyScore, on_delete=models.CASCADE, related_name="actions")
    bottleneck = models.TextField(help_text="What is causing the red/underperforming indicator?")
    responsible_party = models.CharField(max_length=200)
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.county_score} -> {self.responsible_party} (due {self.deadline})"
