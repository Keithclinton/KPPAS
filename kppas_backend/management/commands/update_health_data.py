import os
import json
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Run health ETL and update the database automatically.'

    def handle(self, *args, **options):
        # Import ETL and DB loader
        import sys
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../etl')))
        import health_etl
        import load_health_to_db

        self.stdout.write(self.style.NOTICE('Running health ETL...'))
        health_etl.main()
        self.stdout.write(self.style.SUCCESS('ETL complete. Data saved to health_data_prototype.json.'))

        self.stdout.write(self.style.NOTICE('Loading data into database...'))
        load_health_to_db.main()
        self.stdout.write(self.style.SUCCESS('Database update complete.'))
