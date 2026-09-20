from django.core.management.base import BaseCommand

from kppas_backend.models.public_feedback import PublicFeedback

# (name, county, sector, comment) -- illustrative, deliberately doesn't cover
# every county/sector combo so the "no citizen feedback yet" state has something to show too
FEEDBACK_SAMPLES = [
    ('Mary W.', 'Nairobi', 'Health', 'Health center wait times have improved this quarter.'),
    ('John K.', 'Nairobi', 'Roads', 'Potholes on Thika road still not fixed.'),
    ('Grace A.', 'Kisumu', 'Water', 'Water supply is intermittent but better than last year.'),
    ('Peter O.', 'Kisumu', 'Agriculture', 'Extension officers visited our farm, very helpful.'),
    ('Fatuma S.', 'Mombasa', 'Housing', 'Affordable housing units promised but none delivered here.'),
    ('Ali H.', 'Mombasa', 'Health', 'New clinic equipment, noticeable improvement.'),
    ('Susan N.', 'Nakuru', 'Roads', 'County roads graded recently, big improvement.'),
    ('James M.', 'Nakuru', 'Water', 'Water trucking helps but borehole repair still pending.'),
    ('Halima A.', 'Garissa', 'Health', 'Still long distances to nearest health facility.'),
    ('Mohamed I.', 'Garissa', 'Agriculture', 'Drought-resistant seeds distribution was timely.'),
    ('Lucy N.', 'Nairobi', 'Education', 'New textbooks arrived but classrooms still overcrowded.'),
    ('Brian O.', 'Kisumu', 'Governance', 'Bribes still requested for business permits at county offices.'),
    ('Esther K.', 'Nakuru', 'Governance', 'County assembly held public participation forums as promised this term.'),
    ('David M.', 'Mombasa', 'Education', 'New teachers posted to our school, class sizes more manageable.'),
]


class Command(BaseCommand):
    help = 'Seed demo citizen feedback data for the 5 pilot counties.'

    def handle(self, *args, **options):
        feedback_created = 0
        for name, county, sector, comment in FEEDBACK_SAMPLES:
            _, was_created = PublicFeedback.objects.get_or_create(
                name=name, county=county, sector=sector, comment=comment,
            )
            feedback_created += was_created

        self.stdout.write(self.style.SUCCESS(f'Seeded demo data: {feedback_created} feedback rows created.'))
