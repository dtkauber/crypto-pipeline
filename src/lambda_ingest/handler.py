import os
import json
import requests
import boto3
from datetime import datetime, timezone

RAW_BUCKET = os.environ["RAW_BUCKET"]
API_KEY = os.environ["COINGECKO_API_KEY"]
TRANSFORM_FUNCTION = os.environ["TRANSFORM_FUNCTION"]

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
    # Fetch and write raw data
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
    print(f"Wrote {len(data)} records to s3://{RAW_BUCKET}/{key}")

    # Trigger transform Lambda
    lambda_client = boto3.client("lambda")
    lambda_client.invoke(
        FunctionName=TRANSFORM_FUNCTION,
        InvocationType="Event",  # async — don't wait for it to finish
    )
    print(f"Triggered {TRANSFORM_FUNCTION}")

    return {"statusCode": 200, "body": f"Ingested and triggered transform"}