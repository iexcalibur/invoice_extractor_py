#!/usr/bin/env python3
"""
Query script for invoice database
"""

import sqlite3
import sys
from database import InvoiceDatabase
from tabulate import tabulate


def query_invoices(db_path: str = "invoices.db", limit: int = 10):
    """Query and display invoices from database"""
    db = InvoiceDatabase(db_path)
    
    # Get all invoices
    invoices = db.get_all_invoices(limit=limit)
    
    if not invoices:
        print("No invoices found in database.")
        return
    
    print(f"\n{'='*80}")
    print(f"INVOICES DATABASE - Total: {len(invoices)}")
    print(f"{'='*80}\n")
    
    # Display summary table
    table_data = []
    for inv in invoices:
        table_data.append([
            inv['id'],
            inv['invoice_number'],
            inv['vendor_name'][:30],
            inv['invoice_date'],
            f"${inv['total_amount']:.2f}",
            len(inv['line_items']),
            inv['extraction_method'] or 'N/A'
        ])
    
    headers = ['ID', 'Invoice #', 'Vendor', 'Date', 'Total', 'Items', 'Method']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    # Ask for details
    if len(sys.argv) > 1 and sys.argv[1] == '--details':
        print("\n" + "="*80)
        print("DETAILED VIEW")
        print("="*80)
        
        for inv in invoices:
            print(f"\nInvoice ID: {inv['id']}")
            print(f"Invoice #: {inv['invoice_number']}")
            print(f"Vendor: {inv['vendor_name']}")
            print(f"Date: {inv['invoice_date']}")
            print(f"Total: ${inv['total_amount']:.2f}")
            print(f"Extraction Method: {inv.get('extraction_method', 'N/A')}")
            print(f"Validated: {'Yes' if inv.get('validated') else 'No'}")
            print(f"\nLine Items ({len(inv['line_items'])}):")
            print("-" * 80)
            
            for item in inv['line_items']:
                print(f"  • {item['description'][:50]:<50} Qty: {item['quantity']:<8} "
                      f"Price: ${item['unit_price']:<10.2f} Total: ${item['line_total']:.2f}")
    
    db.close()


if __name__ == "__main__":
    db_path = sys.argv[2] if len(sys.argv) > 2 else "invoices.db"
    query_invoices(db_path)

