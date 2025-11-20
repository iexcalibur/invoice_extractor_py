#!/usr/bin/env python3
"""Verify database contents"""

from database import InvoiceDatabase

db = InvoiceDatabase('invoices.db')
invoices = db.get_all_invoices()

print(f"Total invoices in database: {len(invoices)}")

if invoices:
    inv = invoices[0]
    print(f"\nSample Invoice:")
    print(f"  ID: {inv['id']}")
    print(f"  Invoice #: {inv['invoice_number']}")
    print(f"  Vendor: {inv['vendor_name']}")
    print(f"  Date: {inv['invoice_date']}")
    print(f"  Total: ${inv['total_amount']:.2f}")
    print(f"  Line Items: {len(inv['line_items'])}")
    
    if inv['line_items']:
        print(f"\n  First Line Item:")
        item = inv['line_items'][0]
        print(f"    Description: {item['description']}")
        print(f"    Quantity: {item['quantity']}")
        print(f"    Unit Price: ${item['unit_price']:.2f}")
        print(f"    Total: ${item['line_total']:.2f}")

db.close()

