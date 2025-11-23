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
        """
        Create database tables following dimensional model:
        - invoices: DIMENSION TABLE (descriptive attributes)
        - line_items: FACT TABLE (measures/metrics with foreign key to dimension)
        """
        # Close existing connection if any
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        
        # Create new connection with timeout to handle locks
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # DIMENSION TABLE: Invoices
        # Contains descriptive attributes about invoices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                invoice_date DATE NOT NULL,
                total_amount REAL NOT NULL,
                -- Metadata fields (optional)
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
        
        # FACT TABLE: Line Items
        # Contains measures (quantity, unit_price, total) with foreign key to dimension
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
        
        # Indexes for dimension table (invoices)
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
        
        # Indexes for fact table (line_items) - critical for joins
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_line_items_invoice 
            ON line_items(invoice_id)
        """)
        
        # Composite index for common fact table queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_line_items_invoice_order 
            ON line_items(invoice_id, line_order)
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
        Save invoice to database (with duplicate check)
        
        Args:
            invoice_data: Extracted invoice data
            file_path: Source PDF filename (optional)
            
        Returns:
            Invoice ID if saved, None if duplicate or error
        """
        if not self.conn:
            self._create_tables()
        
        # Check for duplicate first
        invoice_number = invoice_data.get('invoice_number', '')
        vendor_name = invoice_data.get('vendor_name', '')
        
        if not invoice_number:
            print(f"  ⚠ Skipping invoice: no invoice number")
            return None
        
        normalized_invoice_number = self.normalize_invoice_number(invoice_number)
        normalized_vendor = self.normalize_vendor_name(vendor_name)
        
        # Check if invoice already exists
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM invoices WHERE invoice_number = ?",
            (normalized_invoice_number,)
        )
        existing = cursor.fetchone()
        
        if existing:
            existing_id = existing['id']
            # Invoice already exists, skip
            print(f"  ℹ Invoice {invoice_number} already exists")
            return None
        
        # Proceed with insert...
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
            
            # CRITICAL: Validate and fix vendor names and invoice numbers before saving
            # Use vendor registry if available, otherwise skip hardcoded checks
            vendor_name = page.get('vendor_name', '')
            invoice_number = str(page.get('invoice_number', ''))
            
            # Try to use vendor registry for vendor detection and validation
            try:
                from .vendor_registry import get_vendor_registry
                vendor_registry = get_vendor_registry()
                
                if vendor_registry and invoice_number:
                    # Detect vendor from invoice number and vendor name
                    vendor = vendor_registry.detect_vendor(
                        vendor_name=vendor_name,
                        invoice_number=invoice_number,
                        debug=False
                    )
                    
                    if vendor:
                        # Fix vendor name to match registry standard
                        if vendor_name.lower() != vendor.vendor_name.lower():
                            print(f"  ⚠ Fixing vendor name: '{vendor_name}' -> '{vendor.vendor_name}'")
                            page['vendor_name'] = vendor.vendor_name
                        
                        # Validate invoice number using vendor pattern
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
                # Vendor registry not available - skip validation (allow all invoices)
                pass
            
            is_valid, validation_errors = self.validate_invoice(page)
            if not is_valid:
                errors.extend(validation_errors)
                continue
            
            # Check for common issues before attempting save
            invoice_number = page.get('invoice_number', '')
            date_str = page.get('date', '')
            page_num = page.get('page_number', 1)
            
            if not invoice_number:
                errors.append(f"Page {page_num}: Cannot save - missing invoice number")
                continue
            
            # Check if date can be normalized
            normalized_date = self.normalize_date(date_str)
            if not normalized_date:
                errors.append(f"Page {page_num}: Cannot save - invalid date format '{date_str}' (Invoice: {invoice_number})")
                continue
            
            # Check if invoice already exists
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
            
            # Attempt to save
            invoice_id = self.save_invoice(page, file_path)
            if invoice_id:
                saved_invoices.append({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                    'page_number': page_num
                })
            else:
                # If save_invoice returned None, provide detailed error
                errors.append(f"Page {page_num}: Failed to save invoice {invoice_number} - database error occurred")
        
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
    
    def update_invoice_number(self, invoice_id: int, new_invoice_number: str) -> bool:
        """
        Update invoice number for a specific invoice
        
        Args:
            invoice_id: Invoice ID
            new_invoice_number: New invoice number
            
        Returns:
            True if successful, False otherwise
        """
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
        """
        Get all invoices for a specific vendor
        
        Args:
            vendor_name: Vendor name (partial match)
            
        Returns:
            List of invoice dictionaries
        """
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
        """
        Get fact table data (line_items) with dimension attributes joined
        
        This follows the dimensional model pattern where fact table is joined
        with dimension table to get complete information.
        
        Args:
            invoice_ids: Optional list of invoice IDs to filter by
            
        Returns:
            List of dictionaries with fact and dimension data combined
            Format: {line_item_id, invoice_id, description, quantity, unit_price, 
                    line_total, invoice_number, vendor_name, invoice_date, total_amount}
        """
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
        """
        Get dimension table data (invoices) with optional filters
        
        Args:
            vendor_name: Optional vendor name filter
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            List of invoice dictionaries (dimension records)
            Format: {id, invoice_number, vendor_name, invoice_date, total_amount, ...}
        """
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

