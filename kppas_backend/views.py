from django.shortcuts import render, redirect
from .forms import PublicFeedbackForm


def feedback_view(request):
    message = ''
    if request.method == 'POST':
        form = PublicFeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            message = 'Thank you for your feedback!'
            form = PublicFeedbackForm()  # Reset form
    else:
        form = PublicFeedbackForm()
    return render(request, 'feedback_form.html', {'form': form, 'message': message})
