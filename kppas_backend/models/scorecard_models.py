from django.db import models

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
from django.db import models

class CountyScore(models.Model):
    county = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    value = models.FloatField()
    target = models.FloatField()
    score = models.FloatField()
    status = models.CharField(max_length=10)  # green, amber, red
    quarter = models.CharField(max_length=10)
    year = models.IntegerField()

    class Meta:
        unique_together = ("county", "sector", "quarter", "year")

class CitizenFeedback(models.Model):
    county = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    rating = models.IntegerField()  # 1-5
    submitted_at = models.DateTimeField(auto_now_add=True)
