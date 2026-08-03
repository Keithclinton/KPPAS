from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models.scorecard_models import ADMIN_CONTACT_EMAIL

@require_GET
def open_data_api(request):
    """Licensed data feed -- not publicly accessible. See data_access_view for the human-readable page."""
    return JsonResponse({
        'error': 'This API is a licensed data product and is not publicly accessible.',
        'contact': f'To request access, email {ADMIN_CONTACT_EMAIL}.',
    }, status=403)
