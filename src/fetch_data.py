import os
import json
import requests
import boto3
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("COINGECKO_API_KEY")
RAW_BUCKET = "crypto-pipeline-raw-dtkauber"

def fetch_market_data():
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
    return resp.json()

def write_to_s3(data):
    # Partition by date — this matters later for Athena queries
    now = datetime.now(timezone.utc)
    key = f"date={now:%Y-%m-%d}/markets_{now:%Y%m%dT%H%M%SZ}.json"

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(data),
        ContentType="application/json",
    )
    print(f"Wrote {len(data)} records to s3://{RAW_BUCKET}/{key}")

if __name__ == "__main__":
    data = fetch_market_data()
    write_to_s3(data)