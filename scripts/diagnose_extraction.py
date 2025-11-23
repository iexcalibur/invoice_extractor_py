#!/usr/bin/env python3
"""
Diagnostic script to identify why extraction is missing invoices/line items
"""

import os
import sys
from pathlib import Path

# Try to use venv if available
venv_python = Path(__file__).parent / "venv" / "bin" / "python"
if venv_python.exists():
    # Note: This won't change the current process, but helps with shebang
    pass

# PDF path - relative to project root
project_root = Path(__file__).parent.parent
PDF_PATH = project_root / "data" / "Copy of ARPFIINVOEBTCHLASER (4).pdf"

def diagnose():
    """Run comprehensive diagnostics"""
    
    print("="*80)
    print("INVOICE EXTRACTION DIAGNOSTICS")
    print("="*80)
    
    # Check file exists
    print("\n1. FILE CHECK")
    print("-"*80)
    pdf_path_str = str(PDF_PATH)
    if PDF_PATH.exists():
        file_size = PDF_PATH.stat().st_size / 1024
        print(f"✓ File exists: {pdf_path_str}")
        print(f"✓ File size: {file_size:.2f} KB")
    else:
        print(f"❌ File not found: {pdf_path_str}")
        return
    
    # Check PDF conversion
    print("\n2. PDF CONVERSION CHECK")
    print("-"*80)
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path_str, dpi=200)
        print(f"✓ PDF converted successfully")
        print(f"✓ Number of pages: {len(images)}")
        print(f"✓ Image size (first page): {images[0].size}")
    except Exception as e:
        print(f"❌ PDF conversion failed: {e}")
        return
    
    # Check OCR on first page
    print("\n3. OCR CHECK (Page 1)")
    print("-"*80)
    ocr_text = None
    try:
        import pytesseract
        ocr_text = pytesseract.image_to_string(images[0])
        
        print(f"✓ OCR text length: {len(ocr_text)} chars")
        print(f"\nFirst 500 characters:")
        print("-"*80)
        print(ocr_text[:500])
        print("-"*80)
        
        # Check for key terms
        key_terms = {
            'INVOICE': '378093' in ocr_text or 'INVOICE' in ocr_text,
            'Pacific Food': 'Pacific' in ocr_text or 'pacific' in ocr_text.lower(),
            'Invoice number 378093': '378093' in ocr_text,
            'Invoice number 378094': '378094' in ocr_text,
            'FLOUR POWER': 'FLOUR' in ocr_text or 'flour' in ocr_text.lower(),
            'Total amount': '522.75' in ocr_text or '522' in ocr_text
        }
        
        print(f"\nKey terms found:")
        for term, found in key_terms.items():
            status = "✓" if found else "❌"
            print(f"  {status} {term}")
        
    except ImportError:
        print(f"⚠ Tesseract not available, skipping OCR check")
    except Exception as e:
        print(f"❌ OCR failed: {e}")
    
    # Check regex extraction
    print("\n4. REGEX EXTRACTION CHECK")
    print("-"*80)
    if ocr_text is None:
        print("⚠ Skipping regex check - OCR text not available")
    else:
        try:
            import sys
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))
            from core.regex_extractor import RegexInvoiceExtractor
            extractor = RegexInvoiceExtractor()
            
            # Detect vendor
            vendor = extractor.detect_vendor(ocr_text, debug=True)
            print(f"Detected vendor: {vendor}")
            
            if vendor:
                # Try extraction
                result = extractor.extract(ocr_text, debug=True)
                
                if result:
                    print(f"\n✓ Regex extraction successful!")
                    print(f"  Invoice #: {result.get('invoice_number')}")
                    print(f"  Date: {result.get('date')}")
                    print(f"  Total: ${result.get('total_amount')}")
                    print(f"  Line items: {len(result.get('line_items', []))}")
                    print(f"  Confidence: {result.get('_confidence', 0):.2%}")
                else:
                    print(f"❌ Regex extraction returned None")
            else:
                print(f"❌ Vendor not detected")
                
        except ImportError:
            print(f"⚠ regex_extractor not available")
        except Exception as e:
            print(f"❌ Regex check failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Check database
    print("\n5. DATABASE CHECK")
    print("-"*80)
    try:
        import sys
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        from core.database import InvoiceDatabase
        project_root = Path(__file__).parent.parent
        db = InvoiceDatabase(str(project_root / "invoices.db"))
        
        # Get current invoices
        invoices = db.get_all_invoices()
        print(f"Current invoices in database: {len(invoices)}")
        
        if invoices:
            print(f"\nExisting invoice numbers:")
            for inv in invoices:
                print(f"  • {inv['invoice_number']} - {inv['vendor_name']} - ${inv['total_amount']:.2f}")
        
        db.close()
    except Exception as e:
        print(f"❌ Database check failed: {e}")
    
    # Check for common issues
    print("\n6. COMMON ISSUES CHECK")
    print("-"*80)
    
    issues = []
    
    if ocr_text is None:
        print("⚠ Skipping common issues check - OCR text not available")
    else:
        # Check if SHIPPED column is being used
        if 'SHIPPED' in ocr_text and 'ORDERED' in ocr_text:
            print("✓ Document has ORDERED and SHIPPED columns")
            print("  → Ensure extraction uses SHIPPED column for quantity")
        
        # Check for missing line items
        if 'FLOUR POWER' in ocr_text:
            print("✓ First line item (FLOUR POWER) present in OCR")
        else:
            issues.append("First line item not found in OCR text")
        
        # Check invoice number format
        if '378093' in ocr_text:
            print("✓ Invoice number 378093 present in OCR")
        else:
            issues.append("Invoice number 378093 not found in OCR text")
        
        if issues:
            print(f"\n⚠ Potential issues found:")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print(f"\n✓ No obvious issues detected")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    print("""
1. Empty the database first:
   python empty_db.py
   
2. Re-run extraction with debug mode:
   DEBUG_REGEX=true python main.py [pdf_file]
   
3. Check that regex patterns match Pacific Food Importers format:
   - Invoice numbers must start with 378
   - Use SHIPPED column (not ORDERED) for quantities
   - Extract all 6 line items from page 1
   
4. If regex fails, check LayoutLMv3/OCR fallback is working
   
5. Verify database save logic doesn't skip valid invoices
    """)
    
    print("="*80)


if __name__ == "__main__":
    diagnose()
