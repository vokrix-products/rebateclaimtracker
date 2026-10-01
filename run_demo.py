from processor import process_file


def main():
    test_bytes = (
        b"vendor_name,invoice_number,invoice_date,quantity,unit_cost,extended_cost,payment_date\n"
        b"Acme,INV-1001,2025-01-15,10,12.50,125.00,2025-02-15\n"
    )
    results = process_file(test_bytes)

    assert isinstance(results, list)
    assert len(results) == 1

    record = results[0]
    assert set(("title", "status", "details", "due_date")).issubset(record.keys())
    assert record["title"] == "Acme"
    assert record["status"] == "missing_agreement:critical"
    assert isinstance(record["details"], dict)

    print("demo ok:", record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
