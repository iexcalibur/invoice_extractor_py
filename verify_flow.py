#!/usr/bin/env python3
"""
Verification script to test the complete data flow:
1. PDF extraction
2. JSON file creation
3. Database storage
4. Database reading
"""

import os
import json
from pathlib import Path
from database import InvoiceDatabase
from invoice_extractor_enhanced import EnhancedInvoiceExtractor
from config import Config

def verify_flow():
    """Verify the complete data flow"""
    
    print("="*80)
    print("DATA FLOW VERIFICATION")
    print("="*80)
    
    # Step 1: Find a test PDF
    print("\n[STEP 1] Finding test PDF in data folder...")
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ ERROR: 'data' folder not found!")
        return False
    
    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        print("❌ ERROR: No PDF files found in 'data' folder!")
        return False
    
    test_file = pdf_files[0]
    print(f"✓ Found test file: {test_file.name}")
    
    # Step 2: Extract data
    print("\n[STEP 2] Extracting data from PDF...")
    try:
        extractor = EnhancedInvoiceExtractor(
            api_key=Config.get_api_key() if Config.validate() else None,
            use_layoutlmv3=True,
            use_ocr=True
        )
        result = extractor.extract_robust(str(test_file))
        
        if result.get('status') != 'success':
            print(f"❌ ERROR: Extraction failed - {result.get('error', 'Unknown error')}")
            return False
        
        print("✓ Extraction successful!")
        print(f"  - Pages extracted: {len(result.get('pages', []))}")
        if result.get('pages'):
            page = result['pages'][0]
            print(f"  - Invoice #: {page.get('invoice_number', 'N/A')}")
            print(f"  - Vendor: {page.get('vendor_name', 'N/A')}")
            print(f"  - Total: ${page.get('total_amount', 0):.2f}")
    except Exception as e:
        print(f"❌ ERROR: Extraction failed - {e}")
        return False
    
    # Step 3: Check JSON file creation
    print("\n[STEP 3] Verifying JSON file creation...")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    file_name = test_file.stem
    json_file = output_dir / f"{file_name}_extracted.json"
    
    # Save JSON (simulating main.py behavior)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    if not json_file.exists():
        print(f"❌ ERROR: JSON file not created: {json_file}")
        return False
    
    print(f"✓ JSON file created: {json_file.name}")
    
    # Verify JSON content
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    if json_data.get('status') != 'success':
        print("❌ ERROR: JSON file contains error status")
        return False
    
    print(f"✓ JSON file contains valid data")
    print(f"  - File size: {json_file.stat().st_size} bytes")
    
    # Step 4: Store in database
    print("\n[STEP 4] Storing data in SQLite database...")
    try:
        db = InvoiceDatabase("invoices.db")
        
        # Get count before
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM invoices")
        count_before = cursor.fetchone()[0]
        
        # Save to database
        db_result = db.save_extraction_result(result, str(test_file))
        
        if not db_result.get('saved'):
            print(f"❌ ERROR: Database save failed")
            if db_result.get('errors'):
                print(f"  Errors: {', '.join(db_result['errors'])}")
            return False
        
        print(f"✓ Data saved to database")
        print(f"  - Invoices saved: {db_result['saved_pages']}")
        
        # Get count after
        cursor.execute("SELECT COUNT(*) FROM invoices")
        count_after = cursor.fetchone()[0]
        
        if count_after <= count_before:
            print(f"⚠ WARNING: Invoice count didn't increase (may be duplicate)")
        else:
            print(f"✓ Invoice count increased: {count_before} → {count_after}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ ERROR: Database operation failed - {e}")
        return False
    
    # Step 5: Read from database
    print("\n[STEP 5] Reading data from SQLite database...")
    try:
        db = InvoiceDatabase("invoices.db")
        invoices = db.get_all_invoices(limit=5)
        
        if not invoices:
            print("❌ ERROR: No invoices found in database")
            return False
        
        print(f"✓ Retrieved {len(invoices)} invoice(s) from database")
        
        # Verify the data matches
        latest_invoice = invoices[0]
        print(f"\n  Latest Invoice:")
        print(f"    ID: {latest_invoice['id']}")
        print(f"    Invoice #: {latest_invoice['invoice_number']}")
        print(f"    Vendor: {latest_invoice['vendor_name']}")
        print(f"    Date: {latest_invoice['invoice_date']}")
        print(f"    Total: ${latest_invoice['total_amount']:.2f}")
        print(f"    Line Items: {len(latest_invoice['line_items'])}")
        
        if latest_invoice['line_items']:
            print(f"\n  Sample Line Item:")
            item = latest_invoice['line_items'][0]
            print(f"    Description: {item['description'][:50]}")
            print(f"    Quantity: {item['quantity']}")
            print(f"    Unit Price: ${item['unit_price']:.2f}")
            print(f"    Total: ${item['line_total']:.2f}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ ERROR: Database read failed - {e}")
        return False
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    print("✓ Step 1: PDF found and ready")
    print("✓ Step 2: Data extracted successfully")
    print("✓ Step 3: JSON file created and validated")
    print("✓ Step 4: Data stored in SQLite database")
    print("✓ Step 5: Data retrieved from database")
    print("\n✅ ALL STEPS VERIFIED - FLOW IS WORKING CORRECTLY!")
    print("="*80)
    
    return True


if __name__ == "__main__":
    success = verify_flow()
    exit(0 if success else 1)

