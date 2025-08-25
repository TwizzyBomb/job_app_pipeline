import time
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from a .env file if present


CX = "6069166fa70fd403e"  # the 'cx' from the Programmable Search Engine
BASE = "https://www.googleapis.com/customsearch/v1"
query = '"Software Engineer" AND CA OR remote -India -Mexico -Brazil -Argentina -Colombia -Peru -Chile -Ecuador -Venezuela -Bolivia -Paraguay -Uruguay -Spain -Vietnam -Philippines -Indonesia -Thailand -Malaysia -Singapore -China -Russia -Ukraine -Turkey -Egypt -Nigeria -Kenya -South Africa'
per_page = 10
dateRestrict = "d3"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def run_search(max_results=50):
    raw_responses = []
    start = 1
    while start <= 100 and len(raw_responses) < max_results:
        params = {
            "key": GOOGLE_API_KEY,  # make sure this is set in your .env
            "cx": CX,
            "q": query,
            "num": per_page,
            "start": start,
            "dateRestrict": dateRestrict
        }
        r = requests.get(BASE, params=params, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"Search API error: {r.status_code} {r.text}")
        j = r.json()
        raw_responses.append(j)
        start += per_page
        time.sleep(1.0)
        if not j.get("items"):
            break
    return raw_responses

if __name__ == "__main__":
    raw_data = run_search(max_results=50)
    with open("job_search_results.json", "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2)
    print("Saved raw JSON to job_search_results.json")