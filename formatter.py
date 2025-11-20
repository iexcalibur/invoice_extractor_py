"""
Formatter module for converting invoice data to table formats
"""

import csv
import json
from typing import Dict, List, Any
from pathlib import Path


class InvoiceFormatter:
    """Format invoice data into table/list formats"""
    
    @staticmethod
    def _get_vendor_format(page_vendor: str) -> Dict[str, str]:
        """
        Get vendor-specific column headers
        
        Args:
            page_vendor: Vendor name
            
        Returns:
            Dictionary with column header names
        """
        vendor_lower = page_vendor.lower()
        
        if "pacific food" in vendor_lower or "pacific food importers" in vendor_lower:
            return {
                'quantity_col': 'Ordered',
                'price_col': 'Price',
                'amount_col': 'Amount'
            }
        else:
            # Default format (Frank's Quality Produce and others)
            return {
                'quantity_col': 'Quantity',
                'price_col': 'Each Price',
                'amount_col': 'Amount'
            }
    
    @staticmethod
    def format_as_table(invoice_data: Dict[str, Any], vendor_name: str = None) -> str:
        """
        Format invoice data as a readable table
        
        Args:
            invoice_data: Extracted invoice data dictionary
            vendor_name: Optional vendor name filter
            
        Returns:
            Formatted table string
        """
        if invoice_data.get('status') != 'success':
            return f"Error: {invoice_data.get('error', 'Unknown error')}"
        
        pages = invoice_data.get('pages', [])
        if not pages:
            return "No invoice data found"
        
        output_lines = []
        
        for page in pages:
            if 'error' in page:
                continue
                
            # Check vendor filter
            page_vendor = page.get('vendor_name', '')
            if vendor_name and vendor_name.lower() not in page_vendor.lower():
                continue
            
            # Get vendor-specific format
            col_format = InvoiceFormatter._get_vendor_format(page_vendor)
            
            # Header
            output_lines.append("=" * 80)
            output_lines.append(f"Vendor: {page_vendor}")
            output_lines.append(f"Invoice #: {page.get('invoice_number', 'N/A')}")
            output_lines.append(f"Date: {page.get('date', 'N/A')}")
            output_lines.append(f"Total: ${page.get('total_amount', 0):.2f}")
            output_lines.append("=" * 80)
            output_lines.append("")
            
            # Table header with vendor-specific columns
            output_lines.append(f"{col_format['quantity_col']:<12} {'Description':<40} {col_format['price_col']:<15} {col_format['amount_col']:<15}")
            output_lines.append("-" * 80)
            
            # Line items
            line_items = page.get('line_items', [])
            for item in line_items:
                quantity = item.get('quantity', 0)
                description = item.get('description', '')
                unit_price = item.get('unit_price', 0.0)
                line_total = item.get('line_total', 0.0)
                
                # Truncate description if too long
                if len(description) > 38:
                    description = description[:35] + "..."
                
                output_lines.append(
                    f"{str(quantity):<12} {description:<40} ${unit_price:<14.2f} ${line_total:<14.2f}"
                )
            
            output_lines.append("-" * 80)
            output_lines.append(f"{'TOTAL':<52} ${page.get('total_amount', 0):<14.2f}")
            output_lines.append("")
        
        return "\n".join(output_lines)
    
    @staticmethod
    def format_as_csv(invoice_data: Dict[str, Any], output_path: str, vendor_name: str = None):
        """
        Format invoice data as CSV file
        
        Args:
            invoice_data: Extracted invoice data dictionary
            output_path: Path to save CSV file
            vendor_name: Optional vendor name filter
        """
        if invoice_data.get('status') != 'success':
            raise ValueError(f"Invalid invoice data: {invoice_data.get('error', 'Unknown error')}")
        
        pages = invoice_data.get('pages', [])
        if not pages:
            raise ValueError("No invoice data found")
        
        rows = []
        col_format = None
        
        for page in pages:
            if 'error' in page:
                continue
            
            # Check vendor filter
            page_vendor = page.get('vendor_name', '')
            if vendor_name and vendor_name.lower() not in page_vendor.lower():
                continue
            
            # Get vendor-specific format (use first matching vendor)
            if col_format is None:
                col_format = InvoiceFormatter._get_vendor_format(page_vendor)
            
            vendor = page_vendor
            invoice_num = page.get('invoice_number', '')
            date = page.get('date', '')
            total = page.get('total_amount', 0)
            
            line_items = page.get('line_items', [])
            for item in line_items:
                row_data = {
                    'Vendor': vendor,
                    'Invoice Number': invoice_num,
                    'Date': date,
                    'Description': item.get('description', ''),
                    'Amount': item.get('line_total', 0.0),
                    'Total': total
                }
                
                # Add vendor-specific column names
                row_data[col_format['quantity_col']] = item.get('quantity', 0)
                row_data[col_format['price_col']] = item.get('unit_price', 0.0)
                
                rows.append(row_data)
        
        if not rows:
            raise ValueError("No matching invoice data found")
        
        # Determine fieldnames based on vendor format
        fieldnames = ['Vendor', 'Invoice Number', 'Date', col_format['quantity_col'], 
                     'Description', col_format['price_col'], 'Amount', 'Total']
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    @staticmethod
    def format_as_list(invoice_data: Dict[str, Any], vendor_name: str = None) -> List[Dict[str, Any]]:
        """
        Format invoice data as a list of dictionaries (for programmatic use)
        
        Args:
            invoice_data: Extracted invoice data dictionary
            vendor_name: Optional vendor name filter
            
        Returns:
            List of line items with vendor info
        """
        if invoice_data.get('status') != 'success':
            return []
        
        pages = invoice_data.get('pages', [])
        result = []
        
        for page in pages:
            if 'error' in page:
                continue
            
            # Check vendor filter
            page_vendor = page.get('vendor_name', '')
            if vendor_name and vendor_name.lower() not in page_vendor.lower():
                continue
            
            vendor = page_vendor
            invoice_num = page.get('invoice_number', '')
            date = page.get('date', '')
            
            # Get vendor-specific format
            col_format = InvoiceFormatter._get_vendor_format(page_vendor)
            
            line_items = page.get('line_items', [])
            for item in line_items:
                item_dict = {
                    'name': vendor,
                    'invoice_number': invoice_num,
                    'date': date,
                    'description': item.get('description', ''),
                    'amount': item.get('line_total', 0.0)
                }
                
                # Add vendor-specific field names
                if col_format['quantity_col'] == 'Ordered':
                    item_dict['ordered'] = item.get('quantity', 0)
                    item_dict['price'] = item.get('unit_price', 0.0)
                else:
                    item_dict['quantity'] = item.get('quantity', 0)
                    item_dict['each_price'] = item.get('unit_price', 0.0)
                
                result.append(item_dict)
        
        return result

