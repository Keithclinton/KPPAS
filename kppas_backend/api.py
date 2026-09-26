from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models.api_key import ApiKey
from .models.promise_registry import Promise
from .models.scorecard_models import ADMIN_CONTACT_EMAIL

# Simple pagination guard -- this is a hand-rolled endpoint for a handful of
# licensed research/media users, not a public API expecting heavy traffic, so
# a flat cap is enough rather than building out full page-link pagination.
MAX_RESULTS = 500


def _authenticate(request):
    header = request.headers.get('Authorization', '')
    key = header[7:].strip() if header.startswith('Bearer ') else request.GET.get('api_key', '').strip()
    if not key:
        return None
    api_key = ApiKey.objects.filter(key=key, is_active=True).first()
    if api_key is not None:
        ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
    return api_key


def _serialize(promise):
    return {
        'id': promise.id,
        'text': promise.text,
        'county': promise.county or None,
        'category': promise.category,
        'responsible_actor': promise.responsible_actor,
        'date_made': promise.date_made,
        'stated_deadline': promise.stated_deadline,
        'deadline_text': promise.deadline_text,
        'status': promise.status,
        'source': {
            'type': promise.source.source_type,
            'title': promise.source.title,
            'reference': promise.source.reference,
            'url': promise.source.url or None,
        },
        'verifications': [
            {'quarter': v.quarter, 'year': v.year, 'score': v.score}
            for v in promise.verifications.all()
        ],
    }


@require_GET
def open_data_api(request):
    """Licensed data feed -- see data_access_view for how to request a key.
    Keys are issued by hand in the admin (ApiKey model), not self-serve."""
    api_key = _authenticate(request)
    if api_key is None:
        return JsonResponse({
            'error': 'This API requires a licensed API key (Authorization: Bearer <key>, or ?api_key=<key>).',
            'contact': f'To request access, email {ADMIN_CONTACT_EMAIL}.',
        }, status=403)

    promises = (
        Promise.objects.select_related('source')
        .prefetch_related('verifications')
        .order_by('-logged_at')
    )
    county = request.GET.get('county')
    if county is not None:
        # '' is a valid, meaningful filter here (national-level promises),
        # so this checks "was the param given at all", not "is it truthy".
        promises = promises.filter(county=county)

    results = [_serialize(p) for p in promises[:MAX_RESULTS]]
    return JsonResponse({'count': len(results), 'results': results})
