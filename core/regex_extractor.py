import re
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from .ocr_corrector import OCRTextCorrector
    OCR_CORRECTOR_AVAILABLE = True
except ImportError:
    OCR_CORRECTOR_AVAILABLE = False
    print("Warning: ocr_corrector not available - OCR corrections disabled")

try:
    from .vendor_registry import get_vendor_registry, VendorPattern
    VENDOR_REGISTRY_AVAILABLE = True
except ImportError:
    VENDOR_REGISTRY_AVAILABLE = False
    print("Warning: vendor_registry not available - using hardcoded patterns")


class RegexInvoiceExtractor:
    def __init__(self, use_vendor_registry: bool = True):
        if OCR_CORRECTOR_AVAILABLE:
            self.corrector = OCRTextCorrector()
        else:
            self.corrector = None
        
        self.use_vendor_registry = use_vendor_registry and VENDOR_REGISTRY_AVAILABLE
        
        if self.use_vendor_registry:
            try:
                self.vendor_registry = get_vendor_registry()
                print("✓ Using vendor registry for pattern matching")
            except Exception as e:
                print(f"Warning: Could not load vendor registry: {e}")
                print("  Falling back to hardcoded patterns")
                self.use_vendor_registry = False
                self._initialize_fallback_patterns()
        else:
            self._initialize_fallback_patterns()
    
    def _initialize_fallback_patterns(self):
        self.patterns = {
            "franks": {
                "vendor": r"Frank['']?s?\s+Quality\s+Produce",
                "invoice_number": r"Invoice\s*#?\s*:?\s*(200\d{5})",
                "date": r"Date\s*:?\s*(\d{1,2})/(\d{1,2})/(\d{4})",
                "total": r"Total\s*:?\s*\$?\s*([\d,]+\.\d{2})",
                "table_header": r"Quantity\s+Description\s+Price\s+Each\s+Amount",
                "line_item": r"^\s*(\d+)\s+([A-Z][^\d\n]{3,}?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s*$",
            },
            "pacific": {
                "vendor": r"Pacific\s+Food\s+Importers?",
                "invoice_number": r"INVOICE[\s\n]+(\d{6})",
                "invoice_number_alt": r"\b(37\d{4})\b",
                "date": r"INVOICE\s+DATE[\s\n|]+(\d{2})/(\d{2})/(\d{4})",
                "total": r"INVOICE\s+TOTAL[^\d]*(\d{1,3}(?:,\d{3})?\.\d{2})",
                "table_header": r"PRODUCT\s*ID[\s\n]+ORDERED[\s\n]+SHIPPED",
            }
        }
    
    def detect_vendor(self, text: str, debug: bool = False) -> Optional[str]:
        if self.use_vendor_registry:
            vendor_pattern = self.vendor_registry.detect_vendor(
                ocr_text=text[:2000],
                debug=debug
            )
            
            if vendor_pattern:
                vendor_id = vendor_pattern.vendor_id
                if vendor_id == "pacific_food":
                    return "pacific"
                elif vendor_id == "franks":
                    return "franks"
                else:
                    return vendor_id
            
            return None
        else:
            return self._detect_vendor_fallback(text, debug)
    
    def _detect_vendor_fallback(self, text: str, debug: bool = False) -> Optional[str]:
        text_lower = text.lower()
        
        franks_patterns = [
            r"frank['']?s?\s+quality\s+produce",
            r"warehouse@franksproduce\.net",
            r"3800\s+1st\s+ave\s+s",
        ]
        
        for pattern in franks_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if debug:
                    print(f"  [DEBUG] Vendor: Frank's Quality Produce (pattern: {pattern})")
                return "franks"
        
        pacific_patterns = [
            r"pacific\s+food\s+importers?",
            r"customer\s+copy.*kent.*wa",
        ]
        
        for pattern in pacific_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if debug:
                    print(f"  [DEBUG] Vendor: Pacific Food Importers (pattern: {pattern})")
                return "pacific"
        
        if debug:
            print(f"  [DEBUG] Vendor not detected")
        
        return None
    
    def extract(self, ocr_text: str, debug: bool = False) -> Optional[Dict[str, Any]]:
        if self.corrector:
            corrected_text = self.corrector.correct_text(ocr_text, debug=debug)
            if debug:
                validation = self.corrector.validate_invoice_text(corrected_text)
                if not validation.get("all_passed", True):
                    print(f"  [DEBUG] OCR validation warnings: {validation}")
        else:
            corrected_text = ocr_text
        
        vendor_id = self.detect_vendor(corrected_text, debug=debug)
        if not vendor_id:
            if debug:
                print(f"  [DEBUG] Vendor detection failed")
            return None
        
        if debug:
            print(f"  [DEBUG] Vendor detected: {vendor_id}")
        if self.use_vendor_registry:
            vendor_pattern = self._get_vendor_pattern(vendor_id)
            if not vendor_pattern:
                if debug:
                    print(f"  [DEBUG] Could not load vendor pattern for {vendor_id}")
                return None
        else:
            vendor_pattern = None
        
        result = self._extract_fields(
            corrected_text,
            vendor_id,
            vendor_pattern,
            debug
        )
        
        if not result:
            return None
        if self.use_vendor_registry and vendor_pattern:
            is_valid = self._validate_with_registry(result, vendor_pattern, debug)
            if not is_valid:
                if debug:
                    print(f"  [DEBUG] Validation failed using vendor registry")
                return None
        
        confidence = self._calculate_confidence(result, debug)
        result["_confidence"] = confidence
        result["_method"] = "regex"
        
        if debug:
            print(f"  [DEBUG] Confidence score: {confidence:.2f}")
        if self.use_vendor_registry and vendor_pattern:
            try:
                self.vendor_registry.learn_from_invoice(
                    vendor_id=vendor_pattern.vendor_id,
                    extracted_data=result,
                    was_successful=(confidence >= 0.60)
                )
            except Exception as e:
                if debug:
                    print(f"  [DEBUG] Could not update registry: {e}")
        
        if confidence >= 0.60:
            return result
        elif debug:
            print(f"  [DEBUG] Confidence too low ({confidence:.2f} < 0.60)")
        
        return None
    
    def _get_vendor_pattern(self, vendor_id: str) -> Optional[VendorPattern]:
        registry_id = vendor_id
        if vendor_id == "pacific":
            registry_id = "pacific_food"
        
        if registry_id in self.vendor_registry.vendors:
            return self.vendor_registry.vendors[registry_id]
        
        return None
    
    def _extract_fields(
        self,
        text: str,
        vendor_id: str,
        vendor_pattern: Optional[VendorPattern],
        debug: bool
    ) -> Optional[Dict[str, Any]]:
        result = {
            "vendor_name": self._get_vendor_name(vendor_id, vendor_pattern),
            "invoice_number": "",
            "date": "",
            "total_amount": 0.0,
            "line_items": []
        }
        invoice_num = self._extract_invoice_number(
            text, vendor_id, vendor_pattern, debug
        )
        if invoice_num:
            result["invoice_number"] = invoice_num
        
        date = self._extract_date(text, vendor_id, vendor_pattern, debug)
        if date:
            result["date"] = date
        
        total = self._extract_total(text, vendor_id, vendor_pattern, debug)
        if total:
            result["total_amount"] = total
        
        line_items = self._extract_line_items(
            text, vendor_id, vendor_pattern, debug
        )
        result["line_items"] = line_items
        
        return result
    
    def _get_vendor_name(
        self,
        vendor_id: str,
        vendor_pattern: Optional[VendorPattern]
    ) -> str:
        if vendor_pattern:
            return vendor_pattern.vendor_name
        
        if vendor_id == "franks":
            return "Frank's Quality Produce"
        elif vendor_id == "pacific":
            return "Pacific Food Importers"
        else:
            return vendor_id.replace("_", " ").title()
    
    def _extract_invoice_number(
        self,
        text: str,
        vendor_id: str,
        vendor_pattern: Optional[VendorPattern],
        debug: bool
    ) -> Optional[str]:
        if vendor_pattern:
            label = vendor_pattern.invoice_number_label
            regex = vendor_pattern.invoice_number_regex
            
            regex_pattern = regex.lstrip('^').rstrip('$')
            search_pattern = rf"{re.escape(label)}[\s\n#:]*({regex_pattern})(?:\s|$|[^\d])"
            
            match = re.search(search_pattern, text, re.IGNORECASE | re.MULTILINE)
            
            if not match:
                regex_pattern = regex.lstrip('^').rstrip('$')
                match = re.search(rf"\b({regex_pattern})\b", text, re.IGNORECASE)
            
            if match:
                invoice_num = match.group(1) if len(match.groups()) >= 1 else match.group(0)
                
                is_valid, error = self.vendor_registry.validate_invoice_number(
                    invoice_num, vendor_pattern, debug=debug
                )
                
                if is_valid:
                    if debug:
                        print(f"  [DEBUG] Invoice number: {invoice_num}")
                    return invoice_num
                else:
                    if debug:
                        print(f"  [DEBUG] Invalid invoice number '{invoice_num}': {error}")
            
            if debug:
                print(f"  [DEBUG] Invoice number not found")
            return None
        else:
            return self._extract_invoice_number_fallback(text, vendor_id, debug)
    
    def _extract_invoice_number_fallback(
        self,
        text: str,
        vendor_id: str,
        debug: bool
    ) -> Optional[str]:
        if vendor_id not in self.patterns:
            return None
        
        patterns = self.patterns[vendor_id]
        match = re.search(
            patterns["invoice_number"],
            text,
            re.IGNORECASE | re.MULTILINE
        )
        
        if not match and "invoice_number_alt" in patterns:
            match = re.search(
                patterns["invoice_number_alt"],
                text,
                re.IGNORECASE | re.MULTILINE
            )
        
        if match:
            invoice_num = match.group(1)
            
            if vendor_id == "pacific" and not invoice_num.startswith("37"):
                if debug:
                    print(f"  [DEBUG] Rejected invoice '{invoice_num}' - Pacific must start with 37")
                return None
            elif vendor_id == "franks" and not invoice_num.startswith("200"):
                if debug:
                    print(f"  [DEBUG] Rejected invoice '{invoice_num}' - Frank's must start with 200")
                return None
            
            if debug:
                print(f"  [DEBUG] Invoice number: {invoice_num}")
            return invoice_num
        
        return None
    
    def _extract_date(
        self,
        text: str,
        vendor_id: str,
        vendor_pattern: Optional[VendorPattern],
        debug: bool
    ) -> Optional[str]:
        
        if vendor_id not in self.patterns:
            return None
        
        patterns = self.patterns[vendor_id]
        
        date_match = re.search(
            patterns["date"],
            text,
            re.IGNORECASE | re.MULTILINE
        )
        
        if date_match and len(date_match.groups()) >= 3:
            month, day, year = date_match.groups()[:3]
            date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            if debug:
                print(f"  [DEBUG] Date: {date_str}")
            
            return date_str
        
        return None
    
    def _extract_total(
        self,
        text: str,
        vendor_id: str,
        vendor_pattern: Optional[VendorPattern],
        debug: bool
    ) -> Optional[float]:
        if vendor_id not in self.patterns:
            return None
        
        patterns = self.patterns[vendor_id]
        total_match = re.search(
            patterns["total"],
            text,
            re.IGNORECASE
        )
        
        if total_match:
            total_str = total_match.group(1).replace(",", "")
            try:
                total = float(total_str)
                if debug:
                    print(f"  [DEBUG] Total: ${total:.2f}")
                return total
            except ValueError:
                if debug:
                    print(f"  [DEBUG] Could not parse total: {total_str}")
        
        return None
    
    def _extract_line_items(
        self,
        text: str,
        vendor_id: str,
        vendor_pattern: Optional[VendorPattern],
        debug: bool
    ) -> List[Dict[str, Any]]:
        if vendor_id == "franks":
            return self._extract_franks_line_items(text, debug)
        elif vendor_id == "pacific":
            return self._extract_pacific_line_items(text, vendor_pattern, debug)
        else:
            return []
    
    def _extract_franks_line_items(
        self,
        text: str,
        debug: bool
    ) -> List[Dict[str, Any]]:
        items = []
        patterns = self.patterns.get("franks", {})
        
        table_match = re.search(
            patterns.get("table_header", ""),
            text,
            re.IGNORECASE
        )
        
        if not table_match:
            return items
        
        table_start = table_match.end()
        table_end_match = re.search(
            r"(?:FUEL\s+SURCHARGE|Sales\s+Tax|Total)",
            text[table_start:],
            re.IGNORECASE
        )
        
        if table_end_match:
            table_text = text[table_start:table_start + table_end_match.start()]
        else:
            table_text = text[table_start:]
        
        line_pattern = patterns.get("line_item", "")
        matches = re.finditer(line_pattern, table_text, re.MULTILINE)
        
        for match in matches:
            try:
                qty, desc, price, amount = match.groups()
                
                items.append({
                    "description": desc.strip(),
                    "quantity": float(qty),
                    "unit_price": float(price),
                    "line_total": float(amount)
                })
            except (ValueError, AttributeError):
                continue
        
        if debug:
            print(f"  [DEBUG] Extracted {len(items)} line items")
        
        return items
    
    def _extract_pacific_line_items(
        self,
        text: str,
        vendor_pattern: Optional[VendorPattern],
        debug: bool
    ) -> List[Dict[str, Any]]:
        items = []
        patterns = self.patterns.get("pacific", {})
        
        table_match = re.search(
            patterns.get("table_header", ""),
            text,
            re.IGNORECASE
        )
        
        if not table_match:
            return items
        
        table_start = table_match.end()
        table_end_match = re.search(
            r"(?:Total\s+Weight|Invoice\s+Total|Sub\s+Total)",
            text[table_start:],
            re.IGNORECASE
        )
        
        if table_end_match:
            table_text = text[table_start:table_start + table_end_match.start()]
        else:
            table_text = text[table_start:table_start + 3000]
        
        lines = table_text.split('\n')
        quantity_column = "SHIPPED"
        if vendor_pattern and vendor_pattern.column_mappings:
            quantity_column = vendor_pattern.column_mappings.get("quantity", "SHIPPED")
        
        if debug:
            print(f"  [DEBUG] Using '{quantity_column}' column for quantity")
        
        for line in lines:
            if not line.strip():
                continue
            
            match = re.match(r'(\d{5,6})\s+([\d.]+)\s+([\d.]+)', line)
            
            if match:
                product_id = match.group(1)
                ordered = float(match.group(2))
                shipped = float(match.group(3))
                
                quantity = shipped
                
                rest = line[match.end():]
                desc_match = re.search(
                    r'[/\s|]*([A-Z][A-Z\s]+[^\d]{0,30})',
                    rest,
                    re.IGNORECASE
                )
                
                if not desc_match:
                    continue
                
                description = desc_match.group(1).strip()
                description = re.sub(r'[|\s]+$', '', description)
                
                numbers = re.findall(r'([\d.]+)', rest)
                
                if len(numbers) >= 2:
                    unit_price = float(numbers[-2])
                    amount = float(numbers[-1])
                    
                    items.append({
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": amount,
                        "product_id": product_id
                    })
        
        if debug:
            print(f"  [DEBUG] Extracted {len(items)} line items")
        
        return items
    
    def _validate_with_registry(
        self,
        result: Dict[str, Any],
        vendor_pattern: VendorPattern,
        debug: bool
    ) -> bool:
        if result.get("invoice_number"):
            is_valid, error = self.vendor_registry.validate_invoice_number(
                result["invoice_number"],
                vendor_pattern,
                debug=debug
            )
            
            if not is_valid:
                if debug:
                    print(f"  [DEBUG] Validation failed: {error}")
                return False
        
        if result.get("vendor_name"):
            if result["vendor_name"] != vendor_pattern.vendor_name:
                if debug:
                    print(f"  [DEBUG] Vendor name mismatch: '{result['vendor_name']}' != '{vendor_pattern.vendor_name}'")
                result["vendor_name"] = vendor_pattern.vendor_name
        
        return True
    
    def _calculate_confidence(self, result: Dict, debug: bool = False) -> float:
        confidence = 0.0
        breakdown = {}
        
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
        
        line_items = result.get("line_items", [])
        if line_items:
            valid_items = sum(
                1 for item in line_items
                if item.get("description")
                and item.get("quantity") is not None
                and item.get("unit_price") is not None
                and item.get("line_total") is not None
            )
            
            if valid_items > 0:
                item_score = min(0.30, (valid_items / 5.0) * 0.30)
                confidence += item_score
                breakdown["line_items"] = item_score
                
                if valid_items >= 3:
                    confidence += 0.10
                    breakdown["line_items_bonus"] = 0.10
        
        if line_items and result.get("total_amount"):
            line_sum = sum(item.get("line_total", 0) for item in line_items)
            total = result["total_amount"]
            
            if total > 0:
                variance = abs(line_sum - total) / total
                
                if variance < 0.05:
                    confidence += 0.20
                    breakdown["consistency"] = 0.20
                elif variance < 0.15:
                    confidence += 0.15
                    breakdown["consistency"] = 0.15
                elif variance < 0.30:
                    confidence += 0.10
                    breakdown["consistency"] = 0.10
                else:
                    confidence += 0.05
                    breakdown["consistency"] = 0.05
        
        if debug:
            print(f"  [DEBUG] Confidence breakdown:")
            for key, value in breakdown.items():
                print(f"    - {key}: {value:.2f}")
        
        return min(confidence, 1.0)


def test_extractor():
    extractor = RegexInvoiceExtractor()
    
    frank_text = "Frank's Quality Produce\nInvoice #20065629\nDate: 07/15/2025\nTotal: $109.26"
    pacific_text = "Pacific Food Importers\nINVOICE\n378093\nINVOICE DATE\n07/15/2025\nINVOICE TOTAL $522.75"
    
    print("="*60)
    print("Testing Regex Extractor with Vendor Registry")
    print("="*60)
    
    print("\n1. Testing Frank's Quality Produce:")
    print("-"*60)
    result = extractor.extract(frank_text, debug=True)
    if result:
        print(f"✓ Extracted: Invoice #{result['invoice_number']}, Total: ${result['total_amount']:.2f}")
    else:
        print("✗ Extraction failed")
    
    print("\n2. Testing Pacific Food Importers:")
    print("-"*60)
    result = extractor.extract(pacific_text, debug=True)
    if result:
        print(f"✓ Extracted: Invoice #{result['invoice_number']}, Total: ${result['total_amount']:.2f}")
    else:
        print("✗ Extraction failed")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    test_extractor()