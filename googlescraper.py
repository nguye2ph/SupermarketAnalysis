import requests
import json
import time
import random
import pandas as pd
from pytrends.request import TrendReq

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
    print(f"Fetching Google Trends data for {len(keywords)} keywords across Utah, Colorado, California...")

    state_abbr = {'US-UT': 'UT', 'US-CO': 'CO', 'US-CA': 'CA'}

    # Split keywords into batches of 5 (pytrends limit)
    batch_size = 5
    batches = [keywords[i:i+batch_size] for i in range(0, len(keywords), batch_size)]

    rows = [["city", "state"] + keywords]

    for geo in geo_list:
        print(f"Processing {geo}...")
        state = state_abbr[geo]
        # Collect data for each batch
        geo_data = {}
        for batch in batches:
            pytrends = TrendReq()
            pytrends.build_payload(batch, timeframe="today 12-m", geo=geo)
            data = pytrends.interest_by_region(resolution='CITY', inc_low_vol=True, inc_geo_code=False)

            # data is a df with index as city, columns as batch keywords
            for city in data.index:
                if city not in geo_data:
                    geo_data[city] = {}
                for kw in batch:
                    geo_data[city][kw] = data.loc[city, kw]

            # Add delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))

        # Now, for each city in geo_data, create row
        for city, kw_dict in geo_data.items():
            values = [kw_dict.get(kw, 0) for kw in keywords]
            rows.append([city, state] + values)

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
    except:
        pass
    return None, None

def get_supermarkets(city, state, keyword="latin market"):
    api_key = "AIzaSyD5XLQ9w_5lD9Zt_kIAC_umg4YxuGcPkj8"  # Replace with your actual Google Places API key
    if api_key == "YOUR_GOOGLE_PLACES_API_KEY":
        print("Please set your Google Places API key in the script.")
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
    except:
        return []

# -----------------------------------------
# Run script
# -----------------------------------------

if __name__ == "__main__":
    data = get_trends(keywords)

    print("\n===== INTEREST BY CITIES IN UTAH, COLORADO, CALIFORNIA (EXCEL READY) =====")
    print(",".join(data[0]))
    for row in data[1:]:
        print(",".join(str(x) for x in row))

    print(f"... ({len(data)-1} total cities)")

    # Additional data extraction
    print("\n===== FETCHING ADDITIONAL DATA =====")

    populations = {}
    supermarkets = {}

    for row in data[1:]:
        city, state = row[0], row[1]
        key = (city, state)
        if key not in populations:
            hispanic, total = get_hispanic_population(city, state)
            populations[key] = (hispanic, total)
        if key not in supermarkets:
            sups = get_supermarkets(city, state, "latin market")
            supermarkets[key] = sups

    print("\n===== HISPANIC POPULATION DATA =====")
    print("city,state,hispanic_population,total_population")
    for (city, state), (hispanic, total) in populations.items():
        print(f"{city},{state},{hispanic if hispanic else 'N/A'},{total if total else 'N/A'}")

    print("\n===== SUPERMARKET DATA =====")
    print("city,state,supermarket_name,latitude,longitude")
    for (city, state), sups in supermarkets.items():
        for sup in sups:
            print(f"{city},{state},{sup['name']},{sup['lat']},{sup['lng']}")

    print("\nNote: Supermarket square footage data is not readily available via public APIs.")
