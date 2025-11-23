#!/usr/bin/env python3
"""
Script to empty/reset the invoice database

This script provides options to:
1. Delete all data (keep schema)
2. Drop all tables (complete reset)
3. Reset with fresh schema
"""

import sqlite3
import os
from pathlib import Path


def empty_database(db_path: str = "invoices.db", keep_schema: bool = True):
    """
    Empty the database
    
    Args:
        db_path: Path to database file
        keep_schema: If True, only delete data. If False, drop all tables
    """
    if not os.path.exists(db_path):
        print(f"⚠ Database file not found: {db_path}")
        return
    
    # Backup first
    backup_path = f"{db_path}.backup"
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if keep_schema:
        # Delete all data but keep schema
        print("\n🗑️  Deleting all data (keeping schema)...")
        
        # Delete line items first (foreign key constraint)
        cursor.execute("DELETE FROM line_items")
        deleted_line_items = cursor.rowcount
        print(f"  ✓ Deleted {deleted_line_items} line items")
        
        # Delete invoices
        cursor.execute("DELETE FROM invoices")
        deleted_invoices = cursor.rowcount
        print(f"  ✓ Deleted {deleted_invoices} invoices")
        
        # Reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='line_items'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='invoices'")
        print("  ✓ Reset auto-increment counters")
        
    else:
        # Drop all tables (complete reset)
        print("\n🗑️  Dropping all tables (complete reset)...")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            if table_name != 'sqlite_sequence':
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                print(f"  ✓ Dropped table: {table_name}")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Database emptied successfully!")
    
    if keep_schema:
        # Verify tables still exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📋 Remaining tables: {', '.join([t[0] for t in tables])}")
        conn.close()


def delete_database(db_path: str = "invoices.db"):
    """
    Completely delete the database file
    
    Args:
        db_path: Path to database file
    """
    if os.path.exists(db_path):
        # Create backup first
        backup_path = f"{db_path}.backup"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
        
        # Delete the file
        os.remove(db_path)
        print(f"✓ Database file deleted: {db_path}")
    else:
        print(f"⚠ Database file not found: {db_path}")


def get_database_stats(db_path: str = "invoices.db"):
    """
    Show current database statistics
    
    Args:
        db_path: Path to database file
    """
    if not os.path.exists(db_path):
        print(f"⚠ Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    
    # Invoices
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
    
    # Line items
    cursor.execute("SELECT COUNT(*) FROM line_items")
    line_item_count = cursor.fetchone()[0]
    print(f"\nLine Items: {line_item_count}")
    
    # Database size
    db_size = os.path.getsize(db_path) / 1024  # KB
    print(f"\nDatabase Size: {db_size:.2f} KB")
    
    print("="*60 + "\n")
    
    conn.close()


def find_database():
    """
    Find the database file in common locations
    
    Returns:
        Path to database file or None if not found
    """
    # Common locations to check
    possible_paths = [
        "invoices.db",  # Current directory
        "notebooks/invoices.db",  # Notebooks folder
        "../notebooks/invoices.db",  # If running from scripts/
        "data/invoices.db",  # Data folder
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def main():
    """Main interactive menu"""
    import sys
    
    # Check for command-line argument
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Try to find database in common locations
        db_path = find_database()
        if not db_path:
            db_path = "invoices.db"  # Default
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"⚠ Database not found: {db_path}")
        print("\nSearched in:")
        print("  - invoices.db (current directory)")
        print("  - notebooks/invoices.db")
        print("  - data/invoices.db")
        print("\nYou can specify a path: python3 scripts/empty_db.py <path/to/invoices.db>")
        print("\nNothing to empty. Database will be created when you run the extraction.")
        return
    
    print(f"✓ Found database: {os.path.abspath(db_path)}\n")
    
    # Show current stats
    get_database_stats(db_path)
    
    # Interactive menu
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
        confirm = input("\n⚠ This will delete all invoices and line items. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            empty_database(db_path, keep_schema=True)
        else:
            print("❌ Cancelled")
    
    elif choice == "2":
        confirm = input("\n⚠ This will drop all tables. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            empty_database(db_path, keep_schema=False)
        else:
            print("❌ Cancelled")
    
    elif choice == "3":
        confirm = input("\n⚠ This will delete the database file. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_database(db_path)
        else:
            print("❌ Cancelled")
    
    elif choice == "4":
        print("✓ Statistics displayed above")
    
    elif choice == "5":
        print("❌ Cancelled")
    
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()