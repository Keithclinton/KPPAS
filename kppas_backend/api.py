from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
import os
import json

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
