from datetime import date


def aggregate_promise_scores(category_scores):
    """category_scores: iterable of (category, score_or_None) pairs, where
    score is 'green'/'amber'/'red' from a promise's verification for the
    quarter in question, or None if it hasn't been verified yet that
    quarter. Returns per-category counts, sorted by category, per the
    Promise Registry's Step 4 (aggregate by category/county/ministry)."""
    buckets = {}
    for category, score in category_scores:
        bucket = buckets.setdefault(category, {'green': 0, 'amber': 0, 'red': 0, 'unverified': 0})
        bucket[score if score else 'unverified'] += 1
    return [{'category': category, **counts} for category, counts in sorted(buckets.items())]


def infer_status_from_verification(score, stated_deadline):
    """Map a quarterly green/amber/red verification onto the promise's own
    lifecycle status. Whether the deadline has actually passed matters:
    green before the deadline means on-track (still in_progress), not
    delivered; red before the deadline means badly behind (delayed), not
    broken -- broken is reserved for a deadline that's actually been missed,
    the same 'don't presume the worst early' rule the PPRA ingestion's own
    status inference follows."""
    deadline_passed = stated_deadline is not None and date.today() > stated_deadline
    if score == 'green':
        return 'delivered' if deadline_passed else 'in_progress'
    if score == 'amber':
        return 'delayed'
    if score == 'red':
        return 'broken' if deadline_passed else 'delayed'
    return None
