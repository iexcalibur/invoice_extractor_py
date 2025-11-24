import json
import base64
import re
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os
import warnings
import logging

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*device.*")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)

try:
    import anthropic
    from pdf2image import convert_from_path
    from PIL import Image
    import cv2
    import numpy as np
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    raise

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: Tesseract not available")

try:
    from .enhanced_ocr import extract_text_with_enhanced_ocr
    ENHANCED_OCR_AVAILABLE = True
except ImportError:
    ENHANCED_OCR_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification, AutoTokenizer
    import torch
    LAYOUTLMV3_AVAILABLE = True
except ImportError:
    LAYOUTLMV3_AVAILABLE = False

TEXT_PARSING_MODEL = "claude-3-haiku-20240307"

try:
    from .config import Config
except ImportError:
    Config = None

try:
    from .vendor_registry import get_vendor_registry
    VENDOR_REGISTRY_AVAILABLE = True
except ImportError:
    VENDOR_REGISTRY_AVAILABLE = False
    print("Warning: vendor_registry module not available")

REGEX_EXTRACTOR_AVAILABLE = False
regex_extractor_module = None

try:
    from .regex_extractor import RegexInvoiceExtractor
    REGEX_EXTRACTOR_AVAILABLE = True
    regex_extractor_module = "regex_extractor"
    print("✓ Using regex extractor")
except ImportError:
    print("Warning: No regex_extractor module found. Regex extraction will be disabled.")
    print("  To enable regex extraction, ensure regex_extractor.py is in the same directory.")


def _parse_claude_json_response(response_text: str, debug: bool = False) -> Optional[Dict[str, Any]]:
    if not response_text or not response_text.strip():
        if debug:
            print(f"  [DEBUG] Empty response text")
        return None
    
    text = response_text.strip()
    
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\w*\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_text = text[first_brace:last_brace + 1]
    else:
        json_text = text
    
    try:
        result = json.loads(json_text)
        if debug:
            print(f"  [DEBUG] Successfully parsed JSON ({len(json_text)} chars)")
        return result
    except json.JSONDecodeError as e:
        if debug:
            print(f"  [DEBUG] JSON parse error: {e}")
            print(f"  [DEBUG] Attempted to parse: {json_text[:200]}...")
            print(f"  [DEBUG] Full response (first 500 chars): {response_text[:500]}")
        
        if '{' in json_text:
            json_text = json_text[json_text.index('{'):]
        
        if '}' in json_text:
            json_text = json_text[:json_text.rindex('}') + 1]
        
        try:
            result = json.loads(json_text)
            if debug:
                print(f"  [DEBUG] Successfully parsed after cleanup")
            return result
        except json.JSONDecodeError:
            if debug:
                print(f"  [DEBUG] Still failed after cleanup")
            return None


class EnhancedInvoiceExtractor:
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-3-haiku-20240307",
        use_regex: bool = True,
        use_layoutlmv3: bool = True,
        use_ocr: bool = True,
        ocr_engine: str = "tesseract",
        use_enhanced_ocr: bool = True,  
        regex_confidence_threshold: float = 0.60,
        layoutlmv3_confidence_threshold: float = 0.50
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.use_regex = use_regex and REGEX_EXTRACTOR_AVAILABLE
        self.use_layoutlmv3 = use_layoutlmv3 and LAYOUTLMV3_AVAILABLE
        self.use_ocr = use_ocr and (TESSERACT_AVAILABLE or EASYOCR_AVAILABLE)
        self.ocr_engine = ocr_engine
        self.use_enhanced_ocr = use_enhanced_ocr and ENHANCED_OCR_AVAILABLE
        self.regex_confidence_threshold = regex_confidence_threshold
        self.layoutlmv3_confidence_threshold = layoutlmv3_confidence_threshold
        
        if VENDOR_REGISTRY_AVAILABLE:
            try:
                self.vendor_registry = get_vendor_registry()
            except Exception as e:
                print(f"Warning: Could not initialize vendor registry: {e}")
                self.vendor_registry = None
        else:
            self.vendor_registry = None
        
        if self.use_regex:
            try:
                self.regex_extractor = RegexInvoiceExtractor()
                print(f"✓ Regex extractor initialized (module: {regex_extractor_module})")
                print("  Supported vendors: Frank's Quality Produce & Pacific Food Importers")
            except Exception as e:
                print(f"Warning: Could not initialize regex extractor: {e}")
                self.use_regex = False
                self.regex_extractor = None
        else:
            self.regex_extractor = None
        
        if self.api_key:
            try:
                self.claude_client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Claude client: {e}")
                self.claude_client = None
        else:
            self.claude_client = None
            print("Warning: No Anthropic API key provided. Claude-based extraction will be disabled.")
        
        self.layoutlmv3_processor = None
        self.layoutlmv3_model = None
        self.layoutlmv3_tokenizer = None
        if self.use_layoutlmv3:
            try:
                logging.getLogger("transformers").setLevel(logging.ERROR)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    print("Loading LayoutLMv3 model for structured extraction...")
                    model_name = "microsoft/layoutlmv3-base"
                    self.layoutlmv3_processor = LayoutLMv3Processor.from_pretrained(model_name)
                    from transformers import LayoutLMv3Model
                    self.layoutlmv3_model = LayoutLMv3Model.from_pretrained(model_name)
                    self.layoutlmv3_tokenizer = AutoTokenizer.from_pretrained(model_name)
                
                if torch.cuda.is_available():
                    self.layoutlmv3_model.to("cuda")
                self.layoutlmv3_model.eval()
                print("✓ LayoutLMv3 model loaded successfully")
            except Exception as e:
                print(f"Warning: Could not load LayoutLMv3 model: {e}")
                self.use_layoutlmv3 = False
        
        if self.use_ocr:
            if self.ocr_engine == "easyocr" and EASYOCR_AVAILABLE:
                try:
                    print("Initializing EasyOCR...")
                    self.easyocr_reader = easyocr.Reader(['en'])
                    print("✓ EasyOCR initialized")
                except Exception as e:
                    print(f"Warning: Could not initialize EasyOCR: {e}")
                    if TESSERACT_AVAILABLE:
                        self.ocr_engine = "tesseract"
                        print("  Falling back to Tesseract")
                    else:
                        self.use_ocr = False
            elif self.ocr_engine == "tesseract" and not TESSERACT_AVAILABLE:
                if EASYOCR_AVAILABLE:
                    self.ocr_engine = "easyocr"
                    print("  Using EasyOCR instead of Tesseract")
                else:
                    self.use_ocr = False
                    print("Warning: No OCR engine available")
    
    def detect_file_type(self, file_path: str) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return 'pdf'
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']:
            return 'image'
        else:
            return 'unknown'
    
    def load_images(self, file_path: str) -> List[Image.Image]:
        file_type = self.detect_file_type(file_path)
        
        if file_type == 'pdf':
            vision_dpi = 200
            print(f"Converting PDF to images: {file_path} (DPI: {vision_dpi})")
            images = convert_from_path(
                file_path,
                dpi=vision_dpi,
                fmt='png',
                grayscale=False,
                use_pdftocairo=True
            )
            return images
        elif file_type == 'image':
            print(f"Loading image: {file_path}")
            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return [image]
        else:
            raise ValueError(f"Unsupported file type: {file_path}")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        try:
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            denoised = cv2.fastNlMeansDenoising(enhanced)
            rgb = cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)
            
            return Image.fromarray(rgb)
        except Exception as e:
            print(f"Warning: Image preprocessing failed: {e}. Using original image.")
            return image
    
    def extract_with_regex(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        if not self.use_regex or self.regex_extractor is None:
            return None
        
        try:
            if self.use_enhanced_ocr and TESSERACT_AVAILABLE:
                debug_ocr = os.getenv("DEBUG_REGEX", "").lower() == "true"
                ocr_text = extract_text_with_enhanced_ocr(image, debug=debug_ocr)
            elif TESSERACT_AVAILABLE:
                ocr_text = pytesseract.image_to_string(image)
            elif EASYOCR_AVAILABLE:
                results = self.easyocr_reader.readtext(np.array(image))
                ocr_text = "\n".join([result[1] for result in results])
            else:
                return None
            
            if not ocr_text or len(ocr_text.strip()) < 50:
                if os.getenv("DEBUG_REGEX", "").lower() == "true":
                    print(f"  [DEBUG] OCR text too short: {len(ocr_text.strip())} chars")
                return None
            
            debug_regex = os.getenv("DEBUG_REGEX", "").lower() == "true"
            result = self.regex_extractor.extract(ocr_text, debug=debug_regex)
            
            if result and result.get("_confidence", 0) >= self.regex_confidence_threshold:
                print(f"  ✓ Regex extraction successful (confidence: {result['_confidence']:.2%})")
                return result
            elif result:
                conf = result.get("_confidence", 0)
                print(f"  ⚠ Regex extraction low confidence ({conf:.2%} < {self.regex_confidence_threshold:.2%})")
                if debug_regex:
                    print(f"  [DEBUG] Extracted: invoice_number={result.get('invoice_number')}, "
                          f"date={result.get('date')}, total={result.get('total_amount')}, "
                          f"items={len(result.get('line_items', []))}")
                return None
            else:
                if debug_regex:
                    print("  ✗ Regex extraction failed (vendor not recognized)")
                    print(f"  [DEBUG] Set DEBUG_REGEX=true for detailed output")
                return None
                
        except Exception as e:
            print(f"  Regex extraction error: {e}")
            if os.getenv("DEBUG_REGEX", "").lower() == "true":
                import traceback
                traceback.print_exc()
            return None
    
    def _extract_layout_structure(self, ocr_data: Dict, image: Image.Image) -> Dict[str, Any]:
        layout_info = {
            "tables": [],
            "headers": [],
            "text_regions": [],
            "word_positions": []
        }
        
        if not ocr_data or "text" not in ocr_data:
            return layout_info
        
        words = []
        for i in range(len(ocr_data.get("text", []))):
            text = ocr_data["text"][i].strip()
            if text and ocr_data.get("conf", [0])[i] > 0:
                words.append({
                    "text": text,
                    "x": ocr_data.get("left", [0])[i],
                    "y": ocr_data.get("top", [0])[i],
                    "width": ocr_data.get("width", [0])[i],
                    "height": ocr_data.get("height", [0])[i],
                    "conf": ocr_data.get("conf", [0])[i]
                })
        
        layout_info["word_positions"] = words
        
        if words:
            rows = {}
            for word in words:
                y_key = round(word["y"] / 10) * 10
                if y_key not in rows:
                    rows[y_key] = []
                rows[y_key].append(word)
            
            sorted_rows = sorted(rows.items())
            
            table_start = None
            current_table = []
            
            for y_key, row_words in sorted_rows:
                row_words.sort(key=lambda w: w["x"])
                
                if len(row_words) >= 3:
                    if table_start is None:
                        table_start = y_key
                    current_table.append({
                        "y": y_key,
                        "words": row_words
                    })
                else:
                    if current_table:
                        layout_info["tables"].append({
                            "start_y": table_start,
                            "rows": current_table
                        })
                    table_start = None
                    current_table = []
            
            if current_table:
                layout_info["tables"].append({
                    "start_y": table_start,
                    "rows": current_table
                })
        
        return layout_info
    
    def _calculate_confidence(self, extracted_data: Dict[str, Any], layout_info: Dict[str, Any]) -> float:
        confidence = 0.0
        
        required_fields = ["invoice_number", "date", "vendor_name", "total_amount"]
        field_score = sum(1 for field in required_fields 
                         if extracted_data.get(field) and extracted_data[field] != "")
        confidence += (field_score / len(required_fields)) * 0.4
        
        line_items = extracted_data.get("line_items", [])
        if line_items:
            valid_items = sum(1 for item in line_items
                            if item.get("description") and item.get("quantity") is not None)
            if valid_items > 0:
                confidence += (valid_items / len(line_items)) * 0.3
        
        if layout_info.get("tables"):
            confidence += 0.2
        else:
            confidence += 0.1
        
        total = extracted_data.get("total_amount", 0)
        if total and total > 0:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def extract_with_layoutlmv3(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        if not self.use_layoutlmv3 or self.layoutlmv3_processor is None:
            return None
        
        try:
            if TESSERACT_AVAILABLE:
                ocr_text = pytesseract.image_to_string(image)
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            else:
                ocr_text = ""
                ocr_data = {}
            
            if not ocr_text or len(ocr_text.strip()) < 50:
                return None
            
            layout_info = self._extract_layout_structure(ocr_data, image)
            
            encoding = self.layoutlmv3_processor(
                image, 
                ocr_text, 
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=1024
            )
            
            # Validate encoding before processing
            if not encoding or 'input_ids' not in encoding:
                print(f"  ⚠ LayoutLMv3: Invalid encoding, skipping")
                return None
            
            # Check tensor shapes to prevent index errors
            input_ids = encoding.get('input_ids')
            if input_ids is not None and len(input_ids.shape) > 0:
                if input_ids.shape[0] == 0 or input_ids.shape[1] == 0:
                    print(f"  ⚠ LayoutLMv3: Empty input tensors, skipping")
                    return None
            
            if torch.cuda.is_available():
                encoding = {k: v.to("cuda") if isinstance(v, torch.Tensor) else v for k, v in encoding.items()}
            
            with torch.no_grad():
                try:
                    outputs = self.layoutlmv3_model(**encoding)
                except (IndexError, RuntimeError) as e:
                    print(f"  ⚠ LayoutLMv3 model error: {e}")
                    print(f"  ⚠ Falling back to OCR extraction")
                    return None
            
            if self.claude_client and ocr_text:
                try:
                    layout_enhanced_text = ocr_text
                    if layout_info.get("tables"):
                        table_hints = "\n\n[LAYOUT INFO: Document has structured tables]\n"
                        for i, table in enumerate(layout_info["tables"][:2]):
                            table_hints += f"Table {i+1}: {len(table['rows'])} rows\n"
                        layout_enhanced_text = ocr_text + table_hints
                    
                    # Detect vendor for column mapping
                    vendor_instructions = self._get_vendor_instructions(ocr_text)
                    
                    # Use cheaper model for text parsing
                    text_model = TEXT_PARSING_MODEL if TEXT_PARSING_MODEL else self.model
                    response = self.claude_client.messages.create(
                        model=text_model,
                        max_tokens=4000,
                        messages=[{
                            "role": "user",
                            "content": self._build_extraction_prompt(ocr_text[:3000], vendor_instructions)
                        }]
                    )
                    
                    response_text = response.content[0].text.strip()
                    
                    # Use robust JSON parser
                    extracted_data = _parse_claude_json_response(response_text, debug=True)
                    
                    if not extracted_data:
                        print(f"  ⚠ LayoutLMv3 + Claude: Failed to parse JSON response")
                        return None
                    
                    # Calculate confidence
                    confidence = self._calculate_confidence(extracted_data, layout_info)
                    extracted_data["_confidence"] = confidence
                    extracted_data["_method"] = "layoutlmv3"
                    
                    if confidence >= self.layoutlmv3_confidence_threshold:
                        print(f"  ✓ LayoutLMv3 extraction successful (confidence: {confidence:.2%})")
                        return extracted_data
                    else:
                        print(f"  ⚠ LayoutLMv3 low confidence ({confidence:.2%}), trying fallback")
                        return None
                        
                except json.JSONDecodeError as e:
                    print(f"  LayoutLMv3 + Claude JSON parsing error: {e}")
                    print(f"  Raw response (first 300 chars): {response.content[0].text[:300]}")
                    return None
                except Exception as e:
                    print(f"  LayoutLMv3 + Claude parsing error: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
            
            return None
            
        except Exception as e:
            print(f"  LayoutLMv3 extraction error: {e}")
            return None
    
    def _get_vendor_instructions(self, ocr_text: str) -> str:
        # Try vendor registry first (preferred method)
        if self.vendor_registry:
            vendor = self.vendor_registry.detect_vendor(
                ocr_text=ocr_text[:2000],
                debug=False
            )
            
            if vendor:
                instructions = self.vendor_registry.get_extraction_instructions(vendor)
                print(f"  ℹ️  Using vendor instructions from registry: {vendor.vendor_name}")
                return instructions
        
        # Fallback to hardcoded instructions
        ocr_lower = ocr_text.lower()
        
        if "frank" in ocr_lower and "quality produce" in ocr_lower:
            return """
VENDOR: FRANK'S QUALITY PRODUCE
- Invoice Number: Must ALWAYS start with "200" (e.g., "Invoice #20065629", "Invoice #20012345")
- DO NOT use numbers that don't start with 200 - those are not invoice numbers
- Quantity: First column in line items table
- Unit Price: "Price Each" column
- Line Total: "Amount" column
- Total: Bottom right corner (e.g., "Total $109.26")
CRITICAL: 
1. Invoice number MUST start with "200" - reject any other numbers
2. Use exact "Price Each" values, NOT calculated. Extract total from bottom right."""
        
        elif "pacific food" in ocr_lower and "importers" in ocr_lower:
            return """
VENDOR: PACIFIC FOOD IMPORTERS
- Vendor Name: MUST be "Pacific Food Importers" (this is the company issuing the invoice)
- CRITICAL: DO NOT use "Sold To:" or "Ship To:" customer names (like "Westmans Bagel & Caffe") as vendor
- The vendor is always "Pacific Food Importers" - it appears in the header/company name
- Invoice Number: Located at TOP RIGHT CORNER of invoice, labeled "INVOICE" followed by 6-digit number
- CRITICAL: Invoice numbers start with "37" (e.g., "INVOICE 370123", "INVOICE 378093", "INVOICE 379549")
- DO NOT use numbers starting with other digits (like 444509, 444434) - those are ORDER NO values
- DO NOT confuse with "ORDER NO" - ORDER NO is different and appears in a table below
- Quantity: "SHIPPED" column (3rd column) - extract EXACT values
- Unit Price: "Price" column - extract exact decimals
- Line Total: "Amount" column
- Total: Bottom section (e.g., "INVOICE TOTAL $596.94")
CRITICAL: 
1. vendor_name MUST be exactly "Pacific Food Importers" - NOT the customer name
2. Invoice number MUST start with "37" - reject any other numbers
3. Invoice number is at TOP RIGHT - look for "INVOICE" followed by 6 digits starting with 37
4. Use SHIPPED column for quantity, NOT Ordered. Extract exact values."""
        
        return ""
    
    def _get_vendor_instructions_fallback(self) -> str:
        return """
For Frank's Quality Produce:
- Invoice Number: MUST start with "200" (e.g., "Invoice #20065629", "Invoice #20012345")
- DO NOT use numbers that don't start with 200
- Use "Price Each" column for unit_price
- Use FIRST column for quantity
- Extract total from bottom right corner

For Pacific Food Importers:
- Vendor Name: MUST be exactly "Pacific Food Importers" (the company issuing the invoice)
- CRITICAL: DO NOT use customer names from "Sold To:" or "Ship To:" sections (like "Westmans Bagel & Caffe") as vendor
- The vendor is the company name in the header - always "Pacific Food Importers"
- Invoice Number: Look at TOP RIGHT CORNER for "INVOICE" followed by 6-digit number
- CRITICAL: Invoice number MUST start with "37" (e.g., "INVOICE 370123", "INVOICE 378093", "INVOICE 379549")
- DO NOT use "ORDER NO" as invoice number - ORDER NO is different and appears in a table (numbers like 444509, 444434 are ORDER NO, not invoice numbers)
- If you find a number that doesn't start with 37, it's NOT the invoice number
- Use "SHIPPED" column for quantity (exact values)
- Use "Price" column for unit_price
- Extract total from bottom
"""
    
    def _build_extraction_prompt(self, ocr_text: str, vendor_instructions: str) -> str:
        base_prompt = f"""Extract invoice data from this OCR text.

OCR Text:
{ocr_text}

{vendor_instructions}

Extract ALL line items with:
- description: Product name
- quantity: Numeric value (float)
- unit_price: Price per unit (float)
- line_total: Total for line (float)

Extract invoice fields:
- invoice_number: Invoice number
  * For Pacific Food Importers: look at TOP RIGHT corner for "INVOICE" followed by 6-digit number starting with "37", NOT "ORDER NO"
  * For Frank's Quality Produce: invoice number MUST start with "200" (e.g., "Invoice #20065629", "Invoice #20012345")
- date: YYYY-MM-DD format
- vendor_name: Vendor name (the company issuing the invoice)
  * For Pacific Food Importers: MUST be exactly "Pacific Food Importers" - NOT the customer name from "Sold To:" or "Ship To:"
  * DO NOT use customer names like "Westmans Bagel & Caffe" as vendor - that's the customer, not the vendor
- total_amount: Total amount (float, from bottom of invoice)

CRITICAL: 
- For Pacific Food Importers: Invoice number MUST start with "37" (e.g., "INVOICE 370123", "INVOICE 378093", "INVOICE 379549")
  Invoice number is at TOP RIGHT corner labeled "INVOICE". DO NOT use "ORDER NO" values (like 444509, 444434).
- For Frank's Quality Produce: Invoice number MUST start with "200" (e.g., "Invoice #20065629", "Invoice #20012345")
  If you find a number that doesn't start with 200, it's NOT the invoice number for Frank's Quality Produce.
- Extract total_amount from invoice bottom, NOT by summing line items
- For quantities, use exact column values (no calculations)
- For unit_price, use exact "Price Each" or "Price" column values
- Extract numeric values as numbers, not strings

Return ONLY valid JSON:
{{
  "invoice_number": "...",
  "date": "YYYY-MM-DD",
  "vendor_name": "...",
  "total_amount": 0.00,
  "line_items": [
    {{
      "description": "...",
      "quantity": 0.0,
      "unit_price": 0.00,
      "line_total": 0.00
    }}
  ]
}}"""
        return base_prompt
    
    def extract_with_ocr(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        if not self.use_ocr:
            return None
        
        try:
            if self.ocr_engine == "tesseract" and TESSERACT_AVAILABLE:
                ocr_text = pytesseract.image_to_string(image)
            elif self.ocr_engine == "easyocr" and EASYOCR_AVAILABLE:
                results = self.easyocr_reader.readtext(np.array(image))
                ocr_text = "\n".join([result[1] for result in results])
            else:
                return None
            
            if self.claude_client:
                try:
                    vendor_instructions = self._get_vendor_instructions(ocr_text)
                    text_model = TEXT_PARSING_MODEL if TEXT_PARSING_MODEL else self.model
                    
                    response = self.claude_client.messages.create(
                        model=text_model,
                        max_tokens=4000,
                        messages=[{
                            "role": "user",
                            "content": self._build_extraction_prompt(ocr_text[:3000], vendor_instructions)
                        }]
                    )
                    
                    response_text = response.content[0].text.strip()
                    
                    extracted_data = _parse_claude_json_response(response_text, debug=True)
                    
                    if not extracted_data:
                        print(f"  ⚠ OCR + Claude: Failed to parse JSON response")
                        return None
                    
                    extracted_data["_method"] = "ocr"
                    return extracted_data
                    
                except json.JSONDecodeError as e:
                    print(f"  OCR + Claude JSON parsing error: {e}")
                    print(f"  Raw response (first 300 chars): {response.content[0].text[:300]}")
                    return None
                except Exception as e:
                    print(f"  OCR + Claude parsing error: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
            else:
                return self._parse_ocr_text_basic(ocr_text)
                
        except Exception as e:
            print(f"  OCR extraction error: {e}")
            return None
    
    def _parse_ocr_text_basic(self, text: str) -> Dict[str, Any]:
        return {
            "invoice_number": "",
            "date": "",
            "vendor_name": "",
            "total_amount": 0.0,
            "line_items": [],
            "raw_ocr_text": text[:500]
        }
    
    def extract_with_claude(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        if not self.claude_client:
            return None
        
        try:
            processed_image = self.preprocess_image(image)
            
            buffered = BytesIO()
            processed_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            vendor_instructions = ""
            if self.vendor_registry:
                try:
                    if TESSERACT_AVAILABLE:
                        ocr_text = pytesseract.image_to_string(image)
                    elif EASYOCR_AVAILABLE:
                        results = self.easyocr_reader.readtext(np.array(image))
                        ocr_text = "\n".join([result[1] for result in results])
                    else:
                        ocr_text = ""
                    
                    if ocr_text:
                        vendor = self.vendor_registry.detect_vendor(
                            ocr_text=ocr_text[:2000],
                            debug=False
                        )
                        
                        if vendor:
                            vendor_instructions = self.vendor_registry.get_extraction_instructions(vendor)
                            print(f"  ℹ️  Using vendor instructions from registry: {vendor.vendor_name}")
                except Exception as e:
                    # If vendor detection fails, fall back to hardcoded instructions
                    pass
            
            
            if not vendor_instructions:
                vendor_instructions = self._get_vendor_instructions_fallback()
            
            claude_model = TEXT_PARSING_MODEL if TEXT_PARSING_MODEL else "claude-3-haiku-20240307"
            response = self.claude_client.messages.create(
                model=claude_model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"""Extract invoice data from this image.

{vendor_instructions}

Return ONLY valid JSON:
{
  "invoice_number": "...",
  "date": "YYYY-MM-DD",
  "vendor_name": "...",
  "total_amount": 0.00,
  "line_items": [
    {
      "description": "...",
      "quantity": 0.0,
      "unit_price": 0.00,
      "line_total": 0.00
    }
  ]
}"""
                        }
                    ]
                }]
            )
            
            response_text = response.content[0].text.strip()
            
            extracted_data = _parse_claude_json_response(response_text, debug=True)
            
            if not extracted_data:
                print(f"  ⚠ Claude Vision: Failed to parse JSON response")
                print(f"  Raw response (first 500 chars): {response_text[:500]}")
                return None
            
            extracted_data["_method"] = "claude_vision"
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"  Claude Vision JSON parsing error: {e}")
            print(f"  Raw response (first 500 chars): {response.content[0].text[:500]}")
            return None
        except Exception as e:
            print(f"  Claude Vision extraction error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def validate_extraction(self, result: Dict[str, Any], strict: bool = False, debug: bool = False) -> bool:
        required_fields = ['invoice_number', 'date', 'vendor_name', 'total_amount']
        
        vendor_name = result.get('vendor_name', '')
        invoice_number = result.get('invoice_number', '')
        
        if self.vendor_registry and vendor_name and invoice_number:
            vendor = self.vendor_registry.detect_vendor(
                vendor_name=vendor_name,
                invoice_number=str(invoice_number),
                debug=debug
            )
            
            if vendor:
                is_valid, error_msg = self.vendor_registry.validate_invoice_number(
                    str(invoice_number),
                    vendor,
                    debug=debug
                )
                if not is_valid:
                    if debug:
                        print(f"  [DEBUG] Validation failed: {vendor.vendor_name} invoice number '{invoice_number}' - {error_msg}")
                    return False
        
        if not strict:
            fields_present = sum(1 for field in required_fields 
                               if field in result and result[field] is not None and result[field] != "")
            
            if fields_present >= 3:
                for field in required_fields:
                    if field in result and result[field] is not None:
                        if field == 'date':
                            try:
                                if result['date']:
                                    datetime.strptime(result['date'], '%Y-%m-%d')
                            except (ValueError, TypeError):
                                return False
                        elif field == 'total_amount':
                            if not isinstance(result['total_amount'], (int, float)):
                                try:
                                    float(result['total_amount'])
                                except (ValueError, TypeError):
                                    return False
                return True
        
        for field in required_fields:
            if field not in result or result[field] is None:
                return False
            if field != 'total_amount' and result[field] == "":
                return False
        
        try:
            if result['date']:
                datetime.strptime(result['date'], '%Y-%m-%d')
        except (ValueError, TypeError):
            return False
        
        if not isinstance(result['total_amount'], (int, float)):
            try:
                float(result['total_amount'])
            except (ValueError, TypeError):
                return False
        
        return True
    
    def extract_robust(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "error": f"File not found: {file_path}",
                "pdf": file_path
            }
        
        try:
            images = self.load_images(file_path)
            extracted_data = []
            
            for page_num, image in enumerate(images):
                print(f"\nProcessing page {page_num + 1}/{len(images)}...")
                
                page_result = None
                method_used = None
                
                if self.use_regex:
                    print("  [1/4] Trying regex extraction (fastest, free)...")
                    page_result = self.extract_with_regex(image)
                    if page_result:
                        if self.validate_extraction(page_result, strict=False, debug=True):
                            method_used = "regex"
                        else:
                            if page_result:
                                print(f"  [DEBUG] Regex extraction failed validation. Extracted: vendor='{page_result.get('vendor_name')}', invoice='{page_result.get('invoice_number')}', date='{page_result.get('date')}', total={page_result.get('total_amount')}")
                            page_result = None
                
                if not page_result:
                    if self.use_layoutlmv3:
                        print("  [2/4] Trying LayoutLMv3 extraction (with layout understanding)...")
                        page_result = self.extract_with_layoutlmv3(image)
                        if page_result:
                            if self.validate_extraction(page_result, strict=False, debug=True):
                                method_used = "layoutlmv3"
                            else:
                                if page_result:
                                    print(f"  [DEBUG] LayoutLMv3 extraction failed validation. Extracted: vendor='{page_result.get('vendor_name')}', invoice='{page_result.get('invoice_number')}', date='{page_result.get('date')}', total={page_result.get('total_amount')}")
                                page_result = None
                
                if not page_result:
                    if self.use_ocr:
                        print("  [3/4] Trying OCR extraction (with cheap Claude Haiku)...")
                        page_result = self.extract_with_ocr(image)
                        if page_result:
                            if self.validate_extraction(page_result, strict=False, debug=True):
                                method_used = "ocr"
                            else:
                                if page_result:
                                    print(f"  [DEBUG] OCR extraction failed validation. Extracted: vendor='{page_result.get('vendor_name')}', invoice='{page_result.get('invoice_number')}', date='{page_result.get('date')}', total={page_result.get('total_amount')}")
                                page_result = None
                
                if not page_result:
                    if self.claude_client:
                        print("  [4/4] Trying Claude Vision (expensive fallback)...")
                        page_result = self.extract_with_claude(image)
                        if page_result:
                            if self.validate_extraction(page_result, strict=True, debug=True):
                                method_used = "claude_vision"
                            else:
                                if page_result:
                                    print(f"  [DEBUG] Claude Vision extraction failed validation. Extracted: vendor='{page_result.get('vendor_name')}', invoice='{page_result.get('invoice_number')}', date='{page_result.get('date')}', total={page_result.get('total_amount')}")
                                page_result = None
                
                if page_result:
                    vendor_name = page_result.get('vendor_name', '')
                    invoice_number = page_result.get('invoice_number', '')
                    
                    if self.vendor_registry:
                        vendor = self.vendor_registry.detect_vendor(
                            vendor_name=vendor_name,
                            invoice_number=str(invoice_number) if invoice_number else "",
                            debug=False
                        )
                        
                        if vendor:
                            if vendor_name.lower() != vendor.vendor_name.lower():
                                print(f"  ⚠ Warning: Incorrect vendor name '{vendor_name}' - correcting to '{vendor.vendor_name}'")
                                page_result['vendor_name'] = vendor.vendor_name
                            
                            is_valid, error_msg = self.vendor_registry.validate_invoice_number(
                                str(invoice_number) if invoice_number else "",
                                vendor,
                                debug=False
                            )
                            
                            if not is_valid and invoice_number:
                                print(f"  ⚠ Warning: Invoice number '{invoice_number}' doesn't match {vendor.vendor_name} pattern")
                                print(f"     Attempting to find correct invoice number...")
                                
                                if TESSERACT_AVAILABLE:
                                    try:
                                        ocr_text = pytesseract.image_to_string(image)
                                        pattern = vendor.invoice_number_regex.replace('^', '').replace('$', '')
                                        correct_inv_match = re.search(
                                            rf'{vendor.invoice_number_label}\s*:?\s*({pattern})',
                                            ocr_text[:2000],
                                            re.IGNORECASE
                                        )
                                        if correct_inv_match:
                                            page_result['invoice_number'] = correct_inv_match.group(1)
                                            print(f"     ✓ Found correct invoice number: {page_result['invoice_number']}")
                                    except Exception:
                                        pass  
                    if '_confidence' not in page_result or page_result.get('_confidence') is None:
                        layout_info = {}
                        page_result['_confidence'] = self._calculate_confidence(page_result, layout_info)
                    
                    page_result['page_number'] = page_num + 1
                    page_result['extraction_method'] = method_used
                    extracted_data.append(page_result)
                    print(f"  ✓ Extraction successful using {method_used} (confidence: {page_result.get('_confidence', 0):.2%})")
                else:
                    extracted_data.append({
                        "page_number": page_num + 1,
                        "error": "All extraction methods failed",
                        "extraction_method": "none"
                    })
                    print(f"  ✗ All extraction methods failed for page {page_num + 1}")
            
            has_valid = any(
                page.get('extraction_method') and page.get('extraction_method') != 'none'
                for page in extracted_data
            )
            
            return {
                "status": "success" if has_valid else "manual_review_needed",
                "pdf": file_path,
                "pages": extracted_data,
                "validated": has_valid
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "pdf": file_path
            }


def extract_invoice_enhanced(
    file_path: str, 
    api_key: Optional[str] = None,
    use_layoutlmv3: bool = True,
    use_ocr: bool = True,
    use_regex: bool = True
) -> Dict[str, Any]:
    extractor = EnhancedInvoiceExtractor(
        api_key=api_key,
        use_layoutlmv3=use_layoutlmv3,
        use_ocr=use_ocr,
        use_regex=use_regex
    )
    return extractor.extract_robust(file_path)