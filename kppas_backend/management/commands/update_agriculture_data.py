import os
import sys

from django.core.management.base import BaseCommand
from django.utils import timezone

from kppas_backend.models.scorecard_models import CountyScore, DataSource, PILOT_COUNTIES
from kppas_backend.scoring import compute_score_and_status

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../etl')))
import agriculture_etl

# Illustrative policy benchmark: KALRO-recommended attainable yield for
# improved sorghum varieties under normal rainfall in Kenya (t/ha).
SORGHUM_YIELD_TARGET = 1.5

# A county's latest sorghum yield record can lag the current year -- KilimoSTAT
# reporting cadence isn't uniform across counties, so surface how stale it is.
STALE_YEARS_WARNING = 2


class Command(BaseCommand):
    help = 'Fetch real crop yield data (KilimoSTAT) and update CountyScore for pilot counties.'

    def handle(self, *args, **options):
        self.stdout.write('Fetching KilimoSTAT sorghum yield data for Kenya...')
        yields = agriculture_etl.fetch_yields(PILOT_COUNTIES)

        if not yields:
            self.stdout.write(self.style.WARNING('No crop yield data found for pilot counties.'))
            return

        now = timezone.now()
        quarter = f'Q{(now.month - 1) // 3 + 1}'
        year = now.year

        data_source, _ = DataSource.objects.update_or_create(
            label='KilimoSTAT - Kenya Agricultural Open Data Platform',
            source_type='api',
            defaults={
                'trust_tier': 'provisional',
                'origin_url': 'https://statistics.kilimo.go.ke/',
                'notes': (
                    'Sorghum crop yield (tonnes/hectare) per county from KilimoSTAT '
                    '(Ministry of Agriculture and Livestock Development). Sorghum is used '
                    'because it is the only crop with reported data in every pilot county, '
                    'including urban/arid ones. Figures are annual and reporting cadence '
                    'varies by county, so the latest available year may lag the current one.'
                ),
            },
        )

        created, updated = 0, 0
        for county, record in yields.items():
            if now.year - record['year'] >= STALE_YEARS_WARNING:
                self.stdout.write(self.style.WARNING(
                    f"{county}: latest sorghum yield record is from {record['year']} -- stale."
                ))
            score, status = compute_score_and_status(record['value'], SORGHUM_YIELD_TARGET)
            _, was_created = CountyScore.objects.update_or_create(
                county=county, sector='Agriculture', quarter=quarter, year=year,
                defaults={
                    'value': record['value'],
                    'target': SORGHUM_YIELD_TARGET,
                    'score': score,
                    'status': status,
                    'data_source': data_source,
                },
            )
            created += was_created
            updated += not was_created
            self.stdout.write(
                f"  {county}: {record['value']} t/ha ({record['year']}) -> {status}"
            )

        self.stdout.write(self.style.SUCCESS(
            f'Agriculture data updated for {quarter} {year}: {created} created, {updated} updated.'
        ))
