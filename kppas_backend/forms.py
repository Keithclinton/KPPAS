from django import forms
from .models.public_feedback import PublicFeedback
from .models.scorecard_models import DataSource, PILOT_COUNTIES

class PublicFeedbackForm(forms.ModelForm):
    county = forms.ChoiceField(choices=[(c, c) for c in PILOT_COUNTIES])

    class Meta:
        model = PublicFeedback
        fields = ['name', 'county', 'sector', 'rating', 'comment']


class CountyScoreUploadForm(forms.Form):
    sector = forms.CharField(max_length=100)
    quarter = forms.CharField(max_length=10)
    year = forms.IntegerField()
    label = forms.CharField(max_length=200)
    source_type = forms.ChoiceField(choices=DataSource.SOURCE_TYPE_CHOICES)
    trust_tier = forms.ChoiceField(choices=DataSource.TRUST_TIER_CHOICES)
    origin_url = forms.URLField(required=False)
    notes = forms.CharField(widget=forms.Textarea, required=False)
    file = forms.FileField()
