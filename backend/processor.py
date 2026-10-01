import csv
import io
import re
from datetime import date, datetime

import openpyxl
import pdfplumber

STATUS_MISSING_AGREEMENT = "missing_agreement:critical"
STATUS_MISSING_PURCHASE_DATA = "missing_purchase_data:warning"
STATUS_UNPARSED_AGREEMENT_LINE = "unparsed_agreement_line:warning"
STATUS_EXPIRED_CLAIM_WINDOW = "expired_claim_window:critical"
STATUS_CLAIM_WINDOW_OPEN = "claim_window_open:good"
STATUS_CLAIM_WINDOW_CLOSING_SOON = "claim_window_closing_soon:warning"
STATUS_FLAGGED_FOR_REVIEW = "flagged_for_review:warning"


def _normalize_key(value):
    if value is None:
        return ""
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _first_non_empty(row, *keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, "", "nan"):
            return value
    return None


def _to_iso_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in (
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%Y/%m/%d",
            "%d-%b-%Y",
            "%d-%b-%y",
        ):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).isoformat()
        except ValueError:
            return None
    return None


def _looks_like_csv(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    first = lines[0].strip().lower()
    if not ("," in first or "\t" in first):
        return False
    purchase_markers = (
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "sku",
        "quantity",
        "unit_cost",
        "unit_list_price",
        "supplier",
        "product_description",
        "manufacturer_part_number",
    )
    return any(marker in first for marker in purchase_markers)


def _parse_purchase_dict_rows(rows):
    records = []
    for row in rows:
        title = _first_non_empty(row, "vendor_name", "supplier", "seller") or "Unknown Vendor"
        title = str(title)
        due_value = _first_non_empty(row, "payment_date", "invoice_date", "ship_date", "received_date")
        due_date = _to_iso_date(due_value)
        details = dict(row)
        records.append(
            {
                "title": title,
                "status": STATUS_MISSING_AGREEMENT,
                "details": details,
                "due_date": due_date,
            }
        )
    return records


def _parse_csv_text(text):
    lines = text.splitlines()
    if not lines:
        return []
    delimiter = "," if "," in lines[0] else "\t"
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    normalized_rows = []
    for row in reader:
        normalized = {}
        for key, value in row.items():
            normalized_key = _normalize_key(key)
            if normalized_key:
                normalized[normalized_key] = value
        normalized_rows.append(normalized)
    return _parse_purchase_dict_rows(normalized_rows)


def _parse_excel(file_bytes):
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception:
        return None

    try:
        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            headers = [_normalize_key(value) for value in next(rows_iter)]
        except StopIteration:
            return []

        rows = []
        for row in rows_iter:
            record = {}
            for idx, header in enumerate(headers):
                if header and idx < len(row):
                    record[header] = row[idx]
            rows.append(record)
    finally:
        workbook.close()

    if not rows:
        return []
    return _parse_purchase_dict_rows(rows)


def _try_pdf(file_bytes):
    try:
        import pdfplumber
    except ImportError:
        return None

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if not text.strip():
            return []
        return _parse_agreement_text(text)
    except Exception:
        return None


def _status_from_agreement_fields(fields):
    claim_deadline = fields.get("claim_deadline")
    if claim_deadline:
        deadline_date = _to_iso_date(claim_deadline)
        if deadline_date:
            deadline_obj = date.fromisoformat(deadline_date)
            today = date.today()
            if deadline_obj < today:
                return STATUS_EXPIRED_CLAIM_WINDOW
            if (deadline_obj - today).days <= 30:
                return STATUS_CLAIM_WINDOW_CLOSING_SOON
            return STATUS_CLAIM_WINDOW_OPEN

    confidence = str(fields.get("extraction_confidence", "")).lower()
    if confidence in {"low", "unconfident", "unparsed"}:
        return STATUS_FLAGGED_FOR_REVIEW

    return STATUS_MISSING_PURCHASE_DATA


def _parse_agreement_text(text):
    fields = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_ ]*?)\s*[:=]\s*(.*)$", line)
        if match:
            key = _normalize_key(match.group(1))
            value = match.group(2).strip()
            if key:
                fields[key] = value

    if not fields:
        fields = {"notes": text.strip()}
        title = "Unknown Vendor"
        status = STATUS_UNPARSED_AGREEMENT_LINE
    else:
        title = _first_non_empty(fields, "vendor_name", "program_name") or "Unknown Vendor"
        title = str(title)
        status = _status_from_agreement_fields(fields)

    due_date = _to_iso_date(
        _first_non_empty(fields, "claim_deadline", "effective_end_date", "claim_window_end")
    )

    return [
        {
            "title": title,
            "status": status,
            "details": fields,
            "due_date": due_date,
        }
    ]


def _parse_text_fallback(text):
    if not text.strip():
        return []
    if _looks_like_csv(text):
        return _parse_csv_text(text)
    return _parse_agreement_text(text)


def process_file(file_bytes: bytes) -> list[dict]:
    if not file_bytes:
        return []

    pdf_records = _try_pdf(file_bytes)
    if pdf_records is not None:
        return pdf_records

    excel_records = _parse_excel(file_bytes)
    if excel_records is not None:
        return excel_records

    text = file_bytes.decode("utf-8", errors="ignore")
    return _parse_text_fallback(text)


def extract_text(file_bytes):
    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = ""
            for p in pdf.pages:
                text = text + (p.extract_text() or "") + "\n"
            if text.strip():
                return text
    except Exception:
        pass
    return file_bytes.decode("utf-8", errors="ignore")
