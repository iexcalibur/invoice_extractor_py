import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os


class InvoiceDatabase:
    def __init__(self, db_path: str = "invoices.db"):
        self.db_path = db_path
        self.conn = None
        self._create_tables()
    
    def _create_tables(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
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
            CREATE INDEX IF NOT EXISTS idx_invoices_number 
            ON invoices(invoice_number)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_line_items_invoice 
            ON line_items(invoice_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_line_items_invoice_order 
            ON line_items(invoice_id, line_order)
        """)
        
        self.conn.commit()
    
    def normalize_vendor_name(self, vendor_name: str) -> str:
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
        if not invoice_number:
            return ""
        
        normalized = ''.join(c for c in invoice_number if c.isalnum() or c in ['-', '_'])
        normalized = normalized.upper().strip()
        
        return normalized
    
    def normalize_date(self, date_str: str) -> Optional[str]:
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
        errors = []
        
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
        if not self.conn:
            self._create_tables()
        
        invoice_number = invoice_data.get('invoice_number', '')
        vendor_name = invoice_data.get('vendor_name', '')
        
        if not invoice_number:
            print(f"  ⚠ Skipping invoice: no invoice number")
            return None
        
        normalized_invoice_number = self.normalize_invoice_number(invoice_number)
        normalized_vendor = self.normalize_vendor_name(vendor_name)
        
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM invoices WHERE invoice_number = ?",
            (normalized_invoice_number,)
        )
        existing = cursor.fetchone()
        
        if existing:
            existing_id = existing['id']
            print(f"  ℹ Invoice {invoice_number} already exists")
            return None
        
        date_str = invoice_data.get('date', '')
        total_amount = invoice_data.get('total_amount', 0.0)
        extraction_method = invoice_data.get('extraction_method', 'unknown')
        validated = invoice_data.get('validated', False)
        
        normalized_date = self.normalize_date(date_str)
        normalized_total = self.normalize_amount(total_amount)
        
        if not normalized_date:
            print(f"Warning: Could not normalize date '{date_str}', skipping invoice")
            return None
        
        source_pdf_name = None
        if file_path:
            source_pdf_name = Path(file_path).name
        
        try:
            cursor.execute("""
                INSERT INTO invoices (
                    invoice_number, vendor_name, invoice_date, total_amount,
                    file_path, source_pdf_name, extraction_method, validated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            
            vendor_name = page.get('vendor_name', '')
            invoice_number = str(page.get('invoice_number', ''))
            
            try:
                from .vendor_registry import get_vendor_registry
                vendor_registry = get_vendor_registry()
                
                if vendor_registry and invoice_number:
                    vendor = vendor_registry.detect_vendor(
                        vendor_name=vendor_name,
                        invoice_number=invoice_number,
                        debug=False
                    )
                    
                    if vendor:
                        if vendor_name.lower() != vendor.vendor_name.lower():
                            print(f"  ⚠ Fixing vendor name: '{vendor_name}' -> '{vendor.vendor_name}'")
                            page['vendor_name'] = vendor.vendor_name
                        
                        is_valid, error_msg = vendor_registry.validate_invoice_number(
                            invoice_number,
                            vendor,
                            debug=False
                        )
                        
                        if not is_valid:
                            errors.append(
                                f"Page {page.get('page_number', 1)}: Invalid invoice number '{invoice_number}' "
                                f"for {vendor.vendor_name} - {error_msg}"
                            )
                            continue
            except (ImportError, Exception):
                pass
            
            is_valid, validation_errors = self.validate_invoice(page)
            if not is_valid:
                errors.extend(validation_errors)
                continue
            
            invoice_number = page.get('invoice_number', '')
            date_str = page.get('date', '')
            page_num = page.get('page_number', 1)
            
            if not invoice_number:
                errors.append(f"Page {page_num}: Cannot save - missing invoice number")
                continue
            
            normalized_date = self.normalize_date(date_str)
            if not normalized_date:
                errors.append(f"Page {page_num}: Cannot save - invalid date format '{date_str}' (Invoice: {invoice_number})")
                continue
            
            normalized_invoice_number = self.normalize_invoice_number(invoice_number)
            if not self.conn:
                self._create_tables()
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id FROM invoices WHERE invoice_number = ?",
                (normalized_invoice_number,)
            )
            existing = cursor.fetchone()
            if existing:
                errors.append(f"Page {page_num}: Invoice {invoice_number} already exists in database")
                continue
            
            invoice_id = self.save_invoice(page, file_path)
            if invoice_id:
                saved_invoices.append({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                    'page_number': page_num
                })
            else:
                errors.append(f"Page {page_num}: Failed to save invoice {invoice_number} - database error occurred")
        
        return {
            'saved': len(saved_invoices) > 0,
            'invoice_ids': saved_invoices,
            'errors': errors,
            'total_pages': len(pages),
            'saved_pages': len(saved_invoices)
        }
    
    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
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
    
    def update_invoice_number(self, invoice_id: int, new_invoice_number: str) -> bool:
        if not self.conn:
            self._create_tables()
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE invoices 
                SET invoice_number = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_invoice_number, invoice_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error updating invoice number: {e}")
            return False
    
    def get_invoices_by_vendor(self, vendor_name: str) -> List[Dict[str, Any]]:
        if not self.conn:
            self._create_tables()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM invoices 
            WHERE vendor_name LIKE ?
            ORDER BY created_at DESC
        """, (f"%{vendor_name}%",))
        
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
    
    def get_fact_table_data(self, invoice_ids: List[int] = None) -> List[Dict[str, Any]]:
        if not self.conn:
            self._create_tables()
        
        cursor = self.conn.cursor()
        
        if invoice_ids:
            placeholders = ','.join(['?'] * len(invoice_ids))
            query = f"""
                SELECT 
                    li.id as line_item_id,
                    li.invoice_id,
                    li.description,
                    li.quantity,
                    li.unit_price,
                    li.line_total,
                    li.line_order,
                    i.id as invoice_dim_id,
                    i.invoice_number,
                    i.vendor_name,
                    i.invoice_date,
                    i.total_amount
                FROM line_items li
                JOIN invoices i ON li.invoice_id = i.id
                WHERE li.invoice_id IN ({placeholders})
                ORDER BY li.invoice_id, li.line_order
            """
            cursor.execute(query, invoice_ids)
        else:
            query = """
                SELECT 
                    li.id as line_item_id,
                    li.invoice_id,
                    li.description,
                    li.quantity,
                    li.unit_price,
                    li.line_total,
                    li.line_order,
                    i.id as invoice_dim_id,
                    i.invoice_number,
                    i.vendor_name,
                    i.invoice_date,
                    i.total_amount
                FROM line_items li
                JOIN invoices i ON li.invoice_id = i.id
                ORDER BY li.invoice_id, li.line_order
            """
            cursor.execute(query)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_dimension_table_data(self, vendor_name: str = None, start_date: str = None, 
                                 end_date: str = None) -> List[Dict[str, Any]]:
        if not self.conn:
            self._create_tables()
        
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM invoices WHERE 1=1"
        params = []
        
        if vendor_name:
            query += " AND vendor_name LIKE ?"
            params.append(f"%{vendor_name}%")
        
        if start_date:
            query += " AND invoice_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND invoice_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY invoice_date DESC, id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def init_database(db_path: str = "invoices.db") -> InvoiceDatabase:
    return InvoiceDatabase(db_path)

