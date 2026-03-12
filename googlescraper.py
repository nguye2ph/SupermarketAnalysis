import requests
import csv
import time
import random
import logging
import os
from datetime import datetime
import pandas as pd
from tqdm import tqdm
from pytrends.request import TrendReq

# -----------------------------------------
# Logging setup
# -----------------------------------------

os.makedirs("logs", exist_ok=True)
log_filename = f"logs/scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -----------------------------------------
# Combined Spanish + English keyword lists
# -----------------------------------------

keywords_es = [
    "tienda latina",
    "tienda latina cerca de mí",
    "supermercado hispano",
    "mercado latino",
    "mercado mexicano",
    "carnicería latina",
    "panadería latina",
    "productos latinos",
    "abarrotes latinos",
    "tortillería"
]

keywords_en = [
    "hispanic grocery store",
    "latin market",
    "mexican grocery store",
    "latino supermarket",
    "mexican market",
    "latin food store",
    "hispanic food store",
    "mexican butcher shop",
    "latin bakery",
    "tortilla shop"
]

# Merge both lists
keywords = keywords_es + keywords_en

# -----------------------------------------
# Google Trends function
# -----------------------------------------

def get_trends(keywords, geo_list=["US-UT", "US-CO", "US-CA"]):
    logger.info(f"Fetching Google Trends data for {len(keywords)} keywords across {len(geo_list)} regions...")

    state_abbr = {'US-UT': 'UT', 'US-CO': 'CO', 'US-CA': 'CA'}
    batch_size = 5
    batches = [keywords[i:i+batch_size] for i in range(0, len(keywords), batch_size)]

    rows = []

    for geo in tqdm(geo_list, desc="Regions", unit="region"):
        state = state_abbr[geo]
        logger.info(f"Processing region: {geo} ({state})")
        geo_data = {}

        for batch in tqdm(batches, desc=f"  Batches [{state}]", unit="batch", leave=False):
            try:
                pytrends = TrendReq()
                pytrends.build_payload(batch, timeframe="today 12-m", geo=geo)
                data = pytrends.interest_by_region(resolution='CITY', inc_low_vol=True, inc_geo_code=False)

                for city in data.index:
                    if city not in geo_data:
                        geo_data[city] = {}
                    for kw in batch:
                        geo_data[city][kw] = data.loc[city, kw]

                logger.debug(f"Fetched batch {batch} for {geo}")
            except Exception as e:
                logger.warning(f"Failed to fetch batch {batch} for {geo}: {e}")

            time.sleep(random.uniform(1, 3))

        for city, kw_dict in geo_data.items():
            values = [kw_dict.get(kw, 0) for kw in keywords]
            rows.append([city, state] + values)

        logger.info(f"Collected {len(geo_data)} cities for {state}")

    logger.info(f"Trends complete. Total city rows: {len(rows)}")
    return rows

# -----------------------------------------
# Additional data functions
# -----------------------------------------

def get_hispanic_population(city, state):
    state_fips = {'UT': '49', 'CO': '08', 'CA': '06'}
    fips = state_fips.get(state)
    if not fips:
        return None, None
    url = f"https://api.census.gov/data/2020/acs/acs5?get=NAME,B01003_001E,B03003_003E&for=place:*&in=state:{fips}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        for row in data[1:]:
            name = row[0].split(',')[0].strip().lower()
            if name == city.lower() or name == city.lower() + ' city':
                total = int(row[1])
                hispanic = int(row[2])
                return hispanic, total
    except Exception as e:
        logger.warning(f"Census API error for {city}, {state}: {e}")
    return None, None

def get_supermarkets(city, state, keyword="latin market"):
    api_key = "AIzaSyD5XLQ9w_5lD9Zt_kIAC_umg4YxuGcPkj8"
    if api_key == "YOUR_GOOGLE_PLACES_API_KEY":
        logger.error("Google Places API key not set.")
        return []
    query = f"{keyword} in {city}, {state}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('results', [])
        supermarkets = []
        for result in results:
            name = result.get('name', '')
            lat = result.get('geometry', {}).get('location', {}).get('lat', '')
            lng = result.get('geometry', {}).get('location', {}).get('lng', '')
            supermarkets.append({'name': name, 'lat': lat, 'lng': lng})
        return supermarkets
    except Exception as e:
        logger.warning(f"Places API error for {city}, {state}: {e}")
        return []

# -----------------------------------------
# CSV export functions
# -----------------------------------------

def export_trends_csv(data, keywords, path="output/trends.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["city", "state"] + keywords)
        writer.writerows(data)
    logger.info(f"Trends data saved to {path}")

def export_population_csv(populations, path="output/population.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["city", "state", "hispanic_population", "total_population"])
        for (city, state), (hispanic, total) in populations.items():
            writer.writerow([city, state, hispanic or "N/A", total or "N/A"])
    logger.info(f"Population data saved to {path}")

def export_supermarkets_csv(supermarkets, path="output/supermarkets.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["city", "state", "supermarket_name", "latitude", "longitude"])
        for (city, state), sups in supermarkets.items():
            for sup in sups:
                writer.writerow([city, state, sup['name'], sup['lat'], sup['lng']])
    logger.info(f"Supermarket data saved to {path}")

# -----------------------------------------
# Run script
# -----------------------------------------

if __name__ == "__main__":
    logger.info("=== GGTrends scraper started ===")

    trend_rows = get_trends(keywords)
    export_trends_csv(trend_rows, keywords)

    logger.info("Fetching population and supermarket data...")

    populations = {}
    supermarkets = {}

    for row in tqdm(trend_rows, desc="Cities", unit="city"):
        city, state = row[0], row[1]
        key = (city, state)

        if key not in populations:
            logger.debug(f"Fetching population: {city}, {state}")
            populations[key] = get_hispanic_population(city, state)

        if key not in supermarkets:
            logger.debug(f"Fetching supermarkets: {city}, {state}")
            supermarkets[key] = get_supermarkets(city, state, "latin market")

    export_population_csv(populations)
    export_supermarkets_csv(supermarkets)

    logger.info("=== Scraper finished. Outputs saved to output/ ===")
    logger.info("Note: Supermarket square footage data is not readily available via public APIs.")
