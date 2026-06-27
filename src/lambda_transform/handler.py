import os
import json
import boto3
from datetime import datetime, timezone

RAW_BUCKET = os.environ["RAW_BUCKET"]
PROCESSED_BUCKET = os.environ["PROCESSED_BUCKET"]

def lambda_handler(event, context):
    s3 = boto3.client("s3")

    # Find the most recent raw file
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=RAW_BUCKET)

    all_keys = []
    for page in pages:
        for obj in page.get("Contents", []):
            all_keys.append(obj["Key"])

    if not all_keys:
        return {"statusCode": 400, "body": "No raw files found"}

    latest_key = sorted(all_keys)[-1]
    print(f"Transforming: {latest_key}")

    # Read raw JSON
    response = s3.get_object(Bucket=RAW_BUCKET, Key=latest_key)
    raw_data = json.loads(response["Body"].read())

    # Transform: clean and flatten each coin record
    transformed = []
    for coin in raw_data:
        transformed.append({
            "id": coin.get("id"),
            "symbol": coin.get("symbol", "").upper(),
            "name": coin.get("name"),
            "current_price_usd": coin.get("current_price"),
            "market_cap_usd": coin.get("market_cap"),
            "total_volume_usd": coin.get("total_volume"),
            "price_change_24h_pct": coin.get("price_change_percentage_24h"),
            "circulating_supply": coin.get("circulating_supply"),
            "ingested_at": latest_key.split("/")[-1].replace("markets_", "").replace(".json", ""),
            "processed_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        })

    # Write as newline-delimited JSON (Athena-friendly)
    now = datetime.now(timezone.utc)
    out_key = f"date={now:%Y-%m-%d}/markets_{now:%Y%m%dT%H%M%SZ}.json"
    body = "\n".join(json.dumps(r) for r in transformed)

    s3.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=out_key,
        Body=body,
        ContentType="application/json",
    )

    msg = f"Transformed {len(transformed)} records to s3://{PROCESSED_BUCKET}/{out_key}"
    print(msg)
    return {"statusCode": 200, "body": msg}