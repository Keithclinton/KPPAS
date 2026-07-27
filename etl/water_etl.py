# ETL script for Water sector: water point functionality data from the
# Water Point Data Exchange (WPDx), distributed via the Humanitarian Data
# Exchange (HDX). Real, live, county-disaggregated data -- no auth required.
# Dataset: https://data.humdata.org/dataset/wpdx_ken
import io

import requests

CKAN_PACKAGE_URL = 'https://data.humdata.org/api/3/action/package_show?id=wpdx_ken'

FUNCTIONAL_STATUSES = {
    'Functional',
    'Functional, not in use',
    'Functional, needs repair',
}


def _find_csv_resource(package):
    resources = package.get('resources', [])
    for resource in resources:
        if resource.get('format', '').upper() == 'CSV' and 'enhanced' in resource.get('name', '').lower():
            return resource['url']
    for resource in resources:
        if resource.get('format', '').upper() == 'CSV':
            return resource['url']
    return None


def fetch_water_points_csv_url():
    response = requests.get(CKAN_PACKAGE_URL, timeout=30)
    response.raise_for_status()
    package = response.json()['result']
    url = _find_csv_resource(package)
    if not url:
        raise RuntimeError('No CSV resource found in WPDx Kenya dataset on HDX')
    return url


def fetch_water_points():
    """Return a DataFrame of Kenya water points with at least clean_adm1 (county) and status_clean."""
    import pandas as pd
    url = fetch_water_points_csv_url()
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    # Row after the header is an HXL tag row (e.g. "#geo+lat"), not data.
    df = pd.read_csv(io.StringIO(response.text), skiprows=[1], low_memory=False)
    return df[['clean_adm1', 'status_clean']].dropna(subset=['clean_adm1'])


def aggregate_by_county(df, counties=None):
    """Return {county: {pct_functional, functional_points, total_points}}."""
    if counties:
        df = df[df['clean_adm1'].isin(counties)]

    results = {}
    for county, group in df.groupby('clean_adm1'):
        total = len(group)
        functional = int(group['status_clean'].isin(FUNCTIONAL_STATUSES).sum())
        results[county] = {
            'pct_functional': round(100 * functional / total, 1),
            'functional_points': functional,
            'total_points': total,
        }
    return results


def main():
    df = fetch_water_points()
    stats = aggregate_by_county(df)
    print(f"Fetched {len(df)} water points across {len(stats)} counties.")
    for county, s in sorted(stats.items()):
        print(f"  {county}: {s['pct_functional']}% functional ({s['functional_points']}/{s['total_points']})")


if __name__ == '__main__':
    main()
