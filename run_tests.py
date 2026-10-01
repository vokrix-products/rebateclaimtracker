import unittest

from processor import process_file


class ProcessorTests(unittest.TestCase):
    def test_csv_purchase_records(self):
        data = b"vendor_name,invoice_number,quantity,unit_cost\nAcme,INV-1,5,10.00"
        records = process_file(data)
        self.assertIsInstance(records, list)
        self.assertTrue(records)
        self.assertEqual(records[0]["title"], "Acme")
        self.assertEqual(records[0]["status"], "missing_agreement:critical")
        self.assertIsInstance(records[0]["details"], dict)
        self.assertIsNone(records[0]["due_date"])

    def test_text_agreement(self):
        data = b"vendor_name: Acme\nprogram_name: Widget Rebate\nclaim_deadline: 2099-12-31\n"
        records = process_file(data)
        self.assertTrue(records)
        record = records[0]
        self.assertEqual(record["title"], "Acme")
        self.assertIn("program_name", record["details"])
        self.assertIsNotNone(record["due_date"])
        self.assertEqual(record["due_date"], "2099-12-31")

    def test_excel_fallback_plain_csv(self):
        data = b"vendor_name,product_description,quantity\nGlobex,Gadget,2"
        records = process_file(data)
        self.assertTrue(records)
        self.assertEqual(records[0]["title"], "Globex")
        self.assertIsInstance(records[0]["details"], dict)


if __name__ == "__main__":
    unittest.main()
