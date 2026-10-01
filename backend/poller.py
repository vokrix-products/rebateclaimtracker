import os
import time
import json
import requests
from datetime import datetime, timezone

import processor

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
PRODUCT_ID = os.environ.get("PRODUCT_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

REST_URL = f"{SUPABASE_URL}/rest/v1"
SB_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}


def download_file(bucket, file_path):
    if file_path.startswith(bucket + "/"):
        file_path = file_path[len(bucket) + 1:]
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file_path}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", "apikey": SUPABASE_SERVICE_KEY})
    resp.raise_for_status()
    return resp.content


def upload_file(bucket, file_path, data, content_type="application/octet-stream"):
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return file_path


def update_job(job_id, payload):
    url = f"{REST_URL}/jobs?id=eq.{job_id}"
    headers = {**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"}
    resp = requests.patch(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp


def insert_notification(customer_id, title, body, ntype):
    try:
        url = "https://njyvnmczoydsaewvfhyq.supabase.co/rest/v1/notifications"
        headers = {**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"}
        payload = {
            "product_id": PRODUCT_ID,
            "customer_id": customer_id,
            "title": title,
            "body": body,
            "type": ntype,
            "read": False,
        }
        requests.post(url, headers=headers, json=payload)
    except Exception as exc:
        print(f"notification insert failed: {exc}")


def insert_record(customer_id, record, source_file_path):
    url = REST_URL + "/records"
    headers = {**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"}
    payload = {
        "product_id": PRODUCT_ID,
        "customer_id": customer_id,
        "title": record["title"],
        "status": record["status"],
        "details": record["details"],
        "source_file_path": source_file_path,
        "due_date": record.get("due_date"),
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp


def process_job(job):
    job_id = job["id"]
    customer_id = job["customer_id"]
    file_path = job["input_file_path"]
    bucket = job.get("input_bucket") or "uploads"

    try:
        file_bytes = download_file(bucket, file_path)
        records = processor.process_file(file_bytes)

        for record in records:
            insert_record(customer_id, record, file_path)

        result_bytes = json.dumps(records, default=str, indent=2).encode("utf-8")
        output_path = f"{job_id}/results.json"
        upload_file("results", output_path, result_bytes, "application/json")

        update_job(job_id, {
            "status": "completed",
            "output_file_path": output_path,
            "result_summary": {"records": len(records)},
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

        insert_notification(customer_id, "Processing complete", "Your upload has been processed successfully.", "success")
        print(f"job {job_id} completed with {len(records)} records")

    except Exception as exc:
        print(f"job {job_id} failed: {exc}")
        try:
            update_job(job_id, {
                "status": "failed",
                "result_summary": {"error": str(exc)},
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as inner:
            print(f"failed to mark job {job_id} failed: {inner}")
        insert_notification(customer_id, "Processing failed", "There was an error processing your upload.", "error")


def fetch_pending_jobs():
    url = (
        f"{REST_URL}/jobs"
        f"?status=eq.pending&job_type=eq.process_upload&product_id=eq.{PRODUCT_ID}"
        f"&select=*&order=created_at.asc&limit=10"
    )
    resp = requests.get(url, headers=SB_HEADERS)
    resp.raise_for_status()
    return resp.json()


def poll():
    while True:
        try:
            jobs = fetch_pending_jobs()
            for job in jobs:
                process_job(job)
        except Exception as exc:
            print(f"poll loop error: {exc}")
        time.sleep(60)


if __name__ == "__main__":
    print("Poller started")
    poll()
