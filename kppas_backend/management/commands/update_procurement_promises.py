import os
import sys

from django.core.management.base import BaseCommand

from kppas_backend.models.promise_registry import Promise, PromiseSource, CountyProcurementActivity
from kppas_backend.models.scorecard_models import PILOT_COUNTIES

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../etl')))
import procurement_etl


class Command(BaseCommand):
    help = (
        'Fetch county government contract awards from PPRA/PPIP (via the OCP OCDS '
        'data registry) and log each as a Promise Registry entry.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=None, help='Defaults to the current year.')
        parser.add_argument(
            '--all-counties', action='store_true',
            help='Fetch every county with awards this year, not just PILOT_COUNTIES.',
        )

    def handle(self, *args, **options):
        from datetime import datetime
        year = options['year'] or datetime.now().year
        counties = None if options['all_counties'] else PILOT_COUNTIES

        self.stdout.write(f'Fetching PPRA/PPIP contract awards for {year}'
                           f'{" (all counties)" if counties is None else ""}...')
        awards = procurement_etl.fetch_county_awards(year, counties)

        self.stdout.write('Fetching per-county tender activity (for the award-gap flag)...')
        activity = procurement_etl.fetch_county_activity(year, counties)
        for county, counts in activity.items():
            CountyProcurementActivity.objects.update_or_create(
                county=county, year=year,
                defaults={'tenders_published': counts['tenders'], 'awards_recorded': counts['awards']},
            )
        gaps = [c for c, a in activity.items() if a['tenders'] >= CountyProcurementActivity.AWARD_GAP_TENDER_THRESHOLD and a['awards'] == 0]
        if gaps:
            self.stdout.write(self.style.WARNING(
                f"Award gap flagged for {len(gaps)} county(s) (tenders published, nothing awarded yet): {', '.join(sorted(gaps))}"
            ))

        if not awards:
            self.stdout.write(self.style.WARNING('No county-government awards found.'))
            return

        created, updated, skipped = 0, 0, 0
        for a in awards:
            if not a['ocid'] or not a['award_id'] or not a['date_made']:
                skipped += 1
                continue

            source, _ = PromiseSource.objects.update_or_create(
                source_type='ppra',
                reference=f"{a['ocid']}::{a['award_id']}",
                defaults={
                    'title': f"PPRA contract award: {a['title'][:250]}",
                    'excerpt': (
                        f"Awarded to {a['supplier_name'] or 'unknown supplier'} for "
                        f"{a['amount']} {a['currency']} by {a['buyer_name']}."
                        if a['amount'] else f"Awarded by {a['buyer_name']}."
                    ),
                    'published_date': a['date_made'],
                },
            )

            source_fields = {
                'text': a['title'],
                'date_made': a['date_made'],
                'responsible_actor': a['buyer_name'],
                'county': a['county'],
                'category': a['category'],
                'stated_deadline': a['contract_end'],
            }

            existing = Promise.objects.filter(source=source).first()
            if existing:
                # A human verification may have already driven this promise's
                # status past the ETL's own pending/in_progress guess (see
                # PromiseVerification.save()) -- refresh the source-derived
                # fields on re-run, but never overwrite status here.
                Promise.objects.filter(pk=existing.pk).update(**source_fields)
            else:
                Promise.objects.create(
                    source=source,
                    status=procurement_etl.infer_lifecycle_status(a['contract_start'], a['contract_end']),
                    **source_fields,
                )
            created += not existing
            updated += bool(existing)

        self.stdout.write(self.style.SUCCESS(
            f'Procurement promises for {year}: {created} created, {updated} updated, {skipped} skipped (missing id).'
        ))
