"""
Database module for storing invoice and line item data in SQLite
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os


class InvoiceDatabase:
    """SQLite database for storing invoices and line items"""
    
    def __init__(self, db_path: str = "invoices.db"):
        """
        Initialize the database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                invoice_date DATE NOT NULL,
                total_amount REAL NOT NULL,
                file_path TEXT,
                source_pdf_name TEXT,
                extraction_method TEXT,
                confidence_score REAL,
                validated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(invoice_number, vendor_name, invoice_date)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                line_order INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                UNIQUE(invoice_id, line_order)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoices_vendor 
            ON invoices(vendor_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoices_date 
            ON invoices(invoice_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_line_items_invoice 
            ON line_items(invoice_id)
        """)
        
        self.conn.commit()
    
    def normalize_vendor_name(self, vendor_name: str) -> str:
        """
        Normalize vendor name
        
        Args:
            vendor_name: Raw vendor name
            
        Returns:
            Normalized vendor name
        """
        if not vendor_name:
            return ""
        
        suffixes = [' inc', ' inc.', ' incorporated', ' corp', ' corp.', 
                   ' corporation', ' ltd', ' ltd.', ' limited', ' llc', 
                   ' llc.', ' pty', ' pty.', ' pty ltd', ' pty ltd.']
        
        normalized = vendor_name.strip()
        normalized_lower = normalized.lower()
        
        for suffix in suffixes:
            if normalized_lower.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
                break
        
        normalized = normalized.title()
        
        return normalized
    
    def normalize_invoice_number(self, invoice_number: str) -> str:
        """
        Normalize invoice number
        
        Args:
            invoice_number: Raw invoice number
            
        Returns:
            Normalized invoice number
        """
        if not invoice_number:
            return ""
        
        normalized = ''.join(c for c in invoice_number if c.isalnum() or c in ['-', '_'])
        normalized = normalized.upper().strip()
        
        return normalized
    
    def normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize date to YYYY-MM-DD format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Normalized date string (YYYY-MM-DD) or None if invalid
        """
        if not date_str:
            return None
        
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%m-%d-%Y',
            '%d-%m-%Y',
            '%Y.%m.%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y'
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
    def normalize_amount(self, amount: Any) -> float:
        """
        Normalize amount to float
        
        Args:
            amount: Amount in various formats (string, int, float)
            
        Returns:
            Normalized float amount
        """
        if amount is None:
            return 0.0
        
        if isinstance(amount, (int, float)):
            return float(amount)
        
        if isinstance(amount, str):
            cleaned = amount.replace('$', '').replace('€', '').replace('£', '')
            cleaned = cleaned.replace(',', '').strip()
            
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        
        return 0.0
    
    def validate_invoice(self, invoice_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate invoice data
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if 'invoice_number' not in invoice_data or not invoice_data.get('invoice_number'):
            errors.append("Missing required field: invoice_number")
        
        if 'vendor_name' not in invoice_data or not invoice_data.get('vendor_name'):
            errors.append("Missing required field: vendor_name")
        
        if 'date' not in invoice_data or not invoice_data.get('date'):
            errors.append("Missing required field: date")
        
        if 'total_amount' not in invoice_data or invoice_data.get('total_amount') is None:
            errors.append("Missing required field: total_amount")
        
        if 'date' in invoice_data and invoice_data['date']:
            normalized_date = self.normalize_date(invoice_data['date'])
            if not normalized_date:
                errors.append(f"Invalid date format: {invoice_data['date']}")
        
        if 'total_amount' in invoice_data:
            try:
                float(invoice_data['total_amount'])
            except (ValueError, TypeError):
                errors.append(f"Invalid total_amount: {invoice_data['total_amount']}")
        
        if 'line_items' in invoice_data:
            for i, item in enumerate(invoice_data['line_items']):
                if not isinstance(item, dict):
                    errors.append(f"Line item {i} is not a dictionary")
                    continue
                
                if 'description' not in item or not item['description']:
                    errors.append(f"Line item {i} missing description")
                
                for field in ['quantity', 'unit_price', 'line_total']:
                    if field in item:
                        try:
                            float(item[field])
                        except (ValueError, TypeError):
                            errors.append(f"Line item {i} has invalid {field}: {item[field]}")
        
        return len(errors) == 0, errors
    
    def save_invoice(self, invoice_data: Dict[str, Any], file_path: str = None) -> Optional[int]:
        """
        Save invoice and line items to database
        
        Args:
            invoice_data: Extracted invoice data dictionary
            file_path: Source file path (optional)
            
        Returns:
            Invoice ID if successful, None otherwise
        """
        if not self.conn:
            self._create_tables()
        
        invoice_number = invoice_data.get('invoice_number', '')
        vendor_name = invoice_data.get('vendor_name', '')
        date_str = invoice_data.get('date', '')
        total_amount = invoice_data.get('total_amount', 0.0)
        extraction_method = invoice_data.get('extraction_method', 'unknown')
        validated = invoice_data.get('validated', False)
        
        normalized_invoice_number = self.normalize_invoice_number(invoice_number)
        normalized_vendor = self.normalize_vendor_name(vendor_name)
        normalized_date = self.normalize_date(date_str)
        normalized_total = self.normalize_amount(total_amount)
        
        if not normalized_date:
            print(f"Warning: Could not normalize date '{date_str}', skipping invoice")
            return None
        
        source_pdf_name = None
        if file_path:
            source_pdf_name = Path(file_path).name
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO invoices (
                    invoice_number, vendor_name, invoice_date, total_amount,
                    file_path, source_pdf_name, extraction_method, validated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(invoice_number, vendor_name, invoice_date) 
                DO UPDATE SET
                    total_amount = excluded.total_amount,
                    file_path = excluded.file_path,
                    source_pdf_name = excluded.source_pdf_name,
                    extraction_method = excluded.extraction_method,
                    validated = excluded.validated,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                normalized_invoice_number,
                normalized_vendor,
                normalized_date,
                normalized_total,
                file_path,
                source_pdf_name,
                extraction_method,
                1 if validated else 0
            ))
            
            invoice_id = cursor.lastrowid
            
            if invoice_id == 0:
                cursor.execute("""
                    SELECT id FROM invoices 
                    WHERE invoice_number = ? AND vendor_name = ? AND invoice_date = ?
                """, (normalized_invoice_number, normalized_vendor, normalized_date))
                row = cursor.fetchone()
                if row:
                    invoice_id = row['id']
                    cursor.execute("DELETE FROM line_items WHERE invoice_id = ?", (invoice_id,))
            
            line_items = invoice_data.get('line_items', [])
            for order, item in enumerate(line_items, 1):
                description = item.get('description', '').strip()
                quantity = self.normalize_amount(item.get('quantity', 0))
                unit_price = self.normalize_amount(item.get('unit_price', 0.0))
                line_total = self.normalize_amount(item.get('line_total', 0.0))
                
                if not description:
                    continue
                
                cursor.execute("""
                    INSERT INTO line_items (
                        invoice_id, description, quantity, unit_price, 
                        line_total, line_order
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    description,
                    quantity,
                    unit_price,
                    line_total,
                    order
                ))
            
            self.conn.commit()
            return invoice_id
            
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Database error saving invoice: {e}")
            return None
    
    def save_extraction_result(self, result: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Save extraction result to database (handles multi-page invoices)
        
        Args:
            result: Extraction result dictionary with pages
            file_path: Source file path
            
        Returns:
            Dictionary with save results
        """
        if not result or result.get('status') != 'success':
            return {
                'saved': False,
                'error': result.get('error', 'Invalid extraction result')
            }
        
        saved_invoices = []
        errors = []
        
        pages = result.get('pages', [])
        for page in pages:
            if 'error' in page:
                continue
            
            is_valid, validation_errors = self.validate_invoice(page)
            if not is_valid:
                errors.extend(validation_errors)
                continue
            
            invoice_id = self.save_invoice(page, file_path)
            if invoice_id:
                saved_invoices.append({
                    'invoice_id': invoice_id,
                    'invoice_number': page.get('invoice_number'),
                    'page_number': page.get('page_number', 1)
                })
            else:
                errors.append(f"Failed to save invoice from page {page.get('page_number', 1)}")
        
        return {
            'saved': len(saved_invoices) > 0,
            'invoice_ids': saved_invoices,
            'errors': errors,
            'total_pages': len(pages),
            'saved_pages': len(saved_invoices)
        }
    
    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """
        Get invoice with line items by ID
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice dictionary with line items or None
        """
        if not self.conn:
            self._create_tables()
        
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        invoice_row = cursor.fetchone()
        
        if not invoice_row:
            return None
        
        cursor.execute("""
            SELECT * FROM line_items 
            WHERE invoice_id = ? 
            ORDER BY line_order
        """, (invoice_id,))
        line_item_rows = cursor.fetchall()
        
        invoice = dict(invoice_row)
        invoice['line_items'] = [
            dict(item) for item in line_item_rows
        ]
        
        return invoice
    
    def get_all_invoices(self, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all invoices with line items
        
        Args:
            limit: Maximum number of invoices to return
            offset: Offset for pagination
            
        Returns:
            List of invoice dictionaries
        """
        if not self.conn:
            self._create_tables()
        
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM invoices ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query)
        invoice_rows = cursor.fetchall()
        
        invoices = []
        for invoice_row in invoice_rows:
            invoice = dict(invoice_row)
            invoice_id = invoice['id']
            
            cursor.execute("""
                SELECT * FROM line_items 
                WHERE invoice_id = ? 
                ORDER BY line_order
            """, (invoice_id,))
            line_item_rows = cursor.fetchall()
            invoice['line_items'] = [dict(item) for item in line_item_rows]
            
            invoices.append(invoice)
        
        return invoices
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def init_database(db_path: str = "invoices.db") -> InvoiceDatabase:
    """
    Initialize and return database instance
    
    Args:
        db_path: Path to database file
        
    Returns:
        InvoiceDatabase instance
    """
    return InvoiceDatabase(db_path)

