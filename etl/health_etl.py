import logging
logging.basicConfig(
    filename='health_etl.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
# --- Additional Health Data Sources ---
def fetch_health_data_who():
    """
    Fetch health indicators for Kenya from WHO (World Health Organization).
    Example endpoint: https://ghoapi.azureedge.net/api/ (WHO GHO API)
    """
    # WHO GHO API: https://ghoapi.azureedge.net/api/ (OData)
    # Example: https://ghoapi.azureedge.net/api/Indicator?$filter=SpatialDim eq 'KEN'
    import pandas as pd
    base_url = 'https://ghoapi.azureedge.net/api/'
    kenya_filter = "?$filter=SpatialDim eq 'KEN'"
    indicator_url = base_url + 'Indicator' + kenya_filter
    try:
        response = requests.get(indicator_url, verify=False)
        if response.status_code == 200:
            data = response.json()
            # Extract indicator codes for Kenya
            indicators = [item['IndicatorCode'] for item in data.get('value', []) if 'IndicatorCode' in item]
            records = []
            for code in indicators:
                url = f"{base_url}{code}{kenya_filter}"
                try:
                    r = requests.get(url, verify=False)
                    if r.status_code == 200:
                        items = r.json().get('value', [])
                        for item in items:
                            record = {
                                'indicator': item.get('IndicatorCode'),
                                'date': item.get('TimeDim'),
                                'value': item.get('Value'),
                                'sex': item.get('Dim1'),
                                'age': item.get('Dim2'),
                                'county': None  # WHO is national-level
                            }
                            records.append(record)
                    else:
                        logging.warning(f"WHO indicator fetch error: HTTP {r.status_code} for {code}")
                except Exception as ex:
                    logging.error(f"WHO indicator fetch error for {code}: {ex}")
            logging.info(f"Fetched {len(records)} WHO Kenya health records.")
            return records
        else:
            logging.error(f"WHO fetch error: HTTP {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"WHO fetch error: {e}")
        return []

def fetch_health_data_worldbank():
    """
    Fetch health indicators for Kenya from World Bank Open Data.
    Example endpoint: https://databankfiles.worldbank.org/public/ddpext_download/ (CSV/Excel)
    """
    # World Bank API: https://datahelpdesk.worldbank.org/knowledgebase/articles/889386-developer-information-overview
    # Example: https://api.worldbank.org/v2/country/KE/indicator?format=json
    import pandas as pd
    indicators_url = 'http://api.worldbank.org/v2/country/KE/indicator?format=json&per_page=1000'
    try:
        response = requests.get(indicators_url, verify=False)
        if response.status_code == 200:
            data = response.json()
            indicator_ids = [item['id'] for item in data[1]] if len(data) > 1 else []
            records = []
            for ind in indicator_ids:
                url = f"http://api.worldbank.org/v2/country/KE/indicator/{ind}?format=json&per_page=100"
                try:
                    r = requests.get(url, verify=False)
                    if r.status_code == 200:
                        d = r.json()
                        if len(d) > 1:
                            for entry in d[1]:
                                record = {
                                    'indicator': entry.get('indicator', {}).get('id'),
                                    'date': entry.get('date'),
                                    'value': entry.get('value'),
                                    'county': None  # World Bank is national-level
                                }
                                records.append(record)
                    else:
                        logging.warning(f"World Bank indicator fetch error: HTTP {r.status_code} for {ind}")
                except Exception as ex:
                    logging.error(f"World Bank indicator fetch error for {ind}: {ex}")
            logging.info(f"Fetched {len(records)} World Bank Kenya health records.")
            return records
        else:
            logging.error(f"World Bank fetch error: HTTP {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"World Bank fetch error: {e}")
        return []

def fetch_health_data_kenya_opendata():
    """
    Fetch health datasets from Kenya Open Data Portal.
    Example: https://opendata.go.ke/browse?category=Health
    """
    # Kenya Open Data: https://opendata.go.ke/browse?category=Health
    # Example: Health Facilities CSV
    import pandas as pd
    url = 'https://opendata.go.ke/api/views/ke49-5d2g/rows.csv?accessType=DOWNLOAD'
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            from io import StringIO
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            # Normalize column names
            df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
            # Try to keep relevant columns (date, county, facility, service, indicator, value)
            keep_cols = [c for c in df.columns if any(k in c for k in ['date', 'county', 'facility', 'service', 'indicator', 'value'])]
            if keep_cols:
                df = df[keep_cols]
            # Fill missing date/county with None
            if 'date' not in df.columns:
                df['date'] = None
            if 'county' not in df.columns:
                df['county'] = None
            records = df.where(pd.notnull(df), None).to_dict('records')
            logging.info(f"Fetched {len(records)} Kenya Open Data health records.")
            return records
        else:
            logging.error(f"Kenya Open Data fetch error: HTTP {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Kenya Open Data fetch error: {e}")
        return []

# ETL script for Health sector (DHIS2)
# Replace URL and parsing logic with actual endpoint details
import requests
import pandas as pd
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_health_data():
    url = 'https://hiskenya.org/api/health-indicators'  # Placeholder
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Health Data fetch error: {e}")
        return None
    
def fetch_health_data_dhis2():
    # Example: Placeholder for DHIS2 API (requires registration)
    url = 'https://hiskenya.org/api/health-indicators'  # Update as needed
    headers = {'Authorization': 'Bearer YOUR_TOKEN'}  # Replace with actual token
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        print(f"DHIS2 fetch error: {e}")
        return []

def fetch_health_data_opendata():
    # Download and parse CSV from OWID (Our World in Data) for Kenya
    url = 'https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv'
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            from io import StringIO
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            # Keep only Kenya data
            df = df[df['location'] == 'Kenya']
            # Dynamically keep all columns except location and iso_code
            drop_cols = ['location', 'iso_code']
            columns = [col for col in df.columns if col not in drop_cols]
            df = df[columns]
            # Normalize column names
            df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
            # Drop rows where all indicators except date are NaN
            non_date_cols = [c for c in df.columns if c != 'date']
            df = df.dropna(how='all', subset=non_date_cols)
            logging.info(f"Fetched {len(df)} OWID Kenya health records with {len(df.columns)} indicators.")
            return df.to_dict('records')
        else:
            logging.error(f"Open Data fetch error: HTTP {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Open Data fetch error: {e}")
        return []

def fetch_health_data_knbs():
    # Example: Scrape KNBS health statistics page (placeholder)
    url = 'https://www.knbs.or.ke/health-statistics/'
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # TODO: Parse relevant data from soup
            return []
        else:
            return []
    except Exception as e:
        print(f"KNBS fetch error: {e}")
        return []

def fetch_health_data_ministry():
    # Example: Scrape Ministry of Health page (placeholder)
    url = 'https://www.health.go.ke/indicators/'
    try:
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # TODO: Parse relevant data from soup
            return []
        else:
            return []
    except Exception as e:
        print(f"Ministry fetch error: {e}")
        return []

def fetch_health_data_county():
    # Example: Scrape county portals (placeholder)
    county_urls = [
        'https://nairobicity.go.ke/health',
        # Add more county URLs
    ]
    all_data = []
    for url in county_urls:
        try:
            response = requests.get(url, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # TODO: Parse relevant data from soup
                pass
        except Exception as e:
            print(f"County fetch error ({url}): {e}")
    return all_data

def aggregate_health_data():
    # Fetch data from all sources
    logging.info('Starting health ETL aggregation')
    opendata = fetch_health_data_opendata()  # OWID
    who = fetch_health_data_who()
    worldbank = fetch_health_data_worldbank()
    kenya_opendata = fetch_health_data_kenya_opendata()

    import pandas as pd
    dfs = []
    source_map = []
    # Helper to add source attribution
    def add_source(records, source):
        for r in records:
            r['source'] = source
        return records

    if opendata:
        dfs.append(pd.DataFrame(add_source(opendata, 'OWID')))
    if isinstance(who, list) and who:
        dfs.append(pd.DataFrame(add_source(who, 'WHO')))
    if isinstance(worldbank, list) and worldbank:
        dfs.append(pd.DataFrame(add_source(worldbank, 'WorldBank')))
    if isinstance(kenya_opendata, list) and kenya_opendata:
        dfs.append(pd.DataFrame(add_source(kenya_opendata, 'KenyaOpenData')))

    # Normalize column names (lowercase, underscores)
    for i, df in enumerate(dfs):
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        dfs[i] = df

    # Indicator mapping: unify indicator/value columns
    normalized = []
    for df in dfs:
        if 'indicator' in df.columns and 'value' in df.columns:
            # Long format: indicator, value, date, county, source
            normalized.append(df)
        else:
            # Wide format: melt to long
            id_vars = [c for c in ['date', 'county', 'source'] if c in df.columns]
            value_vars = [c for c in df.columns if c not in id_vars]
            melted = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='indicator', value_name='value')
            normalized.append(melted)

    # Concatenate all normalized data
    if normalized:
        merged = pd.concat(normalized, ignore_index=True)
        # Ensure all required columns exist
        for col in ['date', 'county', 'indicator', 'source']:
            if col not in merged.columns:
                merged[col] = None
        # Deduplicate
        merged = merged.drop_duplicates(subset=['date', 'county', 'indicator', 'source'])
        # Sort
        sort_keys = [k for k in ['date', 'county', 'indicator', 'source'] if k in merged.columns]
        if sort_keys:
            merged = merged.sort_values(sort_keys)
        merged = merged.where(pd.notnull(merged), None)

        # Data quality checks: log missing/invalid values for key indicators
        key_indicators = ['total_cases', 'total_deaths', 'total_vaccinations']
        for ind in key_indicators:
            missing = merged[(merged['indicator'] == ind) & (merged['value'].isnull())].shape[0]
            if missing > 0:
                logging.warning(f'Missing values for {ind}: {missing}')
            negatives = merged[(merged['indicator'] == ind) & (pd.to_numeric(merged['value'], errors="coerce") < 0)].shape[0]
            if negatives > 0:
                logging.warning(f'Negative values for {ind}: {negatives}')

        logging.info(f'ETL aggregation complete. Records: {len(merged)}')
        return merged.to_dict('records')
    else:
        logging.warning('No dataframes to merge in ETL')
        return []

def main():
    health_data = aggregate_health_data()
    print(f"Fetched {len(health_data)} health records from all sources.")
    if health_data:
        print("Sample records:")
        for record in health_data[:3]:
            print(record)
        # Save to file for prototype
        import json
        with open('health_data_prototype.json', 'w', encoding='utf-8') as f:
            json.dump(health_data, f, ensure_ascii=False, indent=2)
        print("Saved cleaned health data to health_data_prototype.json")
    else:
        print("No health records fetched. Check error messages above.")

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    data = fetch_health_data()
    print(data)
