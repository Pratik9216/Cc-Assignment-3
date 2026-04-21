import boto3
import csv
import io
from datetime import datetime, timedelta
import urllib.parse

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    AWS Lambda function triggered by an S3 PutObject event on the raw/ prefix.
    Reads the uploaded CSV, filters out old pending/cancelled orders,
    and writes the cleaned output to the processed/ prefix.
    """
    print("Lambda triggered by S3 event.")

    # ── Extract bucket and key from the S3 event ────────────────────────────
    bucket_name   = event['Records'][0]['s3']['bucket']['name']
    raw_key       = urllib.parse.unquote_plus(
                        event['Records'][0]['s3']['object']['key'],
                        encoding='utf-8'
                    )
    file_name = raw_key.split('/')[-1]
    print(f"Incoming file: s3://{bucket_name}/{raw_key}")

    # ── Download raw CSV from S3 ─────────────────────────────────────────────
    try:
        response = s3.get_object(Bucket=bucket_name, Key=raw_key)
        raw_csv  = response['Body'].read().decode('utf-8').splitlines()
        print(f"Successfully read {len(raw_csv) - 1} data rows from {file_name}.")
    except Exception as e:
        print(f"ERROR reading file from S3: {e}")
        raise

    # ── Filter records ────────────────────────────────────────────────────────
    # Keep a row if:
    #   (a) status is NOT pending/cancelled  →  shipped or confirmed always kept
    #   (b) OR the order date is recent (within the last 30 days)  →  keep even
    #       pending/cancelled orders that arrived recently
    reader         = csv.DictReader(raw_csv)
    filtered_rows  = []
    original_count = 0
    removed_count  = 0
    cutoff_date    = datetime.utcnow() - timedelta(days=30)

    print("Processing and filtering records...")
    for row in reader:
        original_count += 1
        order_status = row['Status'].strip().lower()
        order_date   = datetime.strptime(row['OrderDate'].strip(), "%Y-%m-%d")

        if order_status not in ('pending', 'cancelled') or order_date > cutoff_date:
            filtered_rows.append(row)
        else:
            removed_count += 1

    print(f"  Total records  : {original_count}")
    print(f"  Filtered OUT   : {removed_count}")
    print(f"  Records KEPT   : {len(filtered_rows)}")

    # ── Write filtered CSV to memory ─────────────────────────────────────────
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(filtered_rows)

    # ── Upload to processed/ ─────────────────────────────────────────────────
    processed_key = f"processed/filtered_{file_name}"
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=processed_key,
            Body=output.getvalue(),
            ContentType='text/csv'
        )
        print(f"Filtered file written to s3://{bucket_name}/{processed_key}")
    except Exception as e:
        print(f"ERROR writing filtered file to S3: {e}")
        raise

    return {
        'statusCode': 200,
        'body': (
            f"Processed {original_count} rows. "
            f"Kept {len(filtered_rows)}, removed {removed_count}. "
            f"Output: s3://{bucket_name}/{processed_key}"
        )
    }
