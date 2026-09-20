from django import forms
from .models.public_feedback import PublicFeedback
from .models.promise_registry import PromiseComment
from .models.scorecard_models import PILOT_COUNTIES

class PublicFeedbackForm(forms.ModelForm):
    county = forms.ChoiceField(choices=[(c, c) for c in PILOT_COUNTIES])

    class Meta:
        model = PublicFeedback
        fields = ['name', 'county', 'sector', 'comment']


class PromiseCommentForm(forms.ModelForm):
    class Meta:
        model = PromiseComment
        fields = ['name', 'text']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Name (optional)'}),
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add to the discussion...'}),
        }
