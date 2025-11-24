#!/usr/bin/env python3

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List

from core.invoice_extractor import EnhancedInvoiceExtractor
from core.config import Config
from core.database import InvoiceDatabase


def process_single_file(file_path: str, output_dir: str = "output", db: InvoiceDatabase = None) -> dict:
    print(f"\n{'='*60}")
    print(f"Processing: {file_path}")
    print(f"{'='*60}")
    
    try:
        extractor = EnhancedInvoiceExtractor(
            api_key=Config.get_api_key() if Config.validate() else None,
            use_regex=True,  
            use_layoutlmv3=True,
            use_ocr=True
        )
        result = extractor.extract_robust(file_path)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_name = Path(file_path).stem
        output_file = output_path / f"{file_name}_extracted.json"
        
        with open(str(output_file), 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_file}")
        
        if result.get('status') == 'success':
            print("\n✓ Extraction successful!")
            for page in result.get('pages', []):
                if page.get('validated'):
                    print(f"\n  Page {page.get('page_number', '?')}:")
                    print(f"    Invoice #: {page.get('invoice_number', 'N/A')}")
                    print(f"    Date: {page.get('date', 'N/A')}")
                    print(f"    Vendor: {page.get('vendor_name', 'N/A')}")
                    print(f"    Total: ${page.get('total_amount', 0):.2f}")
                    print(f"    Line Items: {len(page.get('line_items', []))}")
            
            vendor_name = None
            for page in result.get('pages', []):
                if page.get('validated'):
                    page_vendor = page.get('vendor_name', '')
                    if "Frank's Quality Produce" in page_vendor or "PACIFIC FOOD IMPORTERS" in page_vendor.upper() or "Pacific Food" in page_vendor:
                        vendor_name = page_vendor
                        break
            
            
            if db:
                db_result = db.save_extraction_result(result, file_path)
                if db_result['saved']:
                    print(f"\n✓ Saved to database: {db_result['saved_pages']} invoice(s)")
                    for inv in db_result['invoice_ids']:
                        print(f"    Invoice ID: {inv['invoice_id']} (#{inv['invoice_number']})")
                elif db_result.get('errors'):
                    print(f"\n⚠ Database save warnings: {', '.join(db_result['errors'])}")
        elif result.get('status') == 'manual_review_needed':
            print("\n⚠ Extraction completed but validation failed - manual review recommended")
        else:
            print(f"\n✗ Error: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"\n✗ Error processing {file_path}: {e}")
        return {"status": "error", "error": str(e), "pdf": file_path}


def process_directory(directory: str, output_dir: str = "output", recursive: bool = False, db: InvoiceDatabase = None) -> List[dict]:
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"Error: Directory not found: {directory}")
        return []
    
    supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']
    
    if recursive:
        all_files = []
        for ext in supported_extensions:
            all_files.extend(list(directory_path.rglob(f"*{ext}")))
            all_files.extend(list(directory_path.rglob(f"*{ext.upper()}")))
    else:
        all_files = []
        for ext in supported_extensions:
            all_files.extend(list(directory_path.glob(f"*{ext}")))
            all_files.extend(list(directory_path.glob(f"*{ext.upper()}")))
    
    all_files = list(set(all_files))
    
    if not all_files:
        print(f"No supported files (PDF or images) found in {directory}")
        return []
    
    print(f"Found {len(all_files)} file(s) (PDF and images)")
    
    results = []
    for i, file_path in enumerate(all_files, 1):
        print(f"\n[{i}/{len(all_files)}]")
        result = process_single_file(str(file_path), output_dir, db)
        results.append(result)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    successful = sum(1 for r in results if r.get('status') == 'success')
    needs_review = sum(1 for r in results if r.get('status') == 'manual_review_needed')
    errors = sum(1 for r in results if r.get('status') == 'error')
    
    print(f"Total processed: {len(results)}")
    print(f"✓ Successful: {successful}")
    print(f"⚠ Needs review: {needs_review}")
    print(f"✗ Errors: {errors}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Extract invoice data from PDF and image files using hybrid approach (Regex → LayoutLMv3 → OCR → Claude)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single PDF or image
  python main.py invoice.pdf
  python main.py invoice.png
  
  # Process all PDFs and images in a directory
  python main.py data/
  
  # Process recursively with custom output directory
  python main.py data/ -o results/ -r
  
  # Process with specific API key
  ANTHROPIC_API_KEY=your-key python main.py invoice.pdf
        """
    )
    
    parser.add_argument(
        'input',
        help='PDF/image file or directory containing PDFs/images'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='outputs',
        help='Output directory for results (default: outputs)'
    )
    
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Process PDFs recursively in subdirectories'
    )
    
    parser.add_argument(
        '--api-key',
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    
    parser.add_argument(
        '--db',
        default='invoices.db',
        help='SQLite database file path (default: invoices.db). Use --no-db to disable database saving.'
    )
    
    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Disable database saving (only save JSON files)'
    )
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        Config.ANTHROPIC_API_KEY = args.api_key
        os.environ['ANTHROPIC_API_KEY'] = args.api_key
    
    if not Config.validate():
        print("Warning: ANTHROPIC_API_KEY not set!")
        print("Enhanced extractor can work without it (using LayoutLMv3/OCR),")
        print("but Claude fallback won't be available.")
    
    db = None
    if not args.no_db:
        try:
            db = InvoiceDatabase(args.db)
            print(f"✓ Database initialized: {args.db}")
        except Exception as e:
            print(f"⚠ Warning: Could not initialize database: {e}")
            print("  Continuing without database storage...")
    
    input_path = Path(args.input)
    
    supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']
    
    if input_path.is_file():
        file_ext = input_path.suffix.lower()
        if file_ext not in supported_extensions:
            print(f"Error: {args.input} is not a supported file type")
            print(f"Supported: {', '.join(supported_extensions)}")
            sys.exit(1)
        process_single_file(str(input_path), args.output, db)
    elif input_path.is_dir():
        process_directory(str(input_path), args.output, args.recursive, db)
    else:
        print(f"Error: {args.input} not found")
        sys.exit(1)
    
    if db:
        db.close()
        print(f"\n✓ Database connection closed")


if __name__ == "__main__":
    main()