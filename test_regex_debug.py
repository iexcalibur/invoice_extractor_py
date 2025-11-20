#!/usr/bin/env python3
"""
Debug script to test regex extraction and see what's happening
"""

import os
import sys
from pathlib import Path

# Enable debug mode
os.environ["DEBUG_REGEX"] = "true"

from invoice_extractor_with_regex import EnhancedInvoiceExtractor

def test_regex_extraction(file_path: str):
    """Test regex extraction on a single file"""
    print("="*80)
    print(f"Testing Regex Extraction: {file_path}")
    print("="*80)
    
    extractor = EnhancedInvoiceExtractor(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        use_regex=True,
        use_layoutlmv3=False,  # Disable to test regex only
        use_ocr=True
    )
    
    result = extractor.extract_robust(file_path)
    
    print("\n" + "="*80)
    print("RESULTS:")
    print("="*80)
    
    if result.get('status') == 'success':
        for page in result.get('pages', []):
            method = page.get('extraction_method', 'unknown')
            confidence = page.get('_confidence', 0)
            print(f"\nExtraction Method: {method}")
            print(f"Confidence: {confidence:.2f}")
            print(f"Invoice #: {page.get('invoice_number', 'N/A')}")
            print(f"Vendor: {page.get('vendor_name', 'N/A')}")
            print(f"Date: {page.get('date', 'N/A')}")
            print(f"Total: ${page.get('total_amount', 0):.2f}")
            print(f"Line Items: {len(page.get('line_items', []))}")
            
            if page.get('line_items'):
                print("\nFirst 3 line items:")
                for item in page.get('line_items', [])[:3]:
                    print(f"  - {item.get('description', 'N/A')[:30]}: qty={item.get('quantity')}, price=${item.get('unit_price', 0):.2f}")
    else:
        print(f"Status: {result.get('status')}")
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        # Find first PDF in data folder
        data_dir = Path("data")
        pdf_files = list(data_dir.glob("*.pdf"))
        if pdf_files:
            test_file = str(pdf_files[0])
            print(f"No file specified, using: {test_file}")
        else:
            print("No PDF files found in data folder")
            sys.exit(1)
    
    test_regex_extraction(test_file)

