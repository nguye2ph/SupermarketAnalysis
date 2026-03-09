import requests
import json
import time
import random

EXPLORE_URL = "https://trends.google.com/trends/api/explore"
WIDGET_URL = "https://trends.google.com/trends/api/widgetdata/multiline"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

def get_headers():
    """Get randomized headers to avoid detection."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://trends.google.com/trends/explore",
        "Accept": "application/json",
    }

def make_request(url, params, max_retries=8, base_wait=3):
    """Make HTTP request with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=get_headers(), timeout=15)
            
            if response.status_code == 429:
                wait_time = base_wait * (2 ** attempt) + random.uniform(0, 2)  # Exponential backoff with jitter
                wait_time = min(wait_time, 120)  # Cap at 2 minutes
                print(f"Rate limited (429). Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            
            if response.status_code == 403:
                wait_time = base_wait * (2 ** attempt) + random.uniform(0, 2)
                wait_time = min(wait_time, 120)
                print(f"Forbidden (403). Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch data: HTTP {response.status_code}")
            
            return response
            
        except requests.exceptions.Timeout:
            wait_time = base_wait * (2 ** attempt)
            print(f"Timeout. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait_time)
            continue
        except requests.exceptions.ConnectionError:
            wait_time = base_wait * (2 ** attempt)
            print(f"Connection error. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait_time)
            continue
    
    raise Exception(f"Failed after {max_retries} retries")

def get_widget_tokens(keyword, geo="US", time_range="today 3-m"):
    params = {
        "hl": "en-US",
        "tz": "-420",
        "req": json.dumps({
            "comparisonItem": [{"keyword": keyword, "geo": geo, "time": time_range}],
            "category": 0,
            "property": ""
        })
    }

    response = make_request(EXPLORE_URL, params)
    text = response.text.replace(")]}',", "")
    
    if not text or text.strip() == "":
        print(f"DEBUG: Empty response received. Full response: {repr(response.text[:500])}")
        raise Exception("Empty response from Google Trends API")

    data = json.loads(text)

    for widget in data["widgets"]:
        if widget["id"] == "TIMESERIES":
            return widget["token"], widget["request"]

    raise Exception("Timeseries widget not found")


def get_daily_data(token, request_payload):
    # Add delay before request to be respectful
    time.sleep(2)
    
    params = {
        "hl": "en-US",
        "tz": "-420",
        "token": token,
        "req": json.dumps(request_payload)
    }

    response = make_request(WIDGET_URL, params)
    text = response.text.replace(")]}',", "")

    data = json.loads(text)

    rows = [["date", "value"]]

    for entry in data["default"]["timelineData"]:
        date = entry["formattedTime"]
        value = entry["value"][0]
        rows.append([date, value])
    
    return rows


def get_trends_last_3_months(keyword, geo="US"):
    print(f"Fetching Google Trends daily data for '{keyword}' (last 3 months)...")

    token, req_payload = get_widget_tokens(keyword, geo)
    rows = get_daily_data(token, req_payload)

    return rows


if __name__ == "__main__":
    keyword = "rancho market"

    data = get_trends_last_3_months(keyword)

    print("\n===== DAILY INTEREST (EXCEL READY) =====")
    for row in data[:15]:
        print(row)

    print(f"... ({len(data)-1} total days)")
