from django import forms
from .models.public_feedback import PublicFeedback

class PublicFeedbackForm(forms.ModelForm):
    class Meta:
        model = PublicFeedback
        fields = ['name', 'county', 'rating', 'comment']
