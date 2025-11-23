"""
SOLUTION 2: Post-OCR Text Correction (SMART FIX)
Automatically fix common OCR errors before regex extraction
"""

import re
from typing import Dict, List, Tuple


class OCRTextCorrector:
    """
    Intelligently correct common OCR misreads in invoice text
    
    This is more robust than patching regex patterns because:
    1. Fixes the text once, benefits all regex patterns
    2. Can handle multiple OCR errors systematically
    3. Maintains a dictionary of known corrections
    4. Can learn new patterns over time
    """
    
    def __init__(self):
        """Initialize correction patterns"""
        
        # Common OCR misreads in invoices (wrong -> correct)
        self.word_corrections = {
            # INVOICE variations
            "INVOKE": "INVOICE",
            "lNVOlCE": "INVOICE",
            "INV0ICE": "INVOICE",  # 0 instead of O
            "INVOlCE": "INVOICE",  # l instead of I
            
            # TOTAL variations
            "T0TAL": "TOTAL",  # 0 instead of O
            "TOTAl": "TOTAL",  # l instead of L
            "TOTAI": "TOTAL",  # I instead of L
            
            # DATE variations
            "0ATE": "DATE",  # 0 instead of D
            "OATE": "DATE",  # O instead of D
            
            # NUMBER variations
            "NUMßER": "NUMBER",  # ß instead of B
            "NUMB3R": "NUMBER",  # 3 instead of E
            
            # CUSTOMER variations
            "CUST0MER": "CUSTOMER",  # 0 instead of O
            "CUSTOMEß": "CUSTOMER",  # ß instead of R
            
            # ORDER variations
            "0RDER": "ORDER",  # 0 instead of O
            "OROER": "ORDER",  # O instead of D
            
            # SHIPPED variations
            "SHlPPED": "SHIPPED",  # l instead of I
            "SHIPP3D": "SHIPPED",  # 3 instead of E
        }
        
        # Character-level corrections (common character confusions)
        self.char_corrections = {
            # In invoice numbers
            r'\b([A-Z]+)([Ol])(\d{5,})\b': lambda m: f"{m.group(1)}{m.group(2).replace('O', '0').replace('l', '1')}{m.group(3)}",
            
            # In amounts (l instead of 1, O instead of 0)
            r'\$\s*([Ol\d,]+\.\d{2})': self._fix_amount,
        }
        
        # Context-aware corrections
        self.context_corrections = [
            # INVOICE should be followed by number or DATE
            (r'\bINVOKE\s+(?:TOTAL|DATE|#|NO|\d)', "INVOICE"),
            
            # TOTAL should be preceded by INVOICE, SUB, or GRAND
            (r'(?:INVOICE|SUB|GRAND)\s+T0TAL', lambda m: m.group(0).replace('T0TAL', 'TOTAL')),
        ]
    
    def _fix_amount(self, match) -> str:
        """Fix common OCR errors in dollar amounts"""
        amount_str = match.group(1)
        # Replace l with 1, O with 0 in amounts
        fixed = amount_str.replace('l', '1').replace('O', '0')
        return f"$ {fixed}"
    
    def correct_text(self, text: str, debug: bool = False) -> str:
        """
        Apply all corrections to OCR text
        
        Args:
            text: Raw OCR text
            debug: If True, print corrections made
            
        Returns:
            Corrected text
        """
        original_text = text
        corrections_made = []
        
        # 1. Word-level corrections
        for wrong, correct in self.word_corrections.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                corrections_made.append(f"{wrong} → {correct}")
        
        # 2. Context-aware corrections (using regex)
        for pattern, replacement in self.context_corrections:
            if callable(replacement):
                # Function-based replacement
                matches = list(re.finditer(pattern, text))
                for match in reversed(matches):  # Replace from end to avoid offset issues
                    old_text = match.group(0)
                    new_text = replacement(match)
                    text = text[:match.start()] + new_text + text[match.end():]
                    if old_text != new_text:
                        corrections_made.append(f"{old_text} → {new_text}")
            else:
                # String replacement
                if re.search(pattern, text):
                    old_matches = re.findall(pattern, text)
                    text = re.sub(pattern, replacement, text)
                    corrections_made.append(f"{pattern} → {replacement}")
        
        # 3. Character-level corrections
        for pattern, fix_func in self.char_corrections.items():
            matches = list(re.finditer(pattern, text))
            for match in reversed(matches):
                old_text = match.group(0)
                new_text = fix_func(match)
                if old_text != new_text:
                    text = text[:match.start()] + new_text + text[match.end():]
                    corrections_made.append(f"Fixed: {old_text} → {new_text}")
        
        if debug and corrections_made:
            print(f"[OCR CORRECTIONS] Made {len(corrections_made)} corrections:")
            for correction in corrections_made[:10]:  # Show first 10
                print(f"  - {correction}")
            if len(corrections_made) > 10:
                print(f"  ... and {len(corrections_made) - 10} more")
        
        return text
    
    def validate_invoice_text(self, text: str) -> Dict[str, bool]:
        """
        Validate that key invoice terms are present and correct
        
        Returns:
            Dictionary of validation checks
        """
        checks = {
            "has_invoice_keyword": bool(re.search(r'\bINVOICE\b', text, re.IGNORECASE)),
            "has_total_keyword": bool(re.search(r'\bTOTAL\b', text, re.IGNORECASE)),
            "has_date_keyword": bool(re.search(r'\bDATE\b', text, re.IGNORECASE)),
            "has_dollar_amounts": bool(re.search(r'\$\s*[\d,]+\.\d{2}', text)),
            "no_invoke_misread": "INVOKE" not in text,  # Should be corrected
        }
        
        checks["all_passed"] = all(checks.values())
        
        return checks


# Integration with regex extractor
def enhance_regex_extractor():
    """
    How to integrate OCRTextCorrector with RegexInvoiceExtractor
    """
    code_example = '''
# In regex_invoice_extractor.py, add at top:
from ocr_corrector import OCRTextCorrector

class RegexInvoiceExtractor:
    def __init__(self):
        self.patterns = {...}
        self.corrector = OCRTextCorrector()  # Add this!
    
    def extract(self, ocr_text: str, debug: bool = False) -> Optional[Dict[str, Any]]:
        """Extract invoice data using regex"""
        
        # CRITICAL: Correct OCR errors BEFORE regex extraction
        corrected_text = self.corrector.correct_text(ocr_text, debug=debug)
        
        # Validate corrections
        if debug:
            validation = self.corrector.validate_invoice_text(corrected_text)
            print(f"  [DEBUG] OCR validation: {validation}")
        
        # Now use corrected_text for all regex patterns
        vendor = self.detect_vendor(corrected_text, debug=debug)
        # ... rest of extraction using corrected_text
    '''
    
    return code_example


if __name__ == "__main__":
    # Test the corrector
    corrector = OCRTextCorrector()
    
    # Sample text with OCR errors
    sample_text = """
    Pacific Food Importers
    INVOKE NO: 378093
    INVOKE DATE: 07/15/2025
    
    Sub T0TAL: $5l9.89
    Tax: $2.86
    INVOKE TOTAL: $522.75
    """
    
    print("="*80)
    print("ORIGINAL TEXT:")
    print("="*80)
    print(sample_text)
    
    print("\n" + "="*80)
    print("CORRECTED TEXT:")
    print("="*80)
    corrected = corrector.correct_text(sample_text, debug=True)
    print(corrected)
    
    print("\n" + "="*80)
    print("VALIDATION:")
    print("="*80)
    validation = corrector.validate_invoice_text(corrected)
    for check, passed in validation.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}: {passed}")
