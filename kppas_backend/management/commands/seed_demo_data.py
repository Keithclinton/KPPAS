from django.core.management.base import BaseCommand

from kppas_backend.models.public_feedback import PublicFeedback
from kppas_backend.models.scorecard_models import CountyScore, DataSource, PILOT_COUNTIES
from kppas_backend.scoring import compute_score_and_status

# (sector, value, target) per county, loosely illustrative of BETA Agenda priorities.
# Governance value is "audit query resolution rate (%)" -- the one self-reported
# administrative number that's at least independently auditable (per KENAO oversight,
# see doc S5.1); citizen perception is expected to matter more here than elsewhere.
SECTOR_TARGETS = {
    'Health': (78, 90),
    'Agriculture': (62, 80),
    'Housing': (40, 100),
    'Roads': (70, 85),
    'Water': (55, 75),
    'Education': (82, 92),
    'Governance': (45, 80),
}

QUARTER = 'Q1'
YEAR = 2026

# (name, county, sector, rating, comment) -- illustrative, deliberately doesn't cover
# every county/sector combo so the "no citizen feedback yet" state has something to show too
FEEDBACK_SAMPLES = [
    ('Mary W.', 'Nairobi', 'Health', 4, 'Health center wait times have improved this quarter.'),
    ('John K.', 'Nairobi', 'Roads', 2, 'Potholes on Thika road still not fixed.'),
    ('Grace A.', 'Kisumu', 'Water', 3, 'Water supply is intermittent but better than last year.'),
    ('Peter O.', 'Kisumu', 'Agriculture', 5, 'Extension officers visited our farm, very helpful.'),
    ('Fatuma S.', 'Mombasa', 'Housing', 2, 'Affordable housing units promised but none delivered here.'),
    ('Ali H.', 'Mombasa', 'Health', 4, 'New clinic equipment, noticeable improvement.'),
    ('Susan N.', 'Nakuru', 'Roads', 5, 'County roads graded recently, big improvement.'),
    ('James M.', 'Nakuru', 'Water', 3, 'Water trucking helps but borehole repair still pending.'),
    ('Halima A.', 'Garissa', 'Health', 2, 'Still long distances to nearest health facility.'),
    ('Mohamed I.', 'Garissa', 'Agriculture', 4, 'Drought-resistant seeds distribution was timely.'),
    ('Lucy N.', 'Nairobi', 'Education', 3, 'New textbooks arrived but classrooms still overcrowded.'),
    ('Brian O.', 'Kisumu', 'Governance', 1, 'Bribes still requested for business permits at county offices.'),
    ('Esther K.', 'Nakuru', 'Governance', 4, 'County assembly held public participation forums as promised this term.'),
    ('David M.', 'Mombasa', 'Education', 4, 'New teachers posted to our school, class sizes more manageable.'),
]


class Command(BaseCommand):
    help = 'Seed demo CountyScore data for the 5 pilot counties.'

    def handle(self, *args, **options):
        data_source, _ = DataSource.objects.update_or_create(
            label='Demo seed data',
            source_type='manual_entry',
            defaults={'trust_tier': 'provisional', 'notes': 'Illustrative data for demo purposes.'},
        )

        created, updated = 0, 0
        for county in PILOT_COUNTIES:
            for sector, (value, target) in SECTOR_TARGETS.items():
                score, status = compute_score_and_status(value, target)
                _, was_created = CountyScore.objects.update_or_create(
                    county=county,
                    sector=sector,
                    quarter=QUARTER,
                    year=YEAR,
                    defaults={
                        'value': value,
                        'target': target,
                        'score': score,
                        'status': status,
                        'data_source': data_source,
                    },
                )
                created += was_created
                updated += not was_created

        feedback_created = 0
        for name, county, sector, rating, comment in FEEDBACK_SAMPLES:
            _, was_created = PublicFeedback.objects.get_or_create(
                name=name, county=county, sector=sector, comment=comment,
                defaults={'rating': rating},
            )
            feedback_created += was_created

        self.stdout.write(self.style.SUCCESS(
            f'Seeded demo data: {created} created, {updated} updated. '
            f'{feedback_created} feedback rows created.'
        ))
