#!/usr/bin/env python3

import sqlite3
import os
from pathlib import Path


def empty_database(db_path: str = "invoices.db", keep_schema: bool = True):
    if not os.path.exists(db_path):
        print(f"WARNING: Database file not found: {db_path}")
        return
    
    backup_path = f"{db_path}.backup"
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if keep_schema:
        print("\nDeleting all data (keeping schema)...")
        
        cursor.execute("DELETE FROM line_items")
        deleted_line_items = cursor.rowcount
        print(f"  Deleted {deleted_line_items} line items")
        
        cursor.execute("DELETE FROM invoices")
        deleted_invoices = cursor.rowcount
        print(f"  Deleted {deleted_invoices} invoices")
        
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='line_items'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='invoices'")
        print("  Reset auto-increment counters")
        
    else:
        print("\nDropping all tables (complete reset)...")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            if table_name != 'sqlite_sequence':
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                print(f"  Dropped table: {table_name}")
    
    conn.commit()
    conn.close()
    
    print("\nDatabase emptied successfully!")
    
    if keep_schema:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nRemaining tables: {', '.join([t[0] for t in tables])}")
        conn.close()


def delete_database(db_path: str = "invoices.db"):
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")
        
        os.remove(db_path)
        print(f"Database file deleted: {db_path}")
    else:
        print(f"WARNING: Database file not found: {db_path}")


def get_database_stats(db_path: str = "invoices.db"):
    if not os.path.exists(db_path):
        print(f"WARNING: Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    invoice_count = cursor.fetchone()[0]
    print(f"\nInvoices: {invoice_count}")
    
    if invoice_count > 0:
        cursor.execute("SELECT SUM(total_amount) FROM invoices")
        total_amount = cursor.fetchone()[0]
        print(f"  Total Amount: ${total_amount:,.2f}")
        
        cursor.execute("SELECT COUNT(DISTINCT vendor_name) FROM invoices")
        vendor_count = cursor.fetchone()[0]
        print(f"  Unique Vendors: {vendor_count}")
        
        cursor.execute("SELECT MIN(invoice_date), MAX(invoice_date) FROM invoices")
        date_range = cursor.fetchone()
        print(f"  Date Range: {date_range[0]} to {date_range[1]}")
    
    cursor.execute("SELECT COUNT(*) FROM line_items")
    line_item_count = cursor.fetchone()[0]
    print(f"\nLine Items: {line_item_count}")
    
    db_size = os.path.getsize(db_path) / 1024
    print(f"\nDatabase Size: {db_size:.2f} KB")
    
    print("="*60 + "\n")
    
    conn.close()


def find_database():
    possible_paths = [
        "invoices.db",
        "notebooks/invoices.db",
        "../notebooks/invoices.db",
        "data/invoices.db",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def main():
    import sys
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = find_database()
        if not db_path:
            db_path = "invoices.db"
    
    if not os.path.exists(db_path):
        print(f"WARNING: Database not found: {db_path}")
        print("\nSearched in:")
        print("  - invoices.db (current directory)")
        print("  - notebooks/invoices.db")
        print("  - data/invoices.db")
        print("\nYou can specify a path: python3 scripts/empty_db.py <path/to/invoices.db>")
        print("\nNothing to empty. Database will be created when you run the extraction.")
        return
    
    print(f"Found database: {os.path.abspath(db_path)}\n")
    
    get_database_stats(db_path)
    
    print("What would you like to do?")
    print("-" * 60)
    print("1. Delete all data (keep schema) - RECOMMENDED")
    print("2. Drop all tables (complete reset)")
    print("3. Delete database file completely")
    print("4. Show statistics only (no changes)")
    print("5. Cancel")
    print("-" * 60)
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        confirm = input("\nWARNING: This will delete all invoices and line items. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            empty_database(db_path, keep_schema=True)
        else:
            print("Cancelled")
    
    elif choice == "2":
        confirm = input("\nWARNING: This will drop all tables. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            empty_database(db_path, keep_schema=False)
        else:
            print("Cancelled")
    
    elif choice == "3":
        confirm = input("\nWARNING: This will delete the database file. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_database(db_path)
        else:
            print("Cancelled")
    
    elif choice == "4":
        print("Statistics displayed above")
    
    elif choice == "5":
        print("Cancelled")
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()