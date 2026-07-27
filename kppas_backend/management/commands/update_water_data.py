import os
import sys

from django.core.management.base import BaseCommand
from django.utils import timezone

from kppas_backend.models.scorecard_models import CountyScore, DataSource, PILOT_COUNTIES
from kppas_backend.scoring import compute_score_and_status

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../etl')))
import water_etl

# Illustrative policy benchmark for % of water points functional.
WATER_FUNCTIONAL_TARGET = 80.0

# Below this many recorded water points, a county's percentage is a thin sample --
# WPDx coverage is driven by which NGOs/agencies have surveyed a given area, not
# uniform national coverage, so treat these numbers cautiously.
MIN_SAMPLE_SIZE = 30


class Command(BaseCommand):
    help = 'Fetch real water point functionality data (WPDx via HDX) and update CountyScore for pilot counties.'

    def handle(self, *args, **options):
        self.stdout.write('Fetching Water Point Data Exchange (WPDx) data for Kenya...')
        df = water_etl.fetch_water_points()
        stats = water_etl.aggregate_by_county(df, counties=PILOT_COUNTIES)

        if not stats:
            self.stdout.write(self.style.WARNING('No water point data found for pilot counties.'))
            return

        now = timezone.now()
        quarter = f'Q{(now.month - 1) // 3 + 1}'
        year = now.year

        data_source, _ = DataSource.objects.update_or_create(
            label='Water Point Data Exchange (WPDx) - Kenya',
            source_type='api',
            defaults={
                'trust_tier': 'provisional',
                'origin_url': 'https://data.humdata.org/dataset/wpdx_ken',
                'notes': (
                    'Aggregated water point functionality (% functional) per county from WPDx, '
                    'hosted on the Humanitarian Data Exchange. Coverage is uneven across counties '
                    '(NGO/government survey driven, not a census) -- treat low-sample counties '
                    'with caution.'
                ),
            },
        )

        created, updated = 0, 0
        for county, s in stats.items():
            if s['total_points'] < MIN_SAMPLE_SIZE:
                self.stdout.write(self.style.WARNING(
                    f"{county}: only {s['total_points']} water points recorded -- low-confidence sample."
                ))
            score, status = compute_score_and_status(s['pct_functional'], WATER_FUNCTIONAL_TARGET)
            _, was_created = CountyScore.objects.update_or_create(
                county=county, sector='Water', quarter=quarter, year=year,
                defaults={
                    'value': s['pct_functional'],
                    'target': WATER_FUNCTIONAL_TARGET,
                    'score': score,
                    'status': status,
                    'data_source': data_source,
                },
            )
            created += was_created
            updated += not was_created
            self.stdout.write(
                f"  {county}: {s['pct_functional']}% functional -> {status} "
                f"({s['functional_points']}/{s['total_points']} points)"
            )

        self.stdout.write(self.style.SUCCESS(
            f'Water data updated for {quarter} {year}: {created} created, {updated} updated.'
        ))
