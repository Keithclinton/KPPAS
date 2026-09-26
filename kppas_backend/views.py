from collections import Counter
from datetime import datetime

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import PublicFeedbackForm, PromiseCommentForm
from .models.public_feedback import PublicFeedback, SECTOR_CHOICES
from .models.promise_registry import Promise, PromiseVerification, PromiseComment, CountyProcurementActivity
from .models.scorecard_models import PILOT_COUNTIES, ADMIN_CONTACT_EMAIL
from .scoring import aggregate_promise_scores

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
        context['perception'] = _get_perception(county, sector)

    return render(request, 'feedback_form.html', context)


def _county_label(county):
    return 'National Government' if county == 'national' else county


def _county_db_value(county):
    """URLs use the literal string 'national' for national-government pages
    (readable, and reuses every county-scoped view/template as-is); the
    database uses '' for the same thing, matching Promise.county's own
    "blank means national" convention. Translate at the view boundary so
    nothing downstream needs to know both spellings exist."""
    return '' if county == 'national' else county


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


def promise_registry_view(request):
    # Shows whatever counties actually have logged promises, not just
    # PILOT_COUNTIES -- procurement ingestion can cover any county with
    # awarded contracts (see update_procurement_promises --all-counties),
    # so this page needs to reflect that rather than a fixed 5-county list.
    promise_stats = {
        row['county']: row
        for row in (
            Promise.objects.values('county')
            .annotate(
                count=Count('id'),
                delivered=Count('id', filter=Q(status='delivered')),
                broken=Count('id', filter=Q(status='broken')),
            )
        )
    }
    national_stats = promise_stats.pop('', None)
    # A county can be active on PPRA (publishing tenders) with nothing
    # awarded yet, so it'd have zero promises and be invisible above --
    # folding in CountyProcurementActivity surfaces it anyway, flagged,
    # instead of it looking identical to a county with no activity at all.
    activity_stats = {a.county: a for a in CountyProcurementActivity.objects.filter(year=datetime.now().year)}

    counties = []
    for county in set(promise_stats) | set(activity_stats):
        stats = promise_stats.get(county, {'count': 0, 'delivered': 0, 'broken': 0})
        activity = activity_stats.get(county)
        counties.append({
            'county': county,
            'count': stats['count'],
            'delivered': stats['delivered'],
            'broken': stats['broken'],
            'tenders_published': activity.tenders_published if activity else None,
            'has_award_gap': activity.has_award_gap if activity else False,
        })
    # Most promises first -- that's where the story is; alphabetical buries
    # West Pokot's 335 promises at the same visual weight as Kisumu's 1.
    counties.sort(key=lambda row: (-row['count'], row['county']))

    national_row = None
    if national_stats:
        national_row = {
            'county': 'national',
            'label': 'National government',
            'count': national_stats['count'],
            'delivered': national_stats['delivered'],
            'broken': national_stats['broken'],
        }

    total_promises = sum(row['count'] for row in counties) + (national_stats['count'] if national_stats else 0)

    return render(request, 'promise_registry.html', {
        'counties': counties,
        'national_row': national_row,
        'counties_with_promises': sum(1 for row in counties if row['count'] > 0),
        'counties_with_gap': sum(1 for row in counties if row['has_award_gap']),
        'total_counties': len(counties),
        'total_promises': total_promises,
    })


def _attach_latest_verification(promises):
    for p in promises:
        # PromiseVerification.Meta.ordering is already -year, -quarter, so the
        # prefetched cache is already in the right order -- .first() here
        # would issue a fresh query per promise and defeat prefetch_related.
        verifications = list(p.verifications.all())
        p.latest_verification = verifications[0] if verifications else None
    return promises


def county_promises_view(request, county):
    county_value = _county_db_value(county)
    all_promises = _attach_latest_verification(list(
        Promise.objects.filter(county=county_value)
        .select_related('source')
        .prefetch_related('verifications')
        .annotate(comment_count=Count('comments', filter=Q(comments__is_hidden=False)))
        .order_by('category', '-date_made')
    ))

    # Lets the brief page's stat tiles link straight to "just the broken
    # ones" etc. -- filters the table only; the rollup below still reflects
    # every promise so it stays a full picture regardless of this filter.
    status_filter = request.GET.get('status') or ''
    promises = [p for p in all_promises if p.status == status_filter] if status_filter else all_promises

    periods = list(
        PromiseVerification.objects.filter(promise__county=county_value)
        .order_by('-year', '-quarter')
        .values_list('year', 'quarter')
        .distinct()
    )
    year, quarter = _resolve_period(request, periods)

    rollup = []
    if year is not None:
        category_scores = []
        for p in all_promises:
            match = next((v for v in p.verifications.all() if v.year == year and v.quarter == quarter), None)
            category_scores.append((p.category, match.score if match else None))
        rollup = aggregate_promise_scores(category_scores)

    return render(request, 'county_promises.html', {
        'county': county,
        'county_label': _county_label(county),
        'promises': promises,
        'status_filter': status_filter,
        'rollup': rollup,
        'periods': periods,
        'year': year,
        'quarter': quarter,
    })


def _build_comment_tree(promise):
    """Attach .child_comments to each comment so the template can render
    replies recursively, without N+1 queries per level."""
    comments = list(promise.comments.filter(is_hidden=False).order_by('posted_at'))
    by_parent = {}
    for c in comments:
        by_parent.setdefault(c.parent_id, []).append(c)
    for c in comments:
        c.child_comments = by_parent.get(c.id, [])
    return by_parent.get(None, [])


def promise_detail_view(request, county, promise_id):
    promise = get_object_or_404(
        Promise.objects.select_related('source').prefetch_related('verifications'),
        pk=promise_id, county=_county_db_value(county),
    )

    if request.method == 'POST':
        form = PromiseCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.promise = promise
            parent_id = request.POST.get('parent_id')
            if parent_id:
                # Only allow replying to a comment that's actually on this
                # promise -- ignore/drop a tampered parent_id rather than
                # letting a reply attach to an unrelated promise's thread.
                comment.parent = promise.comments.filter(pk=parent_id).first()
            comment.save()
            return redirect('promise_detail', county=county, promise_id=promise_id)
    else:
        form = PromiseCommentForm()

    return render(request, 'promise_detail.html', {
        'county': county,
        'county_label': _county_label(county),
        'promise': promise,
        'verifications': list(promise.verifications.all()),
        'top_comments': _build_comment_tree(promise),
        'comment_count': promise.comments.filter(is_hidden=False).count(),
        'form': form,
    })


def county_brief_view(request, county):
    """A standalone, shareable summary -- headline numbers and the promises
    that most need attention up front -- meant to be sent as a link to a
    journalist or CSO rather than requiring them to dig through the full
    table. This is a live current-state snapshot (latest status per promise),
    not scoped to one quarter, so there's nothing to pick before it's useful."""
    county_value = _county_db_value(county)
    promises = _attach_latest_verification(list(
        Promise.objects.filter(county=county_value)
        .select_related('source')
        .prefetch_related('verifications')
    ))

    status_counts = Counter(p.status for p in promises)
    score_counts = Counter(p.latest_verification.score for p in promises if p.latest_verification)
    verified_count = sum(score_counts.values())
    unverified_count = len(promises) - verified_count

    flagged = sorted(
        (p for p in promises if p.status == 'broken' or (p.latest_verification and p.latest_verification.score == 'red')),
        key=lambda p: (p.stated_deadline is None, p.stated_deadline),
    )

    # National entities aren't tracked in CountyProcurementActivity yet (see
    # procurement_etl.fetch_national_awards) -- this naturally resolves to
    # None for county='national', which is correct: no gap data to show.
    activity = CountyProcurementActivity.objects.filter(county=county_value, year=datetime.now().year).first()

    return render(request, 'county_brief.html', {
        'county': county,
        'county_label': _county_label(county),
        'total': len(promises),
        'verified_count': verified_count,
        'unverified_count': unverified_count,
        'status_counts': status_counts,
        'score_counts': score_counts,
        'flagged': flagged,
        'activity': activity,
        'generated_at': timezone.now(),
    })


def _get_perception(county, sector):
    feedback = PublicFeedback.objects.filter(county=county, sector=sector)
    count = feedback.count()
    if not count:
        return None
    return {
        'count': count,
        'recent_comments': list(feedback.order_by('-submitted_at')[:3]),
    }


def _ussd_pick(options, raw_choice):
    try:
        index = int(raw_choice) - 1
    except (TypeError, ValueError):
        return None
    return options[index] if 0 <= index < len(options) else None


@csrf_exempt
@require_POST
def ussd_feedback_view(request):
    """
    Africa's Talking-shaped USSD webhook (SMS/USSD channel for citizens without
    internet access, per the Angazia Kenya community-level feedback design).

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
        return respond('CON', f'Welcome to Angazia Kenya.\nWhich county?\n{menu}')

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
        return respond('CON', 'Share your feedback as a short comment:')

    comment = steps[2].strip()
    if not comment:
        return respond('END', 'Comment cannot be empty. Please dial in again.')

    PublicFeedback.objects.create(
        name=f'USSD {phone_number}'.strip() if phone_number else 'USSD caller',
        county=county,
        sector=sector,
        comment=comment,
    )
    return respond('END', 'Thank you. Your feedback has been recorded.')
