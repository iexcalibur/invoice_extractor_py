#!/usr/bin/env python3
"""
Flask web application for invoice processing
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from pathlib import Path
from typing import List, Dict, Any

from config import Config
from invoice_extractor_with_regex import EnhancedInvoiceExtractor  # Using regex-enabled version
from database import InvoiceDatabase

app = Flask(__name__)
CORS(app)

# Global database instance
db = None


def init_database():
    """Initialize database connection"""
    global db
    try:
        if db is None or db.conn is None:
            db = InvoiceDatabase("invoices.db")
        return db
    except Exception as e:
        # If connection fails, create a new one
        db = InvoiceDatabase("invoices.db")
        return db


@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process_invoices():
    """Process all PDFs/images in the data folder"""
    try:
        data_dir = request.json.get('data_dir', 'data')
        data_path = Path(data_dir)
        
        if not data_path.exists():
            return jsonify({
                'success': False,
                'error': f'Directory not found: {data_dir}'
            }), 404
        
        # Initialize database
        db = init_database()
        
        # Find all supported files
        supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']
        all_files = []
        for ext in supported_extensions:
            all_files.extend(list(data_path.glob(f"*{ext}")))
            all_files.extend(list(data_path.glob(f"*{ext.upper()}")))
        
        all_files = list(set(all_files))
        
        if not all_files:
            return jsonify({
                'success': False,
                'error': f'No supported files found in {data_dir}'
            }), 404
        
        # Initialize extractor with regex enabled (fastest, free for known vendors)
        extractor = EnhancedInvoiceExtractor(
            api_key=Config.get_api_key() if Config.validate() else None,
            use_regex=True,  # Enable regex extraction (first step - fastest, free)
            use_layoutlmv3=True,
            use_ocr=True
        )
        
        results = []
        processed_count = 0
        saved_count = 0
        errors = []
        
        # Process each file
        for file_path in all_files:
            try:
                result = extractor.extract_robust(str(file_path))
                
                # Save to database
                if result.get('status') == 'success':
                    db_result = db.save_extraction_result(result, str(file_path))
                    if db_result['saved']:
                        saved_count += db_result['saved_pages']
                
                # Get extraction method used for each page (to show regex vs LLM usage)
                extraction_methods = []
                for page in result.get('pages', []):
                    method = page.get('extraction_method', 'unknown')
                    confidence = page.get('_confidence', 0.0)
                    extraction_methods.append({
                        'method': method,
                        'confidence': round(confidence, 2) if confidence else None
                    })
                
                results.append({
                    'file': str(file_path.name),
                    'status': result.get('status'),
                    'pages': len(result.get('pages', [])),
                    'saved': db_result.get('saved', False) if result.get('status') == 'success' else False,
                    'extraction_methods': extraction_methods  # Show which method was used (regex/layoutlmv3/ocr/claude)
                })
                
                processed_count += 1
                
            except Exception as e:
                errors.append({
                    'file': str(file_path.name),
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'processed': processed_count,
            'saved_to_db': saved_count,
            'total_files': len(all_files),
            'results': results,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Get all invoices from database"""
    try:
        db = init_database()
        
        # Ensure connection is open
        if db.conn is None:
            db._create_tables()
        
        invoices = db.get_all_invoices()
        
        # Format for frontend
        formatted_invoices = []
        for inv in invoices:
            formatted_invoices.append({
                'id': inv['id'],
                'invoice_number': inv['invoice_number'],
                'vendor_name': inv['vendor_name'],
                'invoice_date': inv['invoice_date'],
                'total_amount': float(inv['total_amount']),
                'line_items_count': len(inv['line_items']),
                'extraction_method': inv.get('extraction_method', 'N/A'),
                'validated': bool(inv.get('validated', False)),
                'line_items': [
                    {
                        'description': item['description'],
                        'quantity': float(item['quantity']),
                        'unit_price': float(item['unit_price']),
                        'line_total': float(item['line_total'])
                    }
                    for item in inv['line_items']
                ]
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_invoices),
            'invoices': formatted_invoices
        })
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_database():
    """Clear all data from database"""
    try:
        db = init_database()
        cursor = db.conn.cursor()
        
        # Delete all line items first (foreign key constraint)
        cursor.execute("DELETE FROM line_items")
        
        # Delete all invoices
        cursor.execute("DELETE FROM invoices")
        
        db.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database cleared successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get processing status and database stats"""
    try:
        db = init_database()
        
        # Ensure connection is open
        if db.conn is None:
            db._create_tables()
        
        cursor = db.conn.cursor()
        
        # Count invoices
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        # Count line items
        cursor.execute("SELECT COUNT(*) FROM line_items")
        line_item_count = cursor.fetchone()[0]
        
        # Check data folder
        data_path = Path('data')
        supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']
        all_files = []
        if data_path.exists():
            for ext in supported_extensions:
                all_files.extend(list(data_path.glob(f"*{ext}")))
                all_files.extend(list(data_path.glob(f"*{ext.upper()}")))
        
        return jsonify({
            'success': True,
            'database': {
                'invoices': invoice_count,
                'line_items': line_item_count
            },
            'data_folder': {
                'exists': data_path.exists(),
                'file_count': len(set(all_files))
            }
        })
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5001)

