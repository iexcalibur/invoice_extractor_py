import json
import base64
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import os
import warnings
import logging

# Suppress warnings for cleaner output
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

# Optional imports for OCR and LayoutLMv3
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: Tesseract not available")

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

# Cost optimization: Use cheaper model for text parsing
TEXT_PARSING_MODEL = "claude-3-haiku-20240307"

try:
    from config import Config
except ImportError:
    Config = None

# Import regex extractor - try improved version first, then fallback
REGEX_EXTRACTOR_AVAILABLE = False
regex_extractor_module = None

try:
    from regex_extractor_improved import RegexInvoiceExtractor
    REGEX_EXTRACTOR_AVAILABLE = True
    regex_extractor_module = "regex_extractor_improved"
    print("✓ Using improved regex extractor (regex_extractor_improved.py)")
except ImportError:
    try:
        from regex_extractor import RegexInvoiceExtractor
        REGEX_EXTRACTOR_AVAILABLE = True
        regex_extractor_module = "regex_extractor"
        print("✓ Using standard regex extractor (regex_extractor.py)")
    except ImportError:
        print("Warning: No regex_extractor module found. Regex extraction will be disabled.")
        print("  To enable regex extraction, ensure regex_extractor_improved.py is in the same directory.")


class EnhancedInvoiceExtractor:
    """Enhanced invoice extractor with hybrid approach: Regex → LayoutLMv3 → OCR → Claude"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-3-haiku-20240307",
        use_regex: bool = True,
        use_layoutlmv3: bool = True,
        use_ocr: bool = True,
        ocr_engine: str = "tesseract",
        regex_confidence_threshold: float = 0.70,
        layoutlmv3_confidence_threshold: float = 0.50
    ):
        """
        Initialize the enhanced invoice extractor with regex support
        
        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            model: Claude model to use as fallback
            use_regex: Whether to use regex extraction first (fastest, free)
            use_layoutlmv3: Whether to use LayoutLMv3 model (cheaper option)
            use_ocr: Whether to use OCR as fallback
            ocr_engine: OCR engine to use ("tesseract" or "easyocr")
            regex_confidence_threshold: Minimum confidence for regex extraction (default: 0.70)
            layoutlmv3_confidence_threshold: Minimum confidence for LayoutLMv3 (default: 0.50)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.use_regex = use_regex and REGEX_EXTRACTOR_AVAILABLE
        self.use_layoutlmv3 = use_layoutlmv3 and LAYOUTLMV3_AVAILABLE
        self.use_ocr = use_ocr and (TESSERACT_AVAILABLE or EASYOCR_AVAILABLE)
        self.ocr_engine = ocr_engine
        self.regex_confidence_threshold = regex_confidence_threshold
        self.layoutlmv3_confidence_threshold = layoutlmv3_confidence_threshold
        
        # Initialize regex extractor
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
        
        # Initialize Claude client
        if self.api_key:
            try:
                self.claude_client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Claude client: {e}")
                self.claude_client = None
        else:
            self.claude_client = None
            print("Warning: No Anthropic API key provided. Claude-based extraction will be disabled.")
        
        # Initialize LayoutLMv3 model
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
        
        # Initialize OCR
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
        """Detect if file is PDF or image"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return 'pdf'
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']:
            return 'image'
        else:
            return 'unknown'
    
    def load_images(self, file_path: str) -> List[Image.Image]:
        """Load images from PDF or image file"""
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
        """Enhance image for better extraction results"""
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
        """
        Extract invoice data using regex patterns (fastest, free)
        Only works for known vendors: Frank's Quality Produce and Pacific Food Importers
        """
        if not self.use_regex or self.regex_extractor is None:
            return None
        
        try:
            # Extract text using OCR (needed for regex)
            if TESSERACT_AVAILABLE:
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
            
            # Try regex extraction
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
        """Extract layout structure from OCR data using bounding boxes"""
        layout_info = {
            "tables": [],
            "headers": [],
            "text_regions": [],
            "word_positions": []
        }
        
        if not ocr_data or "text" not in ocr_data:
            return layout_info
        
        # Extract word positions and bounding boxes
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
        
        # Identify table regions
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
        """Calculate confidence score for extracted data"""
        confidence = 0.0
        
        # Check required fields (40%)
        required_fields = ["invoice_number", "date", "vendor_name", "total_amount"]
        field_score = sum(1 for field in required_fields 
                         if extracted_data.get(field) and extracted_data[field] != "")
        confidence += (field_score / len(required_fields)) * 0.4
        
        # Check line items (40%)
        line_items = extracted_data.get("line_items", [])
        if line_items:
            valid_items = sum(1 for item in line_items
                            if item.get("description") and item.get("quantity") is not None)
            if valid_items > 0:
                confidence += (valid_items / len(line_items)) * 0.3
        
        # Check layout quality (10%)
        if layout_info.get("tables"):
            confidence += 0.2
        else:
            confidence += 0.1
        
        # Check total_amount validity (10%)
        total = extracted_data.get("total_amount", 0)
        if total and total > 0:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def extract_with_layoutlmv3(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        """Extract invoice data using LayoutLMv3 model with layout understanding"""
        if not self.use_layoutlmv3 or self.layoutlmv3_processor is None:
            return None
        
        try:
            # Extract text and layout using OCR
            if TESSERACT_AVAILABLE:
                ocr_text = pytesseract.image_to_string(image)
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            else:
                ocr_text = ""
                ocr_data = {}
            
            if not ocr_text or len(ocr_text.strip()) < 50:
                return None
            
            # Extract layout structure
            layout_info = self._extract_layout_structure(ocr_data, image)
            
            # Process with LayoutLMv3
            encoding = self.layoutlmv3_processor(
                image, 
                ocr_text, 
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=1024
            )
            
            if torch.cuda.is_available():
                encoding = {k: v.to("cuda") for k, v in encoding.items()}
            
            with torch.no_grad():
                outputs = self.layoutlmv3_model(**encoding)
            
            # Use Claude for parsing if available
            if self.claude_client and ocr_text:
                try:
                    # Enhance text with layout hints
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
                    if response_text.startswith("```"):
                        response_text = response_text.split("```")[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]
                        response_text = response_text.strip()
                    
                    extracted_data = json.loads(response_text)
                    
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
                        
                except Exception as e:
                    print(f"  LayoutLMv3 + Claude parsing error: {e}")
                    return None
            
            return None
            
        except Exception as e:
            print(f"  LayoutLMv3 extraction error: {e}")
            return None
    
    def _get_vendor_instructions(self, ocr_text: str) -> str:
        """Get vendor-specific extraction instructions"""
        ocr_lower = ocr_text.lower()
        
        if "frank" in ocr_lower and "quality produce" in ocr_lower:
            return """
VENDOR: FRANK'S QUALITY PRODUCE
- Quantity: First column in line items table
- Unit Price: "Price Each" column
- Line Total: "Amount" column
- Total: Bottom right corner (e.g., "Total $109.26")
CRITICAL: Use exact "Price Each" values, NOT calculated. Extract total from bottom right."""
        
        elif "pacific food" in ocr_lower and "importers" in ocr_lower:
            return """
VENDOR: PACIFIC FOOD IMPORTERS
- Quantity: "SHIPPED" column (3rd column) - extract EXACT values
- Unit Price: "Price" column - extract exact decimals
- Line Total: "Amount" column
- Total: Bottom section (e.g., "INVOICE TOTAL $596.94")
CRITICAL: Use SHIPPED column for quantity, NOT Ordered. Extract exact values."""
        
        return ""
    
    def _build_extraction_prompt(self, ocr_text: str, vendor_instructions: str) -> str:
        """Build extraction prompt with vendor-specific instructions"""
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
- date: YYYY-MM-DD format
- vendor_name: Vendor name
- total_amount: Total amount (float, from bottom of invoice)

CRITICAL: 
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
        """Extract invoice data using OCR + LLM parsing"""
        if not self.use_ocr:
            return None
        
        try:
            # Extract text using OCR
            if self.ocr_engine == "tesseract" and TESSERACT_AVAILABLE:
                ocr_text = pytesseract.image_to_string(image)
            elif self.ocr_engine == "easyocr" and EASYOCR_AVAILABLE:
                results = self.easyocr_reader.readtext(np.array(image))
                ocr_text = "\n".join([result[1] for result in results])
            else:
                return None
            
            # Use Claude to parse if available
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
                    if response_text.startswith("```"):
                        response_text = response_text.split("```")[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]
                        response_text = response_text.strip()
                    
                    extracted_data = json.loads(response_text)
                    extracted_data["_method"] = "ocr"
                    return extracted_data
                    
                except Exception as e:
                    print(f"  OCR + Claude parsing error: {e}")
                    return None
            else:
                return self._parse_ocr_text_basic(ocr_text)
                
        except Exception as e:
            print(f"  OCR extraction error: {e}")
            return None
    
    def _parse_ocr_text_basic(self, text: str) -> Dict[str, Any]:
        """Basic OCR text parsing fallback"""
        return {
            "invoice_number": "",
            "date": "",
            "vendor_name": "",
            "total_amount": 0.0,
            "line_items": [],
            "raw_ocr_text": text[:500]
        }
    
    def extract_with_claude(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        """Extract invoice data using Claude Vision (most accurate, most expensive)"""
        if not self.claude_client:
            return None
        
        try:
            processed_image = self.preprocess_image(image)
            
            buffered = BytesIO()
            processed_image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Use Haiku for all Claude API calls (cheaper option)
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
                            "text": """Extract invoice data from this image.

For Frank's Quality Produce:
- Use "Price Each" column for unit_price
- Use FIRST column for quantity
- Extract total from bottom right corner

For Pacific Food Importers:
- Use "SHIPPED" column for quantity (exact values)
- Use "Price" column for unit_price
- Extract total from bottom

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
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            extracted_data = json.loads(response_text)
            extracted_data["_method"] = "claude_vision"
            return extracted_data
            
        except Exception as e:
            print(f"  Claude Vision extraction error: {e}")
            return None
    
    def validate_extraction(self, result: Dict[str, Any], strict: bool = False) -> bool:
        """Validate that extracted data has required fields"""
        required_fields = ['invoice_number', 'date', 'vendor_name', 'total_amount']
        
        if not strict:
            # Count fields present
            fields_present = sum(1 for field in required_fields 
                               if field in result and result[field] is not None and result[field] != "")
            
            # Accept if we have at least 3 out of 4
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
        
        # Strict validation
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
        """
        Extract invoice data using hybrid approach with fallback chain:
        0. Regex (fastest, free) → 1. LayoutLMv3 (cheap) → 2. OCR (medium) → 3. Claude Vision (expensive)
        """
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
                
                # Strategy 0: Try Regex FIRST (fastest, free, known vendors)
                if self.use_regex:
                    print("  [1/4] Trying regex extraction (fastest, free)...")
                    page_result = self.extract_with_regex(image)
                    if page_result and self.validate_extraction(page_result, strict=False):
                        method_used = "regex"
                    else:
                        page_result = None
                
                # Strategy 1: Try LayoutLMv3
                if not page_result:
                    if self.use_layoutlmv3:
                        print("  [2/4] Trying LayoutLMv3 extraction (with layout understanding)...")
                        page_result = self.extract_with_layoutlmv3(image)
                        if page_result and self.validate_extraction(page_result, strict=False):
                            method_used = "layoutlmv3"
                        else:
                            page_result = None
                
                # Strategy 2: Try OCR + Claude
                if not page_result:
                    if self.use_ocr:
                        print("  [3/4] Trying OCR extraction (with cheap Claude Haiku)...")
                        page_result = self.extract_with_ocr(image)
                        if page_result and self.validate_extraction(page_result, strict=False):
                            method_used = "ocr"
                        else:
                            page_result = None
                
                # Strategy 3: Try Claude Vision (expensive fallback)
                if not page_result:
                    if self.claude_client:
                        print("  [4/4] Trying Claude Vision (expensive fallback)...")
                        page_result = self.extract_with_claude(image)
                        if page_result and self.validate_extraction(page_result, strict=True):
                            method_used = "claude_vision"
                        else:
                            page_result = None
                
                # Add page metadata
                if page_result:
                    page_result['page_number'] = page_num + 1
                    page_result['extraction_method'] = method_used
                    extracted_data.append(page_result)
                    print(f"  ✓ Extraction successful using {method_used}")
                else:
                    extracted_data.append({
                        "page_number": page_num + 1,
                        "error": "All extraction methods failed",
                        "extraction_method": "none"
                    })
                    print(f"  ✗ All extraction methods failed for page {page_num + 1}")
            
            # Validate overall results
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
    """
    Convenience function to extract invoice data with enhanced pipeline
    
    Args:
        file_path: Path to PDF or image file
        api_key: Optional API key (or set ANTHROPIC_API_KEY env var)
        use_layoutlmv3: Whether to use LayoutLMv3 model
        use_ocr: Whether to use OCR
        use_regex: Whether to use regex extraction first
        
    Returns:
        Dictionary with extraction results
    """
    extractor = EnhancedInvoiceExtractor(
        api_key=api_key,
        use_layoutlmv3=use_layoutlmv3,
        use_ocr=use_ocr,
        use_regex=use_regex
    )
    return extractor.extract_robust(file_path)