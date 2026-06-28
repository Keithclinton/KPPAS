import csv
import io

from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import render, redirect

from .forms import PublicFeedbackForm, CountyScoreUploadForm
from .models.public_feedback import PublicFeedback
from .models.scorecard_models import CountyScore, DataSource
from .scoring import compute_score_and_status, compute_perception_status


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


@staff_member_required
def upload_scores_view(request):
    results = None
    if request.method == 'POST':
        form = CountyScoreUploadForm(request.POST, request.FILES)
        if form.is_valid():
            results = _process_score_upload(form, request.user)
            form = CountyScoreUploadForm()
    else:
        form = CountyScoreUploadForm()
    return render(request, 'upload_scores.html', {'form': form, 'results': results})


def _process_score_upload(form, user):
    sector = form.cleaned_data['sector']
    quarter = form.cleaned_data['quarter']
    year = form.cleaned_data['year']
    uploaded_file = form.cleaned_data['file']

    decoded = io.TextIOWrapper(uploaded_file.file, encoding='utf-8')
    reader = csv.DictReader(decoded)
    fieldnames = {(name or '').strip().lower(): name for name in (reader.fieldnames or [])}

    created, updated, errors = 0, 0, []

    with transaction.atomic():
        data_source = DataSource.objects.create(
            label=form.cleaned_data['label'],
            source_type=form.cleaned_data['source_type'],
            trust_tier=form.cleaned_data['trust_tier'],
            origin_url=form.cleaned_data['origin_url'],
            notes=form.cleaned_data['notes'],
            file=form.cleaned_data['file'],
            uploaded_by=user if user.is_authenticated else None,
        )

        if 'county' not in fieldnames or 'value' not in fieldnames or 'target' not in fieldnames:
            errors.append('CSV must have county, value, and target columns.')
        else:
            for row_number, row in enumerate(reader, start=2):
                county = (row.get(fieldnames['county']) or '').strip()
                raw_value = (row.get(fieldnames['value']) or '').strip()
                raw_target = (row.get(fieldnames['target']) or '').strip()

                if not county:
                    errors.append(f'Row {row_number}: missing county.')
                    continue
                try:
                    value = float(raw_value)
                    target = float(raw_target)
                except ValueError:
                    errors.append(f'Row {row_number} ({county}): value/target must be numeric.')
                    continue

                score, status = compute_score_and_status(value, target)
                _, was_created = CountyScore.objects.update_or_create(
                    county=county,
                    sector=sector,
                    quarter=quarter,
                    year=year,
                    defaults={
                        'value': value,
                        'target': target,
                        'score': score,
                        'status': status,
                        'data_source': data_source,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

    return {'created': created, 'updated': updated, 'errors': errors}


def _get_available_periods():
    return list(
        CountyScore.objects.order_by('-year', '-quarter')
        .values_list('year', 'quarter')
        .distinct()
    )


def _resolve_period(request, periods):
    if not periods:
        return None, None
    requested_year = request.GET.get('year')
    requested_quarter = request.GET.get('quarter')
    if requested_year and requested_quarter:
        try:
            requested = (int(requested_year), requested_quarter)
        except ValueError:
            requested = None
        if requested in periods:
            return requested
    return periods[0]


def dashboard_view(request):
    periods = _get_available_periods()
    year, quarter = _resolve_period(request, periods)

    scores = []
    if year is not None:
        scores = list(
            CountyScore.objects.filter(year=year, quarter=quarter).select_related('data_source')
        )

    counties = sorted({s.county for s in scores})
    sectors = sorted({s.sector for s in scores})
    by_county_sector = {(s.county, s.sector): s for s in scores}

    grid = [
        {
            'county': county,
            'cells': [by_county_sector.get((county, sector)) for sector in sectors],
        }
        for county in counties
    ]

    return render(request, 'dashboard.html', {
        'sectors': sectors,
        'grid': grid,
        'periods': periods,
        'year': year,
        'quarter': quarter,
    })


def county_detail_view(request, county):
    periods = _get_available_periods()
    year, quarter = _resolve_period(request, periods)

    rows = []
    if year is not None:
        rows = list(
            CountyScore.objects.filter(county=county, year=year, quarter=quarter)
            .select_related('data_source')
            .order_by('sector')
        )

    for row in rows:
        row.perception = _get_perception(county, row.sector)

    return render(request, 'county_detail.html', {
        'county': county,
        'rows': rows,
        'periods': periods,
        'year': year,
        'quarter': quarter,
    })


def _get_perception(county, sector):
    feedback = PublicFeedback.objects.filter(county=county, sector=sector)
    aggregate = feedback.aggregate(average_rating=Avg('rating'), count=Count('id'))
    if not aggregate['count']:
        return None
    return {
        'average_rating': aggregate['average_rating'],
        'count': aggregate['count'],
        'status': compute_perception_status(aggregate['average_rating']),
        'recent_comments': list(feedback.order_by('-submitted_at')[:3]),
    }
