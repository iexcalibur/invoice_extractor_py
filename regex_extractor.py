"""
Regex-based invoice extraction for known vendors
Optimized for Frank's Quality Produce and Pacific Food Importers
IMPROVED VERSION - Based on actual invoice analysis
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime


class RegexInvoiceExtractor:
    """Regex-based invoice extraction for known vendors"""
    
    def __init__(self):
        """Initialize regex patterns for both vendors"""
        self.patterns = {
            "franks": {
                "vendor": r"Frank['']?s?\s+Quality\s+Produce",
                "invoice_number": r"Invoice\s*#?\s*:?\s*(\d{7,8})",  # Frank's uses 8-digit invoice numbers (20065629)
                "account_number": r"Account\s*#?\s*:?\s*(\d{4})",
                "date": r"Date\s*:?\s*(\d{1,2})/(\d{1,2})/(\d{4})",
                "due_date": r"Due\s+Date\s*:?\s*(\d{1,2})/(\d{1,2})/(\d{4})",
                "total": r"Total\s*:?\s*\$?\s*([\d,]+\.\d{2})",
                "terms": r"Terms\s*:?\s*([\d\s\w-]+)",
                "rep": r"Rep\s*:?\s*(\w+)",
                "table_header": r"Quantity\s+Description\s+Price\s+Each\s+Amount",
                "ship_to": r"Ship\s+To\s*:?\s*\n\s*(.+?)(?:\n.*?)?(?=\n\s*\d{4}|Customer\s+Phone|$)",
                "customer_phone": r"Customer\s+Phone\s*:?\s*([\d-]+)",
                "address": r"3800\s+1st\s+Ave\s+S",  # Specific to Frank's
                "email": r"warehouse@franksproduce\.net",
                # Line items: Quantity | Description | Price Each | Amount
                # Frank's format has cleaner spacing
                "line_item": r"^\s*(\d+)\s+([A-Z][^\d\n]{3,}?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s*$",
                # Alternative patterns for line items with more flexibility
                "line_item_alt": [
                    r"^\s*(\d+)\s+([A-Z][^\d\n]{3,}?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s*$",  # Strict
                    r"(\d+)\s+([A-Z][^#\d\n]+?(?:#)?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})",  # Allow # in description
                    r"(\d+)\t+([^\t\n]+?)\t+(\d+\.\d{2})\t+(\d+\.\d{2})",  # Tab-separated
                ],
                # Special line items to skip
                "skip_items": r"(?i)(FUEL\s+SURCHARGE|Sales\s+Tax|Subtotal|Discount)",
            },
            "pacific": {
                "vendor": r"Pacific\s+Food\s+Importers?",
                "invoice_number": r"(?:INVOICE|Invoice)\s*#?\s*:?\s*(\d{6})",  # Pacific uses 6-digit (379183)
                "order_number": r"ORDER\s+NO\s*:?\s*(\d+)",
                "customer_id": r"CUST\s+ID\s*:?\s*(\d+)",
                "date": r"(?:INVOICE|Invoice)\s+(?:DATE|Date)\s*:?\s*(\d{2})/(\d{2})/(\d{4})",
                "order_date": r"ORDER\s+DATE\s*:?\s*(\d{2})/(\d{2})/(\d{4})",
                "total": r"(?:INVOICE|Invoice)\s+(?:TOTAL|Total)\s*:?\s*\$?\s*([\d,]+\.\d{2})",
                "subtotal": r"Sub\s+Total\s*:?\s*\$?\s*([\d,]+\.\d{2})",
                "terms": r"TERMS\s*:?\s*([^\n]+)",
                "sales_rep": r"SALES\s+REP\s*:?\s*(\d+)",
                "ship_to": r"Ship\s+To:\s*(.+?)(?:Ship\s+Via:|PH:|$)",
                "sold_to": r"Sold\s+To:\s*(.+?)(?:Route/Stop:|Ship\s+To:|$)",
                "table_header": r"PRODUCT\s*ID\s+ORDERED\s+SHIPPED\s+DESCRIPTION",
                "customer_copy": r"CUSTOMER\s+COPY",
                "address": r"KENT,?\s+WA\s+98032",  # Specific to Pacific
                # Line items for Pacific Food Importers
                # Format: ProductID | Ordered | Shipped | CS/EA | Description | ST | Gross WT | Price | per | Amount
                # Example: 102950    8.000    8.000 CS FLOUR POWER 50 LB    400.000 LB    24.063 CS    192.50
                # Key: Use SHIPPED (column 3) as quantity, not ORDERED
                "line_item": r"(\d{5,6})\s+([\d.]+)\s+([\d.]+)\s+(?:CS|EA)\s+([A-Z][^\n]+?)\s+([\d.]+)\s+LB\s+([\d.]+)\s+(?:CS|EA)\s+([\d.]+)",
                # Alternative patterns with more flexibility
                "line_item_alt": [
                    # Pattern 1: Standard format with CS/EA markers
                    r"(\d{5,6})\s+([\d.]+)\s+([\d.]+)\s+(?:CS|EA)\s+([A-Z][^\n]+?)\s+([\d.]+)\s+(?:CS|EA)\s+([\d.]+)",
                    # Pattern 2: Without explicit LB marker
                    r"(\d{5,6})\s+([\d.]+)\s+([\d.]+)\s+(?:CS|EA)\s+([^\d\n]+?)\s+([\d.]+)\s+(?:CS|EA)\s+([\d.]+)",
                    # Pattern 3: More relaxed spacing
                    r"(\d{5,6})\s+[\d.]+\s+([\d.]+)\s+(?:CS|EA)?\s*([A-Z][^\n]+?)\s+([\d.]+)\s+(?:CS|EA)\s+([\d.]+)",
                ],
                # Products that might have an X marker
                "marked_item": r"(\d{5,6})\s+[Xx]\s+([\d.]+)\s+([\d.]+)",
            }
        }
    
    def detect_vendor(self, text: str, debug: bool = False) -> Optional[str]:
        """
        Detect vendor from text (with improved pattern matching)
        
        Args:
            text: OCR extracted text
            debug: If True, print debugging information
            
        Returns:
            "franks", "pacific", or None
        """
        text_lower = text.lower()
        
        # Primary detection: Company name patterns
        franks_patterns = [
            r"frank['']?s?\s+quality\s+produce",
            r"franks\s+quality\s+produce",
            r"frank\s+quality\s+produce",
        ]
        
        pacific_patterns = [
            r"pacific\s+food\s+importers?",
            r"pacific\s+food\s+import",
        ]
        
        # Try Frank's patterns
        for pattern in franks_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if debug:
                    print(f"  [DEBUG] Vendor: Frank's Quality Produce (pattern: {pattern})")
                return "franks"
        
        # Try Pacific patterns
        for pattern in pacific_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if debug:
                    print(f"  [DEBUG] Vendor: Pacific Food Importers (pattern: {pattern})")
                return "pacific"
        
        # Secondary detection: Unique identifiers
        # Frank's specific markers
        if re.search(r"warehouse@franksproduce\.net", text_lower):
            if debug:
                print(f"  [DEBUG] Vendor: Frank's Quality Produce (email match)")
            return "franks"
        
        if re.search(r"3800\s+1st\s+ave\s+s", text_lower):
            if debug:
                print(f"  [DEBUG] Vendor: Frank's Quality Produce (address match)")
            return "franks"
        
        # Pacific specific markers
        if re.search(r"customer\s+copy", text_lower) and re.search(r"kent,?\s+wa", text_lower):
            if debug:
                print(f"  [DEBUG] Vendor: Pacific Food Importers (signature match)")
            return "pacific"
        
        if re.search(r"18620\s+80th\s+court", text_lower):
            if debug:
                print(f"  [DEBUG] Vendor: Pacific Food Importers (address match)")
            return "pacific"
        
        if debug:
            print(f"  [DEBUG] Vendor not detected. First 300 chars:")
            print(f"  {text[:300]}")
            # Check for partial matches
            if "frank" in text_lower or "quality" in text_lower:
                print(f"  [DEBUG] Found 'frank' or 'quality' but no complete pattern match")
            if "pacific" in text_lower or "food" in text_lower:
                print(f"  [DEBUG] Found 'pacific' or 'food' but no complete pattern match")
        
        return None
    
    def extract(self, ocr_text: str, debug: bool = False) -> Optional[Dict[str, Any]]:
        """
        Extract invoice data using regex
        
        Args:
            ocr_text: OCR extracted text
            debug: If True, print debugging information
            
        Returns:
            Extracted data dictionary with confidence score, or None if failed
        """
        vendor = self.detect_vendor(ocr_text, debug=debug)
        if not vendor:
            if debug:
                print(f"  [DEBUG] Vendor detection failed - no vendor pattern matched")
            return None
        
        if debug:
            print(f"  [DEBUG] Vendor detected: {vendor}")
        
        patterns = self.patterns[vendor]
        result = {
            "vendor_name": "Frank's Quality Produce" if vendor == "franks" else "Pacific Food Importers",
            "invoice_number": "",
            "date": "",
            "total_amount": 0.0,
            "line_items": []
        }
        
        # Extract invoice number
        inv_match = re.search(patterns["invoice_number"], ocr_text, re.IGNORECASE)
        if not inv_match and vendor == "franks":
            # Try broader patterns for Frank's
            alt_patterns = [
                r"Invoice\s*#\s*(\d{7,8})",
                r"Invoice\s*Number\s*:?\s*(\d{7,8})",
                r"INV\s*#?\s*:?\s*(\d{7,8})",
            ]
            for alt_pattern in alt_patterns:
                inv_match = re.search(alt_pattern, ocr_text, re.IGNORECASE)
                if inv_match:
                    break
        elif not inv_match and vendor == "pacific":
            # Try broader patterns for Pacific
            alt_patterns = [
                r"INVOICE\s*#?\s*(\d{6})",
                r"Invoice\s*#?\s*(\d{6})",
            ]
            for alt_pattern in alt_patterns:
                inv_match = re.search(alt_pattern, ocr_text, re.IGNORECASE)
                if inv_match:
                    break
        
        if inv_match:
            result["invoice_number"] = inv_match.group(1)
            if debug:
                print(f"  [DEBUG] Invoice number: {result['invoice_number']}")
        elif debug:
            print(f"  [DEBUG] Invoice number not found")
        
        # Extract date
        date_match = re.search(patterns["date"], ocr_text, re.IGNORECASE)
        if not date_match:
            # Try alternative date patterns
            alt_date_patterns = [
                r"Date\s*:?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
                r"(?:Invoice|INVOICE)\s+(?:Date|DATE)\s*:?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
            ]
            for alt_pattern in alt_date_patterns:
                date_match = re.search(alt_pattern, ocr_text, re.IGNORECASE)
                if date_match:
                    break
        
        if date_match:
            month, day, year = date_match.groups()
            result["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            if debug:
                print(f"  [DEBUG] Date: {result['date']}")
        elif debug:
            print(f"  [DEBUG] Date not found")
        
        # Extract total
        total_match = re.search(patterns["total"], ocr_text, re.IGNORECASE)
        if not total_match:
            # Try alternative total patterns
            alt_total_patterns = [
                r"Total\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})",
                r"(?:Invoice|INVOICE)\s+(?:Total|TOTAL)\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})",
                r"Amount\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})",
            ]
            for alt_pattern in alt_total_patterns:
                total_match = re.search(alt_pattern, ocr_text, re.IGNORECASE)
                if total_match:
                    break
        
        if total_match:
            total_str = total_match.group(1).replace(",", "")
            try:
                result["total_amount"] = float(total_str)
                if debug:
                    print(f"  [DEBUG] Total: ${result['total_amount']:.2f}")
            except ValueError:
                if debug:
                    print(f"  [DEBUG] Total found but couldn't parse: {total_str}")
        elif debug:
            print(f"  [DEBUG] Total not found")
        
        # Extract additional fields based on vendor
        if vendor == "franks":
            # Account number
            acct_match = re.search(patterns.get("account_number", ""), ocr_text)
            if acct_match:
                result["account_number"] = acct_match.group(1)
        elif vendor == "pacific":
            # Order number
            order_match = re.search(patterns.get("order_number", ""), ocr_text)
            if order_match:
                result["order_number"] = order_match.group(1)
            # Customer ID
            cust_match = re.search(patterns.get("customer_id", ""), ocr_text)
            if cust_match:
                result["customer_id"] = cust_match.group(1)
        
        # Extract line items
        if vendor == "franks":
            result["line_items"] = self._extract_franks_line_items(ocr_text, patterns, debug)
        elif vendor == "pacific":
            result["line_items"] = self._extract_pacific_line_items(ocr_text, patterns, debug)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(result, debug)
        result["_confidence"] = confidence
        result["_method"] = "regex"
        
        if debug:
            print(f"  [DEBUG] Confidence score: {confidence:.2f}")
            print(f"  [DEBUG] Extraction summary:")
            print(f"    - Invoice #: {result.get('invoice_number', 'NOT FOUND')}")
            print(f"    - Date: {result.get('date', 'NOT FOUND')}")
            print(f"    - Total: ${result.get('total_amount', 0):.2f}")
            print(f"    - Line items: {len(result.get('line_items', []))}")
        
        # Return if confidence is acceptable (lowered threshold for testing)
        if confidence >= 0.65:
            return result
        elif debug:
            print(f"  [DEBUG] Confidence too low ({confidence:.2f} < 0.65), returning None")
        
        return None
    
    def _extract_franks_line_items(self, text: str, patterns: Dict, debug: bool = False) -> List[Dict]:
        """
        Extract line items for Frank's Quality Produce
        
        Format: Quantity | Description | Price Each | Amount
        Example: 8 | TOMATO, ROMA # | 1.99 | 15.92
        """
        items = []
        
        # Find table section (after header)
        table_match = re.search(patterns["table_header"], text, re.IGNORECASE)
        if not table_match:
            if debug:
                print(f"    [DEBUG] Frank's table header not found")
            return items
        
        table_start = table_match.end()
        # Find where table ends (look for "Total" or special lines)
        table_end_match = re.search(r"(?:FUEL\s+SURCHARGE|Sales\s+Tax|Total)", text[table_start:], re.IGNORECASE)
        if table_end_match:
            table_text = text[table_start:table_start + table_end_match.start()]
        else:
            table_text = text[table_start:]
        
        if debug:
            print(f"    [DEBUG] Frank's table text length: {len(table_text)} chars")
            print(f"    [DEBUG] First 200 chars of table:\n{table_text[:200]}")
        
        # Extract rows - try multiple patterns
        patterns_to_try = patterns.get("line_item_alt", [patterns["line_item"]])
        
        seen_items = set()  # Track to avoid duplicates
        
        for i, pattern in enumerate(patterns_to_try):
            matches = list(re.finditer(pattern, table_text, re.MULTILINE))
            if debug and matches:
                print(f"    [DEBUG] Pattern {i} found {len(matches)} matches")
            
            for match in matches:
                try:
                    qty, desc, price_each, amount = match.groups()
                    
                    # Clean description
                    desc = desc.strip()
                    
                    # Skip headers and special items
                    if (not desc or 
                        desc.lower() in ["description", "quantity", "qty", "price each", "amount"] or
                        re.match(patterns.get("skip_items", "^$"), desc, re.IGNORECASE)):
                        continue
                    
                    # Create unique key to avoid duplicates
                    try:
                        qty_float = float(qty)
                        price_float = float(price_each)
                        amount_float = float(amount)
                        
                        item_key = (desc[:50], qty_float, price_float)
                        if item_key in seen_items:
                            continue
                        seen_items.add(item_key)
                        
                        items.append({
                            "description": desc,
                            "quantity": qty_float,
                            "unit_price": price_float,
                            "line_total": amount_float
                        })
                        
                        if debug:
                            print(f"    [DEBUG] Added item: {desc[:30]}... qty={qty_float} price={price_float} total={amount_float}")
                    except ValueError as e:
                        if debug:
                            print(f"    [DEBUG] Skipped item due to parse error: {e}")
                        continue
                except Exception as e:
                    if debug:
                        print(f"    [DEBUG] Error extracting line item: {e}")
                    continue
        
        return items
    
    def _extract_pacific_line_items(self, text: str, patterns: Dict, debug: bool = False) -> List[Dict]:
        """
        Extract line items for Pacific Food Importers
        
        Format: Product ID | Ordered | Shipped | Description | ST | Gross WT | Price/Unit | Amount
        Example: 102950 | 8.000 | 8.000 | CS FLOUR POWER 50 LB | ... | 24.063 CS | 192.50
        
        CRITICAL: Use SHIPPED column (3rd column) for quantity, not ORDERED
        """
        items = []
        
        # Find table section (after header)
        table_match = re.search(patterns["table_header"], text, re.IGNORECASE)
        if not table_match:
            if debug:
                print(f"    [DEBUG] Pacific table header not found")
            return items
        
        table_start = table_match.end()
        # Find where table ends (look for "Total Weight" or "Invoice Total")
        table_end_match = re.search(r"(?:Total\s+Weight|Invoice\s+Total|Sub\s+Total)", text[table_start:], re.IGNORECASE)
        if table_end_match:
            table_text = text[table_start:table_start + table_end_match.start()]
        else:
            table_text = text[table_start:]
        
        if debug:
            print(f"    [DEBUG] Pacific table text length: {len(table_text)} chars")
            print(f"    [DEBUG] First 300 chars of table:\n{table_text[:300]}")
        
        # Extract rows - try multiple patterns
        patterns_to_try = patterns.get("line_item_alt", [patterns["line_item"]])
        
        seen_items = set()  # Track to avoid duplicates
        
        for i, pattern in enumerate(patterns_to_try):
            matches = list(re.finditer(pattern, table_text, re.MULTILINE))
            if debug and matches:
                print(f"    [DEBUG] Pattern {i} found {len(matches)} matches")
            
            for match in matches:
                try:
                    groups = match.groups()
                    
                    # Handle different group counts from different patterns
                    if len(groups) >= 6:
                        product_id = groups[0]
                        shipped = groups[2]  # CRITICAL: Use SHIPPED (column 3), not ORDERED
                        desc = groups[3]
                        price = groups[-2]  # Second to last
                        amount = groups[-1]  # Last
                    else:
                        continue
                    
                    # Clean description
                    desc = desc.strip()
                    
                    # Skip headers
                    if (not desc or 
                        desc.upper() in ["DESCRIPTION", "PRODUCT ID", "ORDERED", "SHIPPED"] or
                        len(desc) < 3):
                        continue
                    
                    # Create unique key to avoid duplicates
                    try:
                        shipped_float = float(shipped)
                        price_float = float(price)
                        amount_float = float(amount)
                        
                        item_key = (desc[:50], shipped_float, price_float)
                        if item_key in seen_items:
                            continue
                        seen_items.add(item_key)
                        
                        items.append({
                            "description": desc,
                            "quantity": shipped_float,  # Use SHIPPED as quantity
                            "unit_price": price_float,
                            "line_total": amount_float,
                            "product_id": product_id
                        })
                        
                        if debug:
                            print(f"    [DEBUG] Added item: {desc[:30]}... qty={shipped_float} price={price_float} total={amount_float}")
                    except ValueError as e:
                        if debug:
                            print(f"    [DEBUG] Skipped item due to parse error: {e}")
                        continue
                except Exception as e:
                    if debug:
                        print(f"    [DEBUG] Error extracting line item: {e}")
                    continue
        
        return items
    
    def _calculate_confidence(self, result: Dict, debug: bool = False) -> float:
        """
        Calculate confidence score for regex extraction
        
        Scoring breakdown:
        - Required fields (vendor, invoice#, date, total): 40% (10% each)
        - Line items existence and quality: 40%
        - Data consistency (total vs line sum): 20%
        
        Args:
            result: Extracted invoice data
            debug: If True, print debugging information
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.0
        breakdown = {}
        
        # Required fields (40% total weight)
        if result.get("vendor_name"):
            confidence += 0.10
            breakdown["vendor"] = 0.10
        
        if result.get("invoice_number"):
            confidence += 0.10
            breakdown["invoice_number"] = 0.10
        
        if result.get("date"):
            confidence += 0.10
            breakdown["date"] = 0.10
        
        if result.get("total_amount") and result["total_amount"] > 0:
            confidence += 0.10
            breakdown["total"] = 0.10
        
        # Line items (40% total weight)
        line_items = result.get("line_items", [])
        if line_items:
            # Check quality of line items
            valid_items = 0
            for item in line_items:
                if (item.get("description") and 
                    item.get("quantity") is not None and 
                    item.get("unit_price") is not None and
                    item.get("line_total") is not None):
                    valid_items += 1
            
            if valid_items > 0:
                # Scale based on number of valid items (min 1, ideal 5+)
                item_score = min(0.30, (valid_items / 5.0) * 0.30)
                confidence += item_score
                breakdown["line_items_count"] = item_score
                
                # Bonus for having multiple items
                if valid_items >= 3:
                    confidence += 0.10
                    breakdown["line_items_bonus"] = 0.10
        
        # Data consistency check (20% weight)
        if line_items and result.get("total_amount"):
            line_sum = sum(item.get("line_total", 0) for item in line_items)
            total = result["total_amount"]
            
            if total > 0:
                # Calculate variance (allow for taxes, fees, surcharges)
                variance = abs(line_sum - total) / total
                
                if variance < 0.05:  # Within 5%
                    confidence += 0.20
                    breakdown["consistency"] = 0.20
                elif variance < 0.15:  # Within 15%
                    confidence += 0.15
                    breakdown["consistency"] = 0.15
                elif variance < 0.30:  # Within 30%
                    confidence += 0.10
                    breakdown["consistency"] = 0.10
                else:
                    confidence += 0.05  # Minimal credit
                    breakdown["consistency"] = 0.05
        
        if debug:
            print(f"    [DEBUG] Confidence breakdown:")
            for key, value in breakdown.items():
                print(f"      - {key}: {value:.2f}")
            print(f"    [DEBUG] Total confidence: {confidence:.2f}")
        
        return min(confidence, 1.0)


# Quick test function
def test_extractor():
    """Test the extractor with sample text"""
    extractor = RegexInvoiceExtractor()
    
    # Test vendor detection
    frank_text = "Frank's Quality Produce\n3800 1st Ave S\nSeattle, WA 98134"
    pacific_text = "Pacific Food Importers\nCUSTOMER COPY\nKENT, WA 98032"
    
    print("Testing vendor detection:")
    print(f"  Frank's: {extractor.detect_vendor(frank_text, debug=True)}")
    print(f"  Pacific: {extractor.detect_vendor(pacific_text, debug=True)}")


if __name__ == "__main__":
    test_extractor()