# RebateClaimTracker Backend

RebateClaimTracker is a backend extraction service for rebate claim tracking. It ingests purchase records and vendor rebate agreements and normalizes them into a uniform list of tracking records so a buyer can monitor which rebates still need an agreement, which claim windows are open, closing soon, or expired, and which items need manual review.

This repository contains pure processing scripts only. No HTTP server is included.

## Archetype

This is an **extraction / normalization backend**. There is no UI and no API layer in this repo. The single public entry point is `process_file(file_bytes: bytes) -> list[dict]`, which turns an arbitrary uploaded document into a list of normalized records. A separate poller/service is expected to call this function and persist the resulting records.

## Files

- `processor.py`: extraction logic for PDF, Excel, CSV, and plain text. Defines `process_file(file_bytes: bytes) -> list[dict]`.
- `run_demo.py`: zero-argument demo using hardcoded CSV data. Exits 0.
- `run_tests.py`: unit tests for the processor (CSV purchases, text agreements, Excel/plain-CSV fallback).
- `requirements.txt`: Python dependencies (`openai`, `requests`, `pdfplumber`, `openpyxl`).

## Extraction Pipeline

`process_file` tries each strategy in order and returns the first that succeeds:

1. **PDF** via `pdfplumber` - extracts text, then parses as a rebate agreement (key/value lines).
2. **Excel** via `openpyxl` - reads the first sheet, treats row 1 as headers, normalizes header names.
3. **Text / CSV fallback** - decodes UTF-8 and parses CSV purchase rows when the document looks like a purchase export, otherwise parses it as agreement text.

## Record Contract

Each record returned by `process_file` has these top-level keys:

- `title`: primary entity the buyer tracks, preferred vendor name.
- `status`: exact status string, including severity suffix.
- `details`: dictionary of extracted extra fields.
- `due_date`: ISO-8601 string or `None`.

### Status Strings

| Status | Severity | Meaning |
|---|---|---|
| `missing_agreement:critical` | critical | A purchase record was found but no matching rebate agreement exists. |
| `missing_purchase_data:warning` | warning | An agreement exists but purchase data is absent. |
| `unparsed_agreement_line:warning` | warning | Agreement text could not be parsed into known fields. |
| `expired_claim_window:critical` | critical | The claim deadline has already passed. |
| `claim_window_open:good` | good | The claim deadline is more than 30 days away. |
| `claim_window_closing_soon:warning` | warning | The claim deadline is within 30 days. |
| `flagged_for_review:warning` | warning | Low extraction confidence; needs manual review. |

## What the Poller Expects as Input

The poller hands raw document bytes straight to `process_file`. Accepted inputs:

- **Purchase CSV / Excel exports** with headers such as `vendor_name`, `supplier`, `invoice_number`, `invoice_date`, `sku`, `quantity`, `unit_cost`, `unit_list_price`, `extended_cost`, `payment_date`, `product_description`, `manufacturer_part_number`. Header names are normalized (lowercased, non-alphanumerics collapsed to `_`), so minor casing/spacing differences are tolerated.
- **Rebate agreement text or PDFs** containing `key: value` or `key = value` lines, e.g. `vendor_name: Acme`, `program_name: Widget Rebate`, `claim_deadline: 2099-12-31`.

For purchase rows the poller receives one record per row with status `missing_agreement:critical` until an agreement is linked. For agreements the status is derived from the claim deadline and extraction confidence.

## Running

```bash
pip install -r requirements.txt
python3 run_demo.py   # zero-argument demo, exits 0
python3 run_tests.py  # unit tests
```
