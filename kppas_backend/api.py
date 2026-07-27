from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
import os
import json

from .models.scorecard_models import CountyScore
from .scoring import GREEN_THRESHOLD, AMBER_THRESHOLD

@require_GET
@login_required
def health_data_api(request):
    # Serve the latest health data as JSON (requires login)
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'health_data_prototype.json')
    if not os.path.exists(data_path):
        return JsonResponse({'error': 'No data available'}, status=404)
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return JsonResponse(data, safe=False)


@require_GET
def open_data_api(request):
    """Public, unauthenticated feed of raw scores + the methodology used to compute them."""
    qs = CountyScore.objects.select_related('data_source').order_by('year', 'quarter', 'county', 'sector')

    year = request.GET.get('year')
    quarter = request.GET.get('quarter')
    if year:
        qs = qs.filter(year=year)
    if quarter:
        qs = qs.filter(quarter=quarter)

    results = [
        {
            'county': s.county,
            'sector': s.sector,
            'year': s.year,
            'quarter': s.quarter,
            'value': s.value,
            'target': s.target,
            'score': s.score,
            'status': s.status,
            'data_source': s.data_source.label if s.data_source else None,
            'trust_tier': s.data_source.trust_tier if s.data_source else None,
            'source_url': s.data_source.origin_url if s.data_source else None,
            'signed_at': s.signed_at.isoformat() if s.signed_at else None,
        }
        for s in qs
    ]

    return JsonResponse({
        'methodology': {
            'score_formula': 'score = value / target',
            'status_thresholds': {
                'green': f'score >= {GREEN_THRESHOLD}',
                'amber': f'score >= {AMBER_THRESHOLD}',
                'red': f'score < {AMBER_THRESHOLD}',
            },
            'note': (
                'Citizen perception (see /feedback/) is scored separately and is never blended '
                'into this official score -- see the county detail pages for both side by side.'
            ),
        },
        'count': len(results),
        'results': results,
    })
