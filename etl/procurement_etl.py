# ETL script for Promise Registry ingestion: county government contract
# awards from the PPRA Public Procurement Information Portal (PPIP),
# distributed as OCDS (Open Contracting Data Standard) releases by the
# Open Contracting Partnership's data registry. Real, live, structured
# data -- no auth required, updated daily upstream.
# Publication: https://data.open-contracting.org/en/publication/147
#
# We treat each award as a government *commitment* worth logging in the
# Promise Registry: money has been contractually committed to deliver
# something, by a named county buyer, on a stated timeline. This script
# only performs Step 1 (collection) of the KPPAS promise-tracking
# methodology -- it never marks a promise 'delivered' or 'broken', since
# an award record is evidence a commitment was *made*, not evidence it
# was *kept*. That verification is a separate, human, quarterly step.
import gzip
import json
from datetime import datetime, timezone

import requests

REGISTRY_BASE = 'https://data.open-contracting.org/en/publication/147/download'

# PPIP buyer names for county government executives all follow "<County>
# County Government" (confirmed consistent -- same casing -- across all 24
# counties with 2026 awards, not just the 5 pilot ones); county assemblies,
# NG-CDFs, water companies and national agencies operating in a county are
# deliberately excluded from this first pass to keep the buyer->county
# mapping unambiguous. Matching the suffix directly (rather than a fixed
# county-name list) means this needs no maintenance as more counties start
# publishing awards, and sidesteps ever having to get 47 counties' spelling/
# hyphenation exactly right ("Trans Nzoia", "Murang'a", "Elgeyo-Marakwet", ...).
_COUNTY_GOVERNMENT_SUFFIX = 'county government'


def _extract_county(buyer_name):
    stripped = (buyer_name or '').strip()
    if not stripped.lower().endswith(_COUNTY_GOVERNMENT_SUFFIX):
        return None
    return stripped[:-len(_COUNTY_GOVERNMENT_SUFFIX)].strip()

CATEGORY_KEYWORDS = [
    ('Water', ['water', 'borehole', 'sewerage', 'sanitation', 'dam ']),
    ('Roads', ['road', 'bridge', 'bitumen', 'tarmac', 'culvert']),
    ('Health', ['hospital', 'health', 'dispensary', 'clinic', 'maternity']),
    ('Education', ['school', 'education', 'classroom', 'polytechnic', 'ecde']),
    ('Agriculture', ['agriculture', 'irrigation', 'farm', 'livestock', 'agro']),
    ('Housing', ['housing', 'estate', 'settlement']),
]

# Titles name the project type up front and then string together a long list
# of landmark names to pin down the location (e.g. "... floodlights in Kware
# Kwa Chris, ... near Borehole Area, Chepseon ..."). A sector keyword hiding
# in that landmark list would otherwise outrank the project's real type, so
# these general county-infrastructure jobs are matched first.
INFRASTRUCTURE_OVERRIDE_KEYWORDS = ['floodlight', 'streetlight', 'highmast', 'motorbike shed']


def _guess_category(title, procurement_category):
    lowered = (title or '').lower()
    if any(kw in lowered for kw in INFRASTRUCTURE_OVERRIDE_KEYWORDS):
        return 'Infrastructure'
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return category
    if procurement_category == 'works':
        return 'Infrastructure'
    return 'Other'


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def fetch_releases(year):
    """Yield raw OCDS release dicts (one per JSONL line) for the given year."""
    url = f'{REGISTRY_BASE}?name={year}.jsonl.gz'
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    for line in gzip.decompress(response.content).decode('utf-8', errors='replace').splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def fetch_county_activity(year, counties=None):
    """Return {county: {'tenders': n, 'awards': n}} -- counts *every*
    published tender per county, not just the ones with an award (which is
    all fetch_county_awards sees). A county can be genuinely active on PPRA
    with nothing awarded yet; without this, that looks identical to a county
    with no procurement activity at all."""
    wanted = {c.lower() for c in counties} if counties else None
    activity = {}
    for release in fetch_releases(year):
        buyer_name = (release.get('buyer') or {}).get('name', '').strip()
        county = _extract_county(buyer_name)
        if county is None:
            continue
        if wanted is not None and county.lower() not in wanted:
            continue
        bucket = activity.setdefault(county, {'tenders': 0, 'awards': 0})
        bucket['tenders'] += 1
        if release.get('awards'):
            bucket['awards'] += 1
    return activity


def fetch_county_awards(year, counties=None):
    """Return a list of normalized award dicts for county-government buyers.

    If `counties` is given, only those (matched case-insensitively) are
    included; if None, every county with awarded contracts this year is
    included.

    Each dict: ocid, award_id, title, county, buyer_name, amount, currency,
    supplier_name, contract_start, contract_end, date_made, category.
    """
    wanted = {c.lower() for c in counties} if counties else None
    results = []

    for release in fetch_releases(year):
        buyer_name = (release.get('buyer') or {}).get('name', '').strip()
        county = _extract_county(buyer_name)
        if county is None:
            continue
        if wanted is not None and county.lower() not in wanted:
            continue

        tender = release.get('tender') or {}
        release_date = _parse_date(release.get('date'))
        # contracts[] carries dateSigned -- the actual day the county committed --
        # keyed to its award via awardID; fall back to the release date if absent.
        signed_by_award = {
            c.get('awardID'): _parse_date(c.get('dateSigned'))
            for c in (release.get('contracts') or [])
        }

        for award in release.get('awards') or []:
            value = award.get('value') or {}
            suppliers = award.get('suppliers') or []
            contract_period = award.get('contractPeriod') or {}

            results.append({
                'ocid': release.get('ocid'),
                'award_id': award.get('id'),
                'title': award.get('title') or tender.get('title') or '(untitled award)',
                'county': county,
                'buyer_name': buyer_name,
                'amount': value.get('amount'),
                'currency': value.get('currency'),
                'supplier_name': suppliers[0].get('name') if suppliers else None,
                'contract_start': _parse_date(contract_period.get('startDate')),
                'contract_end': _parse_date(contract_period.get('endDate')),
                'date_made': signed_by_award.get(award.get('id')) or release_date,
                'category': _guess_category(award.get('title') or tender.get('title'), tender.get('mainProcurementCategory')),
            })

    return results


def infer_lifecycle_status(contract_start, contract_end):
    """Conservative status from contract dates alone -- never 'delivered',
    'delayed' or 'broken' without human verification (see module docstring)."""
    today = datetime.now(timezone.utc).date()
    if contract_start and today < contract_start:
        return 'pending'
    if contract_end and today > contract_end:
        return 'in_progress'  # past its own deadline; flag for verification, don't assume the worst
    return 'in_progress' if contract_start else 'pending'


def main():
    year = datetime.now().year
    awards = fetch_county_awards(year)  # every county with awards this year
    print(f'Fetched {len(awards)} county-government awards for {year} across {len({a["county"] for a in awards})} counties.')
    for a in awards[:10]:
        print(f"  [{a['county']}] {a['title'][:70]} -- {a['amount']} {a['currency']} ({a['category']})")


if __name__ == '__main__':
    main()
