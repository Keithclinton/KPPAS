# ETL script for Agriculture sector: crop yield data from KilimoSTAT, the
# Ministry of Agriculture and Livestock Development's open data platform.
# Real, live, county-disaggregated data -- no auth required.
# API docs: https://statistics.kilimo.go.ke/api/schema/ (OpenAPI)
#
# Sorghum is used as the yield indicator because, unlike maize or cash crops,
# it has reported records in every KPPAS pilot county (including urban/arid
# ones like Nairobi, Mombasa and Garissa where most other crops have none).
import requests

API_BASE = 'https://statistics.kilimo.go.ke/api'
CROP_YIELD_INDICATOR_ID = 1
YIELD_ITEM = 'Sorghum'

# statistics.kilimo.go.ke currently serves an expired TLS certificate;
# verification is disabled to match the rest of this ETL suite's handling
# of Kenyan government sites with broken chains (see health_etl.py, roads_etl.py).
VERIFY_TLS = False

# KilimoSTAT's area names are upper-case and don't always match the county's
# official spelling (notably "GARRISA" for Garissa).
COUNTY_TO_AREA_NAME = {
    'Nairobi': 'NAIROBI',
    'Kisumu': 'KISUMU',
    'Mombasa': 'MOMBASA',
    'Nakuru': 'NAKURU',
    'Garissa': 'GARRISA',
}


def fetch_latest_sorghum_yield(county, area_name):
    """Return {'year': int, 'value': float} for the most recent recorded
    sorghum yield (tonnes/hectare) in this county, or None if unavailable."""
    params = {
        'indicator_id': CROP_YIELD_INDICATOR_ID,
        'item_name': YIELD_ITEM,
        'area_name': area_name,
        'ordering': '-time_period',
        'page_size': 1,
    }
    response = requests.get(f'{API_BASE}/data/', params=params, timeout=30, verify=VERIFY_TLS)
    response.raise_for_status()
    results = response.json().get('results', [])
    if not results:
        return None
    record = results[0]
    return {'year': int(record['time_period']), 'value': float(record['data_value'])}


def fetch_yields(counties):
    """Return {county: {'year': int, 'value': float}} for counties with data."""
    results = {}
    for county in counties:
        area_name = COUNTY_TO_AREA_NAME.get(county)
        if not area_name:
            continue
        record = fetch_latest_sorghum_yield(county, area_name)
        if record:
            results[county] = record
    return results


def main():
    yields = fetch_yields(COUNTY_TO_AREA_NAME.keys())
    print(f"Fetched sorghum yield for {len(yields)} counties.")
    for county, record in sorted(yields.items()):
        print(f"  {county}: {record['value']} t/ha ({record['year']})")


if __name__ == '__main__':
    main()
