"""
Vendor Registry System - Permanent Solution for Invoice Pattern Recognition

This module provides a scalable, maintainable way to:
1. Detect vendor from invoice content
2. Apply vendor-specific validation rules
3. Learn patterns from historical data
4. Add new vendors without code changes

Author: ML Engineer
Date: November 2024
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class VendorPattern:
    """Vendor-specific extraction patterns"""
    vendor_id: str
    vendor_name: str
    
    # Detection patterns (how to identify this vendor)
    name_patterns: List[str]  # Regex patterns in vendor name
    invoice_prefix_patterns: List[str]  # Invoice number patterns (e.g., ["378.*", "379.*"])
    
    # Extraction hints (where to find fields)
    invoice_number_location: str  # "top_right", "top_left", "header", etc.
    invoice_number_label: str  # Label before invoice number (e.g., "INVOICE", "Invoice #")
    
    # Validation rules
    invoice_number_regex: str  # Regex for valid invoice number
    invoice_number_min_length: int
    invoice_number_max_length: int
    
    # Field extraction hints
    column_mappings: Dict[str, str]  # Maps field to column name
    
    # Learning data
    confidence: float = 1.0  # How confident we are in these patterns
    sample_count: int = 0  # How many invoices we've seen
    last_updated: str = ""
    
    # Additional metadata
    notes: str = ""


class VendorRegistry:
    """
    Central registry for vendor patterns with learning capabilities
    
    Features:
    - Vendor detection from invoice content
    - Pattern-based validation
    - Learning from historical data
    - Easy vendor addition via config
    """
    
    def __init__(self, registry_file: str = "vendor_registry.json"):
        """
        Initialize vendor registry
        
        Args:
            registry_file: Path to JSON file containing vendor patterns
        """
        self.registry_file = Path(registry_file)
        self.vendors: Dict[str, VendorPattern] = {}
        self.load_registry()
    
    def load_registry(self):
        """Load vendor patterns from file or initialize with defaults"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    self.vendors = {
                        v_id: VendorPattern(**v_data)
                        for v_id, v_data in data.items()
                    }
                print(f"✓ Loaded {len(self.vendors)} vendors from registry")
            except Exception as e:
                print(f"Warning: Could not load vendor registry: {e}")
                self._initialize_default_vendors()
        else:
            print("No vendor registry found, creating with defaults")
            self._initialize_default_vendors()
            self.save_registry()
    
    def _initialize_default_vendors(self):
        """Initialize with known vendors (Pacific Food, Frank's)"""
        
        # Pacific Food Importers
        self.vendors["pacific_food"] = VendorPattern(
            vendor_id="pacific_food",
            vendor_name="Pacific Food Importers",
            name_patterns=[
                r"pacific\s+food\s+importers?",
                r"pacific\s+food"
            ],
            invoice_prefix_patterns=["^37"],  # ✅ Accept any 37X
            invoice_number_location="top_right",
            invoice_number_label="INVOICE",
            invoice_number_regex=r"^37\d{4}$",  # ✅ 37 + 4 digits = 6 total
            invoice_number_min_length=6,
            invoice_number_max_length=6,
            column_mappings={
                "quantity": "SHIPPED",
                "unit_price": "Price",
                "line_total": "Amount",
                "description": "DESCRIPTION"
            },
            confidence=1.0,
            sample_count=4,
            last_updated=datetime.now().isoformat(),
            notes="Invoices always start with 37 (370-379). Be careful not to confuse with ORDER NO."
        )
        
        # Frank's Quality Produce
        self.vendors["franks"] = VendorPattern(
            vendor_id="franks",
            vendor_name="Frank's Quality Produce",
            name_patterns=[
                r"frank'?s?\s+quality\s+produce",
                r"frank'?s?\s+produce"
            ],
            invoice_prefix_patterns=["^200"],
            invoice_number_location="top_center",
            invoice_number_label="Invoice #",
            invoice_number_regex=r"^200\d{5}$",
            invoice_number_min_length=8,
            invoice_number_max_length=8,
            column_mappings={
                "quantity": "Quantity",
                "unit_price": "Price Each",
                "line_total": "Amount",
                "description": "Description"
            },
            confidence=1.0,
            sample_count=2,
            last_updated=datetime.now().isoformat(),
            notes="Invoice numbers always start with 200 and are 8 digits total."
        )
    
    def save_registry(self):
        """Save vendor patterns to file"""
        try:
            data = {
                v_id: asdict(vendor)
                for v_id, vendor in self.vendors.items()
            }
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✓ Saved vendor registry to {self.registry_file}")
        except Exception as e:
            print(f"Warning: Could not save vendor registry: {e}")
    
    def detect_vendor(
        self, 
        vendor_name: str = "",
        invoice_number: str = "",
        ocr_text: str = "",
        debug: bool = False
    ) -> Optional[VendorPattern]:
        """
        Detect vendor from invoice content
        
        Args:
            vendor_name: Extracted vendor name
            invoice_number: Extracted invoice number
            ocr_text: Full OCR text (optional, for better detection)
            debug: Print debug information
            
        Returns:
            VendorPattern if detected, None otherwise
        """
        scores = {}
        
        for v_id, vendor in self.vendors.items():
            score = 0.0
            reasons = []
            
            # Check vendor name match
            if vendor_name:
                vendor_name_lower = vendor_name.lower()
                for pattern in vendor.name_patterns:
                    if re.search(pattern, vendor_name_lower, re.IGNORECASE):
                        score += 0.5
                        reasons.append(f"name_match:{pattern}")
                        break
            
            # Check invoice number prefix
            if invoice_number:
                inv_str = str(invoice_number)
                for pattern in vendor.invoice_prefix_patterns:
                    if re.match(pattern, inv_str):
                        score += 0.3
                        reasons.append(f"invoice_prefix:{pattern}")
                        break
            
            # Check OCR text for vendor mentions
            if ocr_text:
                ocr_lower = ocr_text.lower()
                for pattern in vendor.name_patterns:
                    if re.search(pattern, ocr_lower, re.IGNORECASE):
                        score += 0.2
                        reasons.append("ocr_match")
                        break
            
            if score > 0:
                scores[v_id] = (score, reasons)
                if debug:
                    print(f"  [DEBUG] Vendor '{v_id}': score={score:.2f}, reasons={reasons}")
        
        # Return vendor with highest score
        if scores:
            best_vendor_id = max(scores.keys(), key=lambda k: scores[k][0])
            best_score, reasons = scores[best_vendor_id]
            
            if best_score >= 0.5:  # Minimum confidence threshold
                if debug:
                    print(f"  [DEBUG] Detected vendor: {best_vendor_id} (score={best_score:.2f})")
                return self.vendors[best_vendor_id]
        
        if debug:
            print(f"  [DEBUG] No vendor detected (scores: {scores})")
        return None
    
    def validate_invoice_number(
        self, 
        invoice_number: str, 
        vendor: VendorPattern,
        debug: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate invoice number against vendor pattern
        
        Args:
            invoice_number: Invoice number to validate
            vendor: Vendor pattern
            debug: Print debug info
            
        Returns:
            (is_valid, error_message)
        """
        if not invoice_number:
            return False, "Invoice number is empty"
        
        inv_str = str(invoice_number).strip()
        
        # Check length
        if len(inv_str) < vendor.invoice_number_min_length:
            return False, f"Too short (min: {vendor.invoice_number_min_length})"
        
        if len(inv_str) > vendor.invoice_number_max_length:
            return False, f"Too long (max: {vendor.invoice_number_max_length})"
        
        # Check regex pattern
        if not re.match(vendor.invoice_number_regex, inv_str):
            return False, f"Doesn't match pattern: {vendor.invoice_number_regex}"
        
        if debug:
            print(f"  [DEBUG] Invoice number '{inv_str}' is valid for {vendor.vendor_name}")
        
        return True, None
    
    def get_extraction_instructions(self, vendor: VendorPattern) -> str:
        """
        Generate extraction instructions for a specific vendor
        
        Args:
            vendor: Vendor pattern
            
        Returns:
            Extraction instructions string
        """
        instructions = f"""
VENDOR: {vendor.vendor_name.upper()}
- Vendor Name: MUST be exactly "{vendor.vendor_name}"
"""
        
        # Invoice number instructions
        inv_prefixes = ", ".join(vendor.invoice_prefix_patterns)
        instructions += f"""- Invoice Number: Located at {vendor.invoice_number_location}, labeled "{vendor.invoice_number_label}"
  * CRITICAL: Invoice number MUST match pattern: {vendor.invoice_number_regex}
  * Valid prefixes: {inv_prefixes}
  * Length: {vendor.invoice_number_min_length}-{vendor.invoice_number_max_length} digits
  * DO NOT confuse with other numbers (PO, Order No, etc.)
"""
        
        # Column mappings
        if vendor.column_mappings:
            instructions += "\n- Column Mappings:\n"
            for field, column in vendor.column_mappings.items():
                instructions += f"  * {field}: '{column}' column\n"
        
        # Notes
        if vendor.notes:
            instructions += f"\nIMPORTANT NOTES:\n{vendor.notes}\n"
        
        return instructions
    
    def add_vendor(
        self,
        vendor_id: str,
        vendor_name: str,
        name_patterns: List[str],
        invoice_prefix_patterns: List[str],
        invoice_number_regex: str,
        invoice_number_length: Tuple[int, int],
        **kwargs
    ):
        """
        Add a new vendor to the registry
        
        Args:
            vendor_id: Unique identifier (e.g., "acme_corp")
            vendor_name: Display name (e.g., "ACME Corporation")
            name_patterns: Regex patterns to detect vendor name
            invoice_prefix_patterns: Invoice number prefix patterns
            invoice_number_regex: Full regex for invoice number
            invoice_number_length: (min_length, max_length) tuple
            **kwargs: Additional VendorPattern fields
        """
        min_len, max_len = invoice_number_length
        
        self.vendors[vendor_id] = VendorPattern(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            name_patterns=name_patterns,
            invoice_prefix_patterns=invoice_prefix_patterns,
            invoice_number_regex=invoice_number_regex,
            invoice_number_min_length=min_len,
            invoice_number_max_length=max_len,
            invoice_number_location=kwargs.get("invoice_number_location", "top_right"),
            invoice_number_label=kwargs.get("invoice_number_label", "Invoice"),
            column_mappings=kwargs.get("column_mappings", {}),
            confidence=kwargs.get("confidence", 0.8),
            sample_count=kwargs.get("sample_count", 0),
            last_updated=datetime.now().isoformat(),
            notes=kwargs.get("notes", "")
        )
        
        print(f"✓ Added vendor: {vendor_name} ({vendor_id})")
        self.save_registry()
    
    def learn_from_invoice(
        self,
        vendor_id: str,
        extracted_data: Dict[str, Any],
        was_successful: bool
    ):
        """
        Update vendor patterns based on extraction results (learning)
        
        Args:
            vendor_id: Vendor identifier
            extracted_data: Extraction results
            was_successful: Whether extraction was successful
        """
        if vendor_id not in self.vendors:
            return
        
        vendor = self.vendors[vendor_id]
        vendor.sample_count += 1
        
        # Update confidence based on success
        if was_successful:
            vendor.confidence = min(1.0, vendor.confidence + 0.01)
        else:
            vendor.confidence = max(0.5, vendor.confidence - 0.05)
        
        vendor.last_updated = datetime.now().isoformat()
        
        # Save updated registry
        self.save_registry()
    
    def get_all_vendors(self) -> List[Dict[str, Any]]:
        """Get all registered vendors"""
        return [asdict(vendor) for vendor in self.vendors.values()]
    
    def suggest_vendor_pattern(
        self,
        sample_invoices: List[Dict[str, Any]],
        vendor_name: str
    ) -> Dict[str, Any]:
        """
        Suggest vendor pattern based on sample invoices (ML approach)
        
        Args:
            sample_invoices: List of successfully extracted invoices
            vendor_name: Vendor name
            
        Returns:
            Suggested VendorPattern as dict
        """
        # Analyze invoice numbers to find pattern
        invoice_numbers = [
            str(inv.get('invoice_number', ''))
            for inv in sample_invoices
            if inv.get('invoice_number')
        ]
        
        if not invoice_numbers:
            return {}
        
        # Find common prefix
        prefix_counts = {}
        for inv_num in invoice_numbers:
            for i in range(1, min(5, len(inv_num))):
                prefix = inv_num[:i]
                prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
        
        # Find most common prefix
        common_prefix = max(prefix_counts.keys(), key=lambda p: prefix_counts[p])
        prefix_pattern = f"^{common_prefix}"
        
        # Determine length range
        lengths = [len(inv) for inv in invoice_numbers]
        min_len = min(lengths)
        max_len = max(lengths)
        
        # Create regex pattern
        if min_len == max_len:
            regex_pattern = f"^{common_prefix}\\d{{{max_len - len(common_prefix)}}}$"
        else:
            regex_pattern = f"^{common_prefix}\\d{{{min_len - len(common_prefix)},{max_len - len(common_prefix)}}}$"
        
        suggestion = {
            "vendor_name": vendor_name,
            "invoice_prefix_patterns": [prefix_pattern],
            "invoice_number_regex": regex_pattern,
            "invoice_number_min_length": min_len,
            "invoice_number_max_length": max_len,
            "sample_count": len(sample_invoices),
            "confidence": 0.7,  # Initial confidence
            "notes": f"Auto-generated from {len(sample_invoices)} sample invoices"
        }
        
        print(f"\n📊 Suggested pattern for '{vendor_name}':")
        print(f"  Prefix: {common_prefix}")
        print(f"  Regex: {regex_pattern}")
        print(f"  Length: {min_len}-{max_len}")
        
        return suggestion


# Global registry instance
_registry = None

def get_vendor_registry(registry_file: str = "vendor_registry.json") -> VendorRegistry:
    """Get or create global vendor registry instance"""
    global _registry
    if _registry is None:
        _registry = VendorRegistry(registry_file)
    return _registry


# Example usage and testing
if __name__ == "__main__":
    print("="*60)
    print("Vendor Registry System - Demo")
    print("="*60)
    
    # Initialize registry
    registry = VendorRegistry("test_vendor_registry.json")
    
    # Test vendor detection
    print("\n1. Testing Vendor Detection:")
    print("-" * 40)
    
    # Test Pacific Food
    vendor = registry.detect_vendor(
        vendor_name="Pacific Food Importers",
        invoice_number="378093",
        debug=True
    )
    if vendor:
        print(f"✓ Detected: {vendor.vendor_name}")
        
        # Validate invoice number
        is_valid, error = registry.validate_invoice_number("378093", vendor, debug=True)
        print(f"  Invoice '378093': {'✓ Valid' if is_valid else f'✗ Invalid - {error}'}")
        
        # Test invalid number
        is_valid, error = registry.validate_invoice_number("444509", vendor, debug=True)
        print(f"  Invoice '444509': {'✓ Valid' if is_valid else f'✗ Invalid - {error}'}")
    
    # Test Frank's
    print()
    vendor = registry.detect_vendor(
        vendor_name="Frank's Quality Produce",
        invoice_number="20065629",
        debug=True
    )
    if vendor:
        print(f"✓ Detected: {vendor.vendor_name}")
        
        is_valid, error = registry.validate_invoice_number("20065629", vendor, debug=True)
        print(f"  Invoice '20065629': {'✓ Valid' if is_valid else f'✗ Invalid - {error}'}")
    
    # Test adding new vendor
    print("\n2. Adding New Vendor:")
    print("-" * 40)
    registry.add_vendor(
        vendor_id="sysco",
        vendor_name="Sysco Corporation",
        name_patterns=[r"sysco\s+corp", r"sysco"],
        invoice_prefix_patterns=["^INV-", "^SC"],
        invoice_number_regex=r"^(INV-|SC)\d{6}$",
        invoice_number_length=(9, 9),
        invoice_number_location="top_right",
        invoice_number_label="Invoice No",
        column_mappings={
            "quantity": "Qty",
            "unit_price": "Unit Price",
            "line_total": "Total"
        },
        notes="Sysco invoices start with INV- or SC prefix"
    )
    
    # Test detection for new vendor
    vendor = registry.detect_vendor(
        vendor_name="Sysco Corporation",
        invoice_number="INV-123456",
        debug=True
    )
    if vendor:
        print(f"✓ Detected: {vendor.vendor_name}")
        is_valid, error = registry.validate_invoice_number("INV-123456", vendor, debug=True)
        print(f"  Invoice 'INV-123456': {'✓ Valid' if is_valid else f'✗ Invalid - {error}'}")
    
    # Test pattern suggestion (ML approach)
    print("\n3. Suggesting Pattern from Samples:")
    print("-" * 40)
    sample_invoices = [
        {"invoice_number": "AB12345"},
        {"invoice_number": "AB12346"},
        {"invoice_number": "AB12347"},
        {"invoice_number": "AB12348"},
    ]
    suggestion = registry.suggest_vendor_pattern(
        sample_invoices,
        "ABC Wholesale"
    )
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
