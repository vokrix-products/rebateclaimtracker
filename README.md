# RebateClaimTracker

RebateClaimTracker is an automated rebate claim tracking product. It ingests purchase-history files and vendor rebate agreements, extracts normalized rebate tracking records, and surfaces earned, claimed, and received rebate amounts with deadlines and tier gaps by vendor through a web dashboard.

## Architecture

This repo contains three cooperating pieces:

- `processor.py` (repo root + `backend/`): pure extraction logic. `process_file(file_bytes: bytes) -> list[dict]` turns an arbitrary uploaded document (PDF, Excel, CSV, plain text) into normalized rebate records. `extract_text(file_bytes)` tries PDF extraction first and falls back to UTF-8 decode.
- `poller.py` (repo root + `backend/`): the always-on worker deployed to Railway. It polls the `jobs` table for `status=eq.pending` AND `job_type=eq.process_upload` AND `product_id=eq.$PRODUCT_ID`, downloads the input file from the `uploads` bucket, runs `processor.process_file`, inserts each record into the `records` table, uploads result JSON to the `results` bucket, marks the job `completed`/`failed`, and writes a notification row. It defines a named `poll()` function containing the `while True` loop plus a `time.sleep(60)`; `__main__` calls `poll()`.
- `dashboard/`: the Vite + React + TanStack Router admin dashboard (Vokrix dashboard template). It provides the records table, upload flow, jobs view, settings, notifications, and audit surfaces. The product copy is driven by `VITE_*` env vars set in Vercel (archetype `extraction`, label `Rebate Claims`).

## Data flow

1. A customer uploads a purchase-history CSV or rebate agreement PDF via the dashboard.
2. The dashboard writes a row to `jobs` (`status=pending`, `job_type=process_upload`) and stores the file in the `uploads` storage bucket.
3. `poller.py` (Railway) picks up the job, downloads the file, extracts records with `processor.py`, inserts them into `records`, uploads the result to `results`, and updates the job status.
4. A `notifications` row is created so the dashboard bell reflects success or failure.

## Extractable record statuses

`missing_agreement`, `missing_purchase_data`, `missing_required_claim_document`, `unparsed_agreement_line`, `expired_claim_window`, `valid_earned_unclaimed`, `claim_window_open`, `claim_window_closing_soon`, `submitted`, `approved`, `partially_paid`, `paid`, `denied`, `disputed`, `flagged_for_review`, `threshold_gap`, `threshold_reached`, `unreconciled_gap`, `reconciled`, `no_activity`.

## Required environment variables

Poller / Railway:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `PRODUCT_ID`
- `ANTHROPIC_API_KEY`

Dashboard / Vercel:

- `VITE_PRODUCT_ARCHETYPE`, `VITE_RECORDS_LABEL`, `VITE_RECORDS_SUBTITLE`, `VITE_FILTER_PLACEHOLDER`, `VITE_UPLOAD_DESCRIPTION`, `VITE_UPLOAD_EMPTY_STATE`
- Supabase URL / anon key for the client.

## Local development

Backend:

    pip install -r requirements.txt
    python3 run_demo.py
    python3 run_tests.py

Dashboard:

    cd dashboard
    npm install
    npm run build

## Deployment

- Dashboard: Vercel (project `rebateclaimtracker`), builds from `dashboard/` with `vercel.json` SPA rewrites.
- Poller: Railway, built from the repo-root `Dockerfile` (`CMD ["python3", "poller.py"]`).

Dashboard: https://rebateclaimtracker.vokrix.co
Vercel: rebateclaimtracker
Railway: rebateclaimtracker
Cloudflare: rebateclaimtracker.vokrix.co
