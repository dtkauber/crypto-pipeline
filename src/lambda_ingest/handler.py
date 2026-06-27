import os
import json
import requests
import boto3
from datetime import datetime, timezone

RAW_BUCKET = os.environ["RAW_BUCKET"]
API_KEY = os.environ["COINGECKO_API_KEY"]

def fetch_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
    }
    headers = {"x-cg-demo-api-key": API_KEY}
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def lambda_handler(event, context):
    data = fetch_market_data()
    now = datetime.now(timezone.utc)
    key = f"date={now:%Y-%m-%d}/markets_{now:%Y%m%dT%H%M%SZ}.json"

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(data),
        ContentType="application/json",
    )
    msg = f"Wrote {len(data)} records to s3://{RAW_BUCKET}/{key}"
    print(msg)
    return {"statusCode": 200, "body": msg}