## Project has gone to steath mode

Please find public web version here: https://rancho-market-data.vercel.app/



# GGTrends

Market research tool for Latin/Hispanic grocery stores. Pulls Google Trends search interest, US Census Hispanic population data, and Google Places competitor listings across Utah, Colorado, and California.

## Installation

**Requirements:** Python 3.8+

```bash
pip install -r requirements.txt
```

## Configuration

Set your Google Places API key in `googlescraper.py`:

```python
api_key = "YOUR_GOOGLE_PLACES_API_KEY"
```

## Usage

```bash
python googlescraper.py
```

## Output

Results are saved to the `output/` directory:

| File | Description |
|------|-------------|
| `output/trends.csv` | Google Trends search interest by city and keyword |
| `output/population.csv` | Hispanic and total population per city (Census 2020) |
| `output/supermarkets.csv` | Latin supermarket locations with lat/lng |

Logs are saved to `logs/scraper_<timestamp>.log`.
