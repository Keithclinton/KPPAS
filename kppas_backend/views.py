import csv
import io

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import PublicFeedbackForm, CountyScoreUploadForm
from .models.public_feedback import PublicFeedback, SECTOR_CHOICES
from .models.scorecard_models import (
    CountyScore, DataSource, RemediationAction, PILOT_COUNTIES, ADMIN_CONTACT_EMAIL,
)
from .scoring import compute_score_and_status, compute_perception_status

USSD_SECTORS = [choice for choice, _ in SECTOR_CHOICES if choice != 'General']


def data_access_view(request):
    return render(request, 'data_access.html', {'contact_email': ADMIN_CONTACT_EMAIL})


def feedback_view(request):
    message = ''
    county = request.POST.get('county') or request.GET.get('county') or ''
    sector = request.POST.get('sector') or request.GET.get('sector') or ''

    if request.method == 'POST':
        form = PublicFeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            message = 'Thank you for your feedback!'
            county = form.cleaned_data['county']
            sector = form.cleaned_data['sector']
            form = PublicFeedbackForm(initial={'county': county, 'sector': sector})
    else:
        form = PublicFeedbackForm(initial={'county': county, 'sector': sector} if county and sector else None)

    context = {
        'form': form,
        'message': message,
        'county': county,
        'sector': sector,
        'counties': PILOT_COUNTIES,
        'sectors': USSD_SECTORS,
    }

    if county and sector:
        periods = _get_available_periods()
        year, quarter = _resolve_period(request, periods)
        context['period'] = (year, quarter)
        if year is not None:
            context['official_score'] = (
                CountyScore.objects.filter(county=county, sector=sector, year=year, quarter=quarter)
                .select_related('data_source')
                .first()
            )
        context['perception'] = _get_perception(county, sector)

    return render(request, 'feedback_form.html', context)


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

    created, updated, errors, locked_notes = 0, 0, [], []

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

                existing = CountyScore.objects.filter(
                    county=county, sector=sector, quarter=quarter, year=year
                ).first()
                if existing and existing.is_signed:
                    target = existing.target
                    locked_notes.append(
                        f'Row {row_number} ({county}): target is locked (signed '
                        f'{existing.signed_at:%Y-%m-%d}) -- kept at {target}, only value updated.'
                    )

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

    return {'created': created, 'updated': updated, 'errors': errors, 'locked_notes': locked_notes}


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
            CountyScore.objects.filter(year=year, quarter=quarter)
            .select_related('data_source')
            .order_by('county', 'sector')
        )

    for row in scores:
        row.perception = _get_perception(row.county, row.sector)
        row.remediation_actions = (
            list(row.actions.order_by('deadline')) if row.status == 'red' else []
        )

    counties = sorted({s.county for s in scores})
    county_sections = [
        {'county': county, 'rows': [s for s in scores if s.county == county]}
        for county in counties
    ]

    return render(request, 'dashboard.html', {
        'county_sections': county_sections,
        'periods': periods,
        'year': year,
        'quarter': quarter,
    })


def rankings_view(request):
    periods = _get_available_periods()
    year, quarter = _resolve_period(request, periods)

    county_scores = {}
    if year is not None:
        for s in CountyScore.objects.filter(year=year, quarter=quarter):
            county_scores.setdefault(s.county, []).append(s.score)

    rankings = sorted(
        (
            {
                'county': county,
                'average_score': sum(scores) / len(scores),
                'sector_count': len(scores),
            }
            for county, scores in county_scores.items()
        ),
        key=lambda r: r['average_score'],
        reverse=True,
    )
    for position, row in enumerate(rankings, start=1):
        row['rank'] = position

    return render(request, 'rankings.html', {
        'rankings': rankings,
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
        row.remediation_actions = (
            list(row.actions.order_by('deadline')) if row.status == 'red' else []
        )

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


def _ussd_pick(options, raw_choice):
    try:
        index = int(raw_choice) - 1
    except (TypeError, ValueError):
        return None
    return options[index] if 0 <= index < len(options) else None


def _ussd_pick_rating(raw_choice):
    try:
        value = int(raw_choice)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 5 else None


@csrf_exempt
@require_POST
def ussd_feedback_view(request):
    """
    Africa's Talking-shaped USSD webhook (SMS/USSD channel for citizens without
    internet access, per the KPPAS community-level feedback design).

    Stateless by design: Africa's Talking resends the full accumulated `text`
    (each step separated by '*') on every request, so the current step is
    derived from how many steps have been answered -- no session store needed.
    Point your USSD gateway's callback URL here once you have an account;
    set USSD_SHARED_SECRET in settings and require ?secret=... to lock it down.
    """
    shared_secret = getattr(settings, 'USSD_SHARED_SECRET', None)
    if shared_secret and request.GET.get('secret') != shared_secret:
        return HttpResponse('Forbidden', status=403)

    phone_number = request.POST.get('phoneNumber', '').strip()
    text = request.POST.get('text', '')
    steps = text.split('*') if text else []

    def respond(prefix, message):
        return HttpResponse(f'{prefix} {message}', content_type='text/plain')

    if len(steps) == 0:
        menu = '\n'.join(f'{i + 1}. {c}' for i, c in enumerate(PILOT_COUNTIES))
        return respond('CON', f'Welcome to KPPAS.\nWhich county?\n{menu}')

    county = _ussd_pick(PILOT_COUNTIES, steps[0])
    if county is None:
        return respond('END', 'Invalid county selection. Please dial in again.')

    if len(steps) == 1:
        menu = '\n'.join(f'{i + 1}. {s}' for i, s in enumerate(USSD_SECTORS))
        return respond('CON', f'Which sector?\n{menu}')

    sector = _ussd_pick(USSD_SECTORS, steps[1])
    if sector is None:
        return respond('END', 'Invalid sector selection. Please dial in again.')

    if len(steps) == 2:
        return respond('CON', 'Rate this service from 1 (worst) to 5 (best):')

    rating = _ussd_pick_rating(steps[2])
    if rating is None:
        return respond('END', 'Invalid rating. Please dial in again.')

    if len(steps) == 3:
        return respond('CON', 'Optional: reply with a short comment, or 0 to skip.')

    comment = steps[3].strip()
    if comment == '0':
        comment = ''

    PublicFeedback.objects.create(
        name=f'USSD {phone_number}'.strip() if phone_number else 'USSD caller',
        county=county,
        sector=sector,
        rating=rating,
        comment=comment or 'No comment provided.',
    )
    return respond('END', 'Thank you. Your feedback has been recorded.')
