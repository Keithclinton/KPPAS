from django.db import models

SECTOR_CHOICES = [
    ('Health', 'Health'),
    ('Agriculture', 'Agriculture'),
    ('Housing', 'Housing'),
    ('Roads', 'Roads'),
    ('Water', 'Water'),
    ('Education', 'Education'),
    ('Governance', 'Governance'),
    ('General', 'General'),
]

class PublicFeedback(models.Model):
    name = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    sector = models.CharField(max_length=100, choices=SECTOR_CHOICES, blank=True, default='General')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.county}) - {self.rating}"
