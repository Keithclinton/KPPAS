# Angazia Kenya

This project uses Django, Airflow, and PostgreSQL for the backend. ETL scripts are in the etl/ folder.

## Structure
- kppas_backend/: Django project
- etl/: ETL scripts
- requirements.txt: Python dependencies

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run Django server: `python manage.py runserver`
3. Configure Airflow for ETL jobs

## Next Steps
- Add sample dataset and scoring logic
- Design PostgreSQL schema
- Integrate Metabase dashboard
- Build citizen feedback API
- Prepare deployment
