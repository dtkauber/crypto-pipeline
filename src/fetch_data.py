import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("COINGECKO_API_KEY")

url = "https://api.coingecko.com/api/v3/coins/markets"
params = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 50,
    "page": 1,
}
headers = {"x-cg-demo-api-key": API_KEY}

resp = requests.get(url, params=params, headers=headers)
resp.raise_for_status()
data = resp.json()

for coin in data[:5]:
    print(f"{coin['name']:15} ${coin['current_price']:>12,.2f}  "
          f"24h: {coin['price_change_percentage_24h']:+.2f}%")