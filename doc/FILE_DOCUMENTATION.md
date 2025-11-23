# 📚 Invoice Extraction System - File Documentation

---

## 📋 Table of Contents

1. [Project Structure Overview](#project-structure-overview)
2. [Core Modules](#core-modules)
3. [Scripts & Utilities](#scripts--utilities)
4. [Tests & Evaluation](#tests--evaluation)
5. [Configuration Files](#configuration-files)
6. [Documentation Files](#documentation-files)
7. [Data & Output Directories](#data--output-directories)

---

## 🗂️ Project Structure Overview

```
invoice-extraction/
│
├── 📁 core/                          # Core extraction modules
│   ├── __init__.py                   # Package initialization
│   ├── config.py                     # Configuration management
│   ├── database.py                   # SQLite database interface
│   ├── invoice_extractor.py          # Main orchestrator (4-tier pipeline)
│   ├── regex_extractor.py            # Tier 1: Pattern-based extraction
│   ├── enhanced_ocr.py               # OCR preprocessing & enhancement
│   ├── ocr_corrector.py              # Post-OCR text correction
│   └── vendor_registry.py            # Vendor pattern registry system
│
├── 📁 tests/                         # Testing & evaluation
│   ├── evaluate_extraction.py        # Ground truth evaluation
│   ├── test_evaluation.py            # Automated test runner
│   └── ground_truth.json             # Manual verification data
│
├── 📁 scripts/                       # Utility scripts
│   ├── diagnose_extraction.py        # Debugging & diagnostics
│   └── empty_db.py                   # Database management
│
├── 📁 data/                          # Input directory (PDFs/images)
├── 📁 output/                        # Extraction results
│
├── main.py                           # CLI application
├── streamlit_app.py                  # Interactive dashboard
├── requirements.txt                  # Python dependencies
├── README.md                         # Project documentation
├── TRADE_OFFS_ANALYSIS.md            # Method comparison
├── Doc.md                            # Additional documentation
├── vendor_registry.json              # Vendor patterns (auto-generated)
├── invoices.db                       # SQLite database
└── .gitignore                        # Git ignore rules
```

---

## 🔧 Core Modules

### 1. `core/__init__.py`

**Purpose:** Package initialization file that makes `core/` a Python package.

**Contents:**
```python
"""
Core invoice extraction modules
"""

from .regex_extractor import RegexInvoiceExtractor
from .invoice_extractor import EnhancedInvoiceExtractor
from .database import InvoiceDatabase
from .config import Config

__all__ = [
    'RegexInvoiceExtractor',
    'EnhancedInvoiceExtractor',
    'InvoiceDatabase',
    'Config'
]
```

**Why It Exists:**
- Allows importing modules as `from core.invoice_extractor import EnhancedInvoiceExtractor`
- Provides clean package namespace
- Defines public API through `__all__`

**When to Edit:**
- When adding new core modules
- When changing public API exports

---

### 2. `core/config.py`

**Purpose:** Centralized configuration management for the entire extraction system.

**Key Features:**
- Environment variable management
- Model selection (Claude Opus/Sonnet/Haiku)
- Extraction strategy toggles (regex/LayoutLMv3/OCR/Vision)
- Confidence thresholds
- PDF/OCR settings
- Database configuration
- Validation rules

**Critical Settings:**
```python
# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

# Extraction Strategy
USE_REGEX = True          # Tier 1: Free, instant
USE_LAYOUTLMV3 = True     # Tier 2: Local, fast
USE_OCR = True            # Tier 3: Cheap Claude
USE_VISION = True         # Tier 4: Expensive fallback

# Confidence Thresholds
REGEX_CONFIDENCE_THRESHOLD = 0.60
LAYOUTLMV3_CONFIDENCE_THRESHOLD = 0.50
```

**Why It Exists:**
- **Single source of truth** for all settings
- Easy to modify extraction behavior
- Environment-specific configuration (.env support)
- Validation to catch misconfigurations early

**When to Edit:**
- Changing API keys
- Adjusting confidence thresholds
- Enabling/disabling extraction tiers
- Tuning OCR/PDF settings

**Usage:**
```python
from core.config import Config

# Get API key
api_key = Config.get_api_key()

# Check if valid
is_valid, errors = Config.validate()

# Print summary
Config.print_config()
```

---

### 3. `core/database.py`

**Purpose:** SQLite database interface for storing and querying invoice data.

**Database Schema:**

**Dimensional Model:**
```sql
-- DIMENSION TABLE: invoices
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    invoice_date DATE NOT NULL,
    total_amount REAL NOT NULL,
    extraction_method TEXT,
    confidence_score REAL,
    source_pdf_name TEXT,
    created_at TIMESTAMP
);

-- FACT TABLE: line_items
CREATE TABLE line_items (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER NOT NULL,  -- FK to invoices
    description TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    line_order INTEGER,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
```

**Key Features:**
- **Normalization:** Invoice number, vendor name, date
- **Validation:** Required fields, date formats, amounts
- **Duplicate detection:** Prevents re-inserting same invoice
- **Vendor registry integration:** Validates against vendor patterns
- **Query methods:** Get by ID, vendor, date range
- **Fact table queries:** Line items with joined dimensions

**Why It Exists:**
- **Persistent storage** of extracted data
- **Structured querying** (SQL)
- **Data integrity** through validation
- **Analytics support** (aggregations, filtering)
- **Dimensional modeling** for reporting

**When to Edit:**
- Adding new fields to schema
- Changing validation rules
- Adding new query methods
- Modifying vendor integration

**Usage:**
```python
from core.database import InvoiceDatabase

# Initialize
db = InvoiceDatabase("invoices.db")

# Save invoice
result = {"invoice_number": "378093", "vendor_name": "Pacific Food Importers", ...}
invoice_id = db.save_invoice(result, "invoice.pdf")

# Query
all_invoices = db.get_all_invoices()
vendor_invoices = db.get_invoices_by_vendor("Pacific")

# Close
db.close()
```

---

### 4. `core/invoice_extractor.py`

**Purpose:** Main orchestrator that implements the 4-tier hybrid extraction pipeline.

**Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│              EnhancedInvoiceExtractor                   │
│                                                         │
│  Tier 1: Regex Extraction (FREE, <0.1s)               │
│         ↓ (if confidence < 60%)                         │
│  Tier 2: LayoutLMv3 (FREE/local, ~2s)                 │
│         ↓ (if confidence < 50%)                         │
│  Tier 3: OCR + Claude Haiku ($0.01/invoice, ~5s)      │
│         ↓ (if failed)                                   │
│  Tier 4: Claude Vision ($0.05/invoice, ~10s)          │
└─────────────────────────────────────────────────────────┘
```

**Key Components:**

1. **Intelligent Fallback System:**
   - Tries cheapest method first
   - Falls back on failure
   - Uses confidence scores to decide

2. **Extraction Methods:**
   - `extract_with_regex()` - Pattern matching (Frank's, Pacific)
   - `extract_with_layoutlmv3()` - Document AI model
   - `extract_with_ocr()` - Tesseract/EasyOCR + Claude parsing
   - `extract_with_claude()` - Multimodal Vision API

3. **Validation:**
   - `validate_extraction()` - Check required fields
   - Vendor registry integration
   - Date format checking
   - Amount validation

4. **Vendor-Specific Instructions:**
   - `_get_vendor_instructions()` - Dynamic prompts
   - Uses vendor registry when available
   - Falls back to hardcoded rules

**Why It Exists:**
- **Cost optimization:** 92-96% savings vs pure Vision
- **Accuracy:** 100% F1 score through fallbacks
- **Flexibility:** Each tier can work independently
- **Maintainability:** Clear separation of concerns

**When to Edit:**
- Adding new extraction tiers
- Changing confidence thresholds
- Modifying vendor detection
- Updating Claude prompts

**Usage:**
```python
from core.invoice_extractor import EnhancedInvoiceExtractor

# Initialize
extractor = EnhancedInvoiceExtractor(
    api_key="your-key",
    use_regex=True,
    use_layoutlmv3=True,
    use_ocr=True
)

# Extract
result = extractor.extract_robust("invoice.pdf")

# Result structure
{
    "status": "success",
    "pages": [
        {
            "page_number": 1,
            "invoice_number": "378093",
            "vendor_name": "Pacific Food Importers",
            "date": "2025-07-15",
            "total_amount": 522.75,
            "line_items": [...],
            "extraction_method": "regex",
            "confidence_score": 0.95
        }
    ]
}
```

---

### 5. `core/regex_extractor.py`

**Purpose:** Tier 1 extraction using regex patterns for known vendor formats.

**Supported Vendors:**
1. **Frank's Quality Produce**
   - Invoice format: `2006XXXX` (8 digits starting with 2006)
   - Layout: Clean table format
   - Columns: Quantity | Description | Price Each | Amount

2. **Pacific Food Importers**
   - Invoice format: `37XXXX` (6 digits starting with 37)
   - Layout: Complex table with multiple columns
   - Columns: Product ID | Ordered | Shipped | Description | Price | Amount
   - **Critical:** Uses SHIPPED column (not ORDERED) for quantity

**Key Features:**
- **Fast:** <0.1s per invoice
- **Free:** No API costs
- **Accurate:** 100% for known formats
- **OCR correction:** Integrates `ocr_corrector` to fix common errors
- **Confidence scoring:** Calculates reliability (0.0-1.0)
- **Vendor detection:** Automatic vendor identification

**Pattern Examples:**
```python
# Frank's invoice number
r"Invoice\s*#?\s*:?\s*(2006\d{4})"

# Pacific invoice number (TOP RIGHT corner)
r"INVOICE[\s\n]+(\d{6})"

# Pacific date (after pipe separator)
r"INVOICE\s+DATE[\s\n|]+(\d{2})/(\d{2})/(\d{4})"

# Line item extraction
r"(\d+)\s+([A-Z][^\d\n]{3,}?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})"
```

**Why It Exists:**
- **Performance:** Orders of magnitude faster than ML/LLM
- **Cost:** Zero API costs for 80%+ of invoices
- **Reliability:** Deterministic, no model hallucinations
- **Specific formats:** Optimized for exact layouts

**When to Edit:**
- Adding new vendor patterns
- Fixing pattern matching issues
- Updating line item extraction
- Adjusting confidence calculation

**Usage:**
```python
from core.regex_extractor import RegexInvoiceExtractor

# Initialize
extractor = RegexInvoiceExtractor()

# Extract from OCR text
ocr_text = "Pacific Food Importers\nINVOICE 378093\n..."
result = extractor.extract(ocr_text, debug=True)

# Result includes confidence score
{
    "invoice_number": "378093",
    "vendor_name": "Pacific Food Importers",
    "date": "2025-07-15",
    "total_amount": 522.75,
    "line_items": [...],
    "_confidence": 0.95,
    "_method": "regex"
}
```

---

### 6. `core/enhanced_ocr.py`

**Purpose:** Pre-OCR image preprocessing to improve text recognition accuracy.

**Problem Solved:**
- Raw OCR often misreads text: "INVOICE" → "INVOKE", "TOTAL" → "T0TAL"
- Poor image quality causes character confusion
- Small text and noise reduce accuracy

**Enhancement Pipeline:**

```
Raw Image
    ↓
1. Upscaling (2x) - Increase resolution
    ↓
2. Denoising - Remove noise while preserving edges
    ↓
3. Adaptive Thresholding - Handle varying lighting
    ↓
4. Morphological Operations - Clean up text
    ↓
5. Sharpening - Make edges crisper
    ↓
Enhanced Image → Better OCR Results
```

**Technical Details:**
```python
def preprocess_invoice_image_enhanced(image: Image.Image) -> Image.Image:
    # 1. Upscale (2x resolution)
    upscaled = cv2.resize(gray, (width*2, height*2), interpolation=cv2.INTER_CUBIC)
    
    # 2. Denoise
    denoised = cv2.fastNlMeansDenoising(upscaled, h=10)
    
    # 3. Adaptive threshold
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, blockSize=11, C=2
    )
    
    # 4. Morphological closing
    kernel = np.ones((2, 2), np.uint8)
    morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # 5. Sharpen
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(morphed, -1, kernel_sharpen)
    
    return Image.fromarray(sharpened)
```

**Why It Exists:**
- **Root cause fix:** Improves OCR quality at the source
- **Better than patching:** More robust than correcting text after OCR
- **Universal benefit:** Helps all downstream processing
- **Debug support:** Optional debug mode saves intermediate images

**When to Edit:**
- Tuning preprocessing parameters
- Adding new enhancement techniques
- Handling specific image types
- Optimizing for different scanners

**Usage:**
```python
from core.enhanced_ocr import extract_text_with_enhanced_ocr
from PIL import Image

# Load image
image = Image.open("invoice.png")

# Extract with preprocessing
text = extract_text_with_enhanced_ocr(image, debug=True)

# Debug mode saves intermediate images:
# - debug_01_upscaled.png
# - debug_02_denoised.png
# - debug_03_binary.png
# - debug_04_morphed.png
# - debug_05_sharpened.png
```

---

### 7. `core/ocr_corrector.py`

**Purpose:** Post-OCR text correction to fix common character misreads.

**Problem Solved:**
OCR engines commonly confuse similar-looking characters:
- `INVOICE` → `INVOKE` (V instead of V+I)
- `TOTAL` → `T0TAL` (0 instead of O)
- `DATE` → `0ATE` (0 instead of D)
- `378093` → `37809B` (B instead of 3)

**Correction Strategies:**

1. **Word-Level Corrections:**
   ```python
   word_corrections = {
       "INVOKE": "INVOICE",
       "T0TAL": "TOTAL",
       "0ATE": "DATE",
       "CUST0MER": "CUSTOMER"
   }
   ```

2. **Context-Aware Corrections:**
   ```python
   # "INVOICE" should be followed by number or DATE
   r'\bINVOKE\s+(?:TOTAL|DATE|#|NO|\d)' → "INVOICE"
   
   # "TOTAL" should be preceded by INVOICE/SUB/GRAND
   r'(?:INVOICE|SUB|GRAND)\s+T0TAL' → "TOTAL"
   ```

3. **Character-Level Corrections:**
   ```python
   # Fix common confusions in invoice numbers
   r'\b([A-Z]+)([Ol])(\d{5,})\b'
   # Replace O→0, l→1 in numeric context
   ```

**Why It Exists:**
- **Catches systematic errors:** OCR engines make predictable mistakes
- **Maintainable:** Dictionary-based, easy to extend
- **Validates corrections:** Context-aware rules prevent false corrections
- **Improves regex matching:** Fixes text before pattern matching

**When to Edit:**
- Adding new common misreads
- Adjusting correction rules
- Handling vendor-specific terms
- Tuning context patterns

**Usage:**
```python
from core.ocr_corrector import OCRTextCorrector

# Initialize
corrector = OCRTextCorrector()

# Correct text
raw_ocr = "Pacific Food Importers\nINVOKE NO: 378093\nINVOKE TOTAL: $522.75"
corrected = corrector.correct_text(raw_ocr, debug=True)

# Output:
# "Pacific Food Importers\nINVOICE NO: 378093\nINVOICE TOTAL: $522.75"

# Validate
validation = corrector.validate_invoice_text(corrected)
# {
#     "has_invoice_keyword": True,
#     "has_total_keyword": True,
#     "no_invoke_misread": True,  # No "INVOKE" found
#     "all_passed": True
# }
```

**Integration:**
```python
# In regex_extractor.py
class RegexInvoiceExtractor:
    def __init__(self):
        self.corrector = OCRTextCorrector()
    
    def extract(self, ocr_text: str) -> Dict:
        # CRITICAL: Correct errors BEFORE regex
        corrected_text = self.corrector.correct_text(ocr_text)
        
        # Now use corrected text for pattern matching
        result = self.detect_vendor(corrected_text)
        ...
```

---

### 8. `core/vendor_registry.py`

**Purpose:** Centralized vendor pattern registry with learning capabilities.

**Key Concept:**
Instead of hardcoding vendor patterns throughout the codebase, maintain a **single source of truth** in JSON format that can be:
- Updated without code changes
- Learned from historical data
- Shared across team/deployments
- Version controlled

**Data Structure:**
```python
@dataclass
class VendorPattern:
    vendor_id: str                      # "pacific_food"
    vendor_name: str                    # "Pacific Food Importers"
    
    # Detection
    name_patterns: List[str]            # [r"pacific\s+food\s+importers?"]
    invoice_prefix_patterns: List[str]  # ["^37"]
    
    # Extraction hints
    invoice_number_location: str        # "top_right"
    invoice_number_label: str           # "INVOICE"
    
    # Validation rules
    invoice_number_regex: str           # r"^37\d{4}$"
    invoice_number_min_length: int      # 6
    invoice_number_max_length: int      # 6
    
    # Column mappings
    column_mappings: Dict[str, str]     # {"quantity": "SHIPPED"}
    
    # Learning data
    confidence: float                   # 1.0
    sample_count: int                   # 4
    last_updated: str                   # ISO timestamp
```

**Stored Format (`vendor_registry.json`):**
```json
{
  "pacific_food": {
    "vendor_id": "pacific_food",
    "vendor_name": "Pacific Food Importers",
    "invoice_prefix_patterns": ["^37"],
    "invoice_number_regex": "^37\\d{4}$",
    "column_mappings": {
      "quantity": "SHIPPED",
      "unit_price": "Price"
    },
    "notes": "Invoices start with 37 (370-379). Use SHIPPED column."
  }
}
```

**Key Features:**

1. **Vendor Detection:**
   ```python
   vendor = registry.detect_vendor(
       vendor_name="Pacific Food Importers",
       invoice_number="378093",
       ocr_text="...",
       debug=True
   )
   # Returns: VendorPattern for Pacific Food
   ```

2. **Validation:**
   ```python
   is_valid, error = registry.validate_invoice_number(
       "378093", vendor, debug=True
   )
   # Returns: (True, None)
   
   is_valid, error = registry.validate_invoice_number(
       "444509", vendor, debug=True
   )
   # Returns: (False, "Doesn't match pattern: ^37\d{4}$")
   ```

3. **Extraction Instructions:**
   ```python
   instructions = registry.get_extraction_instructions(vendor)
   # Returns formatted instructions for Claude prompts
   ```

4. **Learning:**
   ```python
   registry.learn_from_invoice(
       vendor_id="pacific_food",
       extracted_data={...},
       was_successful=True
   )
   # Updates confidence score and sample count
   ```

5. **Pattern Suggestion (ML):**
   ```python
   samples = [
       {"invoice_number": "AB12345"},
       {"invoice_number": "AB12346"},
       ...
   ]
   suggestion = registry.suggest_vendor_pattern(samples, "New Vendor")
   # Analyzes samples and suggests regex pattern
   ```

**Why It Exists:**
- **Scalability:** Add vendors without changing code
- **Maintainability:** One place to update patterns
- **Learning:** Automatically improves over time
- **Sharing:** JSON can be committed to Git
- **Flexibility:** Easy to experiment with patterns

**When to Edit:**
- Adding new vendors (use `add_vendor()` method)
- Updating validation rules
- Changing column mappings
- Adding pattern learning logic

**Usage:**
```python
from core.vendor_registry import get_vendor_registry

# Get global instance
registry = get_vendor_registry()

# Add new vendor
registry.add_vendor(
    vendor_id="sysco",
    vendor_name="Sysco Corporation",
    name_patterns=[r"sysco"],
    invoice_prefix_patterns=["^SC"],
    invoice_number_regex=r"^SC\d{6}$",
    invoice_number_length=(8, 8),
    column_mappings={"quantity": "Qty"}
)

# Use in extraction
vendor = registry.detect_vendor(vendor_name="Sysco Corp", invoice_number="SC123456")
if vendor:
    is_valid, _ = registry.validate_invoice_number("SC123456", vendor)
    instructions = registry.get_extraction_instructions(vendor)
```

---

## 🛠️ Scripts & Utilities

### 9. `scripts/diagnose_extraction.py`

**Purpose:** Comprehensive diagnostic tool to debug extraction failures.

**What It Checks:**

1. **File Existence & Accessibility:**
   - Verifies PDF exists
   - Checks file size
   - Validates file permissions

2. **PDF Conversion:**
   - Tests `pdf2image` conversion
   - Reports number of pages
   - Validates image dimensions

3. **OCR Quality:**
   - Extracts text with Tesseract
   - Checks text length
   - Searches for key terms (INVOICE, vendor name, amounts)

4. **Regex Extraction:**
   - Tests vendor detection
   - Runs extraction with debug mode
   - Reports confidence scores

5. **Database State:**
   - Lists existing invoices
   - Checks for duplicates
   - Shows current counts

6. **Common Issues:**
   - Verifies SHIPPED vs ORDERED column usage
   - Checks invoice number format
   - Validates line item extraction

**Output Example:**
```
================================================================================
INVOICE EXTRACTION DIAGNOSTICS
================================================================================

1. FILE CHECK
--------------------------------------------------------------------------------
✓ File exists: /path/to/invoice.pdf
✓ File size: 156.32 KB

2. PDF CONVERSION CHECK
--------------------------------------------------------------------------------
✓ PDF converted successfully
✓ Number of pages: 4
✓ Image size (first page): (1700, 2200)

3. OCR CHECK (Page 1)
--------------------------------------------------------------------------------
✓ OCR text length: 2847 chars

First 500 characters:
--------------------------------------------------------------------------------
Pacific Food Importers
INVOICE 378093
...
--------------------------------------------------------------------------------

Key terms found:
  ✓ INVOICE
  ✓ Pacific Food
  ✓ Invoice number 378093
  ✓ FLOUR POWER
  ✓ Total amount

4. REGEX EXTRACTION CHECK
--------------------------------------------------------------------------------
  [DEBUG] Vendor detected: pacific
✓ Regex extraction successful!
  Invoice #: 378093
  Date: 2025-07-15
  Total: $522.75
  Line items: 6
  Confidence: 95%

5. DATABASE CHECK
--------------------------------------------------------------------------------
Current invoices in database: 3

Existing invoice numbers:
  • 378094 - Pacific Food Importers - $75.08
  • 378206 - Pacific Food Importers - $95.23
  • 378262 - Pacific Food Importers - $95.23

6. COMMON ISSUES CHECK
--------------------------------------------------------------------------------
✓ Document has ORDERED and SHIPPED columns
  → Ensure extraction uses SHIPPED column for quantity
✓ First line item (FLOUR POWER) present in OCR
✓ Invoice number 378093 present in OCR

✓ No obvious issues detected

================================================================================
RECOMMENDATIONS
================================================================================

1. Empty the database first:
   python scripts/empty_db.py
   
2. Re-run extraction with debug mode:
   DEBUG_REGEX=true python main.py [pdf_file]
   
3. Check that regex patterns match Pacific Food Importers format
   
4. If regex fails, check LayoutLMv3/OCR fallback is working
   
5. Verify database save logic doesn't skip valid invoices
================================================================================
```

**Why It Exists:**
- **Debugging:** Quickly identify what's failing
- **Validation:** Verify entire pipeline end-to-end
- **Documentation:** Shows expected behavior
- **Troubleshooting:** Step-by-step diagnosis

**When to Use:**
- Extraction failing mysteriously
- Low accuracy on known formats
- Database not saving correctly
- OCR quality issues
- New vendor testing

**Usage:**
```bash
# Diagnose specific file
python scripts/diagnose_extraction.py

# Or edit PDF_PATH in the script to test different files
```

---

### 10. `scripts/empty_db.py`

**Purpose:** Database management utility to reset/clear invoice data.

**Features:**

1. **Interactive Menu:**
   ```
   1. Delete all data (keep schema) - RECOMMENDED
   2. Drop all tables (complete reset)
   3. Delete database file completely
   4. Show statistics only (no changes)
   5. Cancel
   ```

2. **Auto-Backup:**
   - Creates `invoices.db.backup` before any destructive operation
   - Allows recovery if mistake is made

3. **Statistics Display:**
   ```
   DATABASE STATISTICS
   ================================================================================
   
   Invoices: 127
     Total Amount: $45,234.56
     Unique Vendors: 3
     Date Range: 2025-07-01 to 2025-07-31
   
   Line Items: 542
   
   Database Size: 128.43 KB
   ================================================================================
   ```

4. **Safety Confirmations:**
   - Requires typing "yes" for destructive operations
   - Shows what will be deleted
   - Provides undo instructions

**Why It Exists:**
- **Testing:** Clean slate for re-running extractions
- **Development:** Reset during feature development
- **Maintenance:** Remove test/duplicate data
- **Safety:** Prevents accidental data loss

**When to Use:**
- Before re-extracting all invoices
- Testing new extraction logic
- Removing duplicate/invalid data
- Database corruption issues
- Development workflow

**Usage:**
```bash
# Interactive mode (recommended)
python scripts/empty_db.py

# Specify database path
python scripts/empty_db.py /path/to/invoices.db

# The script will:
# 1. Find the database
# 2. Show current statistics
# 3. Present interactive menu
# 4. Create backup before changes
# 5. Execute chosen operation
```

**Safety Features:**
- ✅ Auto-backup before any deletion
- ✅ Confirmation prompt for destructive actions
- ✅ Shows statistics before deletion
- ✅ Option to cancel at any time
- ✅ Preserves schema when deleting data only

---

## 🧪 Tests & Evaluation

### 11. `tests/evaluate_extraction.py`

**Purpose:** Automated evaluation system that compares extracted data against manually verified ground truth.

**What It Does:**

1. **Loads Ground Truth:**
   - Reads `ground_truth.json` (manually verified data)
   - Contains 4 invoices with 9 line items

2. **Fetches Extracted Data:**
   - Queries database for matching invoices
   - Retrieves all fields and line items

3. **Field-by-Field Comparison:**
   - Invoice number
   - Vendor name
   - Invoice date
   - Total amount
   - Line items count

4. **Calculates Metrics:**
   - **Precision:** True Positives / (True Positives + False Positives)
   - **Recall:** True Positives / (True Positives + False Negatives)
   - **F1 Score:** Harmonic mean of precision and recall
   - **Accuracy:** Correct extractions / Total extractions

5. **Detailed Error Analysis:**
   - Lists mismatches
   - Shows expected vs actual values
   - Identifies missing invoices

**Output Example:**
```
================================================================================
🔍 EVALUATING EXTRACTION ACCURACY
================================================================================

📋 Ground Truth File: ground_truth.json
📊 Total Invoices to Evaluate: 4

================================================================================
📊 EVALUATION RESULTS
================================================================================

📋 Summary:
   Total Invoices in Ground Truth: 4
   Successfully Evaluated: 4

--------------------------------------------------------------------------------
Field                     Precision    Recall      F1 Score    Accuracy    
--------------------------------------------------------------------------------
invoice_number             100.00%     100.00%     100.00%     100.00%
vendor_name                100.00%     100.00%     100.00%     100.00%
invoice_date               100.00%     100.00%     100.00%     100.00%
total_amount               100.00%     100.00%     100.00%     100.00%
line_items_count           100.00%     100.00%     100.00%     100.00%
--------------------------------------------------------------------------------
OVERALL AVERAGE            100.00%     100.00%     100.00%     100.00%
================================================================================

✅ NO ERRORS - Perfect extraction!

================================================================================

💾 Results saved to: evaluation_results.json
```

**Why It Exists:**
- **Quality Assurance:** Measure extraction accuracy objectively
- **Regression Testing:** Catch accuracy drops after changes
- **Benchmarking:** Compare different extraction methods
- **Documentation:** Prove system performance

**When to Use:**
- After making changes to extraction logic
- Before deploying to production
- When adding new vendors
- For performance reporting
- During development/testing

**Usage:**
```bash
# Run evaluation
python tests/evaluate_extraction.py

# Or from Python
from tests.evaluate_extraction import GroundTruthEvaluator

evaluator = GroundTruthEvaluator(
    db_path="invoices.db",
    gt_file="tests/ground_truth.json"
)

results = evaluator.evaluate()
evaluator.display_results(results)
evaluator.export_results(results)
```

**Metrics Explained:**

- **Precision:** Of the invoices we extracted, how many were correct?
  - Formula: `TP / (TP + FP)`
  - Perfect: 100% = No false positives

- **Recall:** Of the invoices we should extract, how many did we find?
  - Formula: `TP / (TP + FN)`
  - Perfect: 100% = No false negatives

- **F1 Score:** Balanced measure of precision and recall
  - Formula: `2 * (Precision * Recall) / (Precision + Recall)`
  - Perfect: 100% = Both precision and recall are perfect

- **Accuracy:** Overall correctness rate
  - Formula: `Correct / Total`
  - Perfect: 100% = All extractions correct

---

### 12. `tests/test_evaluation.py`

**Purpose:** Quick automated test runner wrapper around evaluation.

**What It Does:**
- Checks if required files exist
- Runs `evaluate_extraction.py`
- Displays summary results
- Handles errors gracefully

**Output Example:**
```
🚀 GROUND TRUTH EVALUATION - QUICK TEST

================================================================================
🔍 CHECKING REQUIRED FILES
================================================================================
✅ tests/ground_truth.json         - Ground truth data
✅ invoices.db                      - Invoice database
✅ tests/evaluate_extraction.py    - Evaluation script
================================================================================

✅ All files found! Running evaluation...

[... evaluation output ...]

✅ Evaluation completed successfully!

🎯 Quick Summary:
   Overall F1 Score: 100%
   Overall Accuracy: 100%
   Invoices Evaluated: 4/4
```

**Why It Exists:**
- **Convenience:** One-command testing
- **Validation:** Ensures prerequisites exist
- **Quick feedback:** Immediate results summary
- **Error handling:** Graceful failure messages

**Usage:**
```bash
python tests/test_evaluation.py
```

---

### 13. `tests/ground_truth.json`

**Purpose:** Manually verified "truth" data for 4 sample invoices.

**Structure:**
```json
{
  "_file": "Copy_of_ARPFIINVOEBTCHLASER__4_.pdf",
  "_description": "Ground truth data manually extracted from PDF",
  "_total_invoices": 4,
  
  "page_1": {
    "invoice_number": "378093",
    "vendor_name": "Pacific Food Importers",
    "date": "2025-07-15",
    "total_amount": 522.75,
    "line_items": [
      {
        "product_id": "102950",
        "description": "FLOUR POWER 50 LB GRAINCRAFT",
        "quantity": 12.0,
        "unit_price": 24.063,
        "line_total": 288.76
      },
      ...
    ],
    "line_items_count": 6
  },
  
  "page_2": { ... },
  "page_3": { ... },
  "page_4": { ... },
  
  "_summary": {
    "total_invoices": 4,
    "total_amount": 788.29,
    "total_line_items": 9,
    "vendor": "Pacific Food Importers",
    "invoice_numbers": ["378093", "378094", "378206", "378262"]
  }
}
```

**Why It Exists:**
- **Baseline:** Objective truth to measure against
- **Testing:** Validate extraction accuracy
- **Documentation:** Shows expected output format
- **Quality control:** Human-verified data

**When to Update:**
- Adding new test invoices
- Correcting errors in ground truth
- Expanding test coverage
- Adding new vendors

**How to Create:**
1. Select representative invoices
2. Manually extract all fields
3. Verify totals match
4. Double-check line items
5. Save in JSON format

---

## 📝 Configuration Files

### 14. `requirements.txt`

**Purpose:** Python package dependencies for the project.

**Categories:**

**Core Dependencies:**
```
anthropic>=0.18.0          # Claude API client
pdf2image>=1.16.3          # PDF to image conversion
Pillow>=10.0.0             # Image processing
pytesseract>=0.3.10        # OCR engine
opencv-python>=4.8.0       # Computer vision
```

**Machine Learning:**
```
transformers>=4.35.0       # LayoutLMv3
torch>=2.0.0               # PyTorch (ML framework)
torchvision>=0.15.0        # Vision models
```

**Data & Database:**
```
pandas>=2.0.0              # Data manipulation
numpy>=1.24.0              # Numerical operations
sqlite3                     # Database (built-in)
```

**Web Dashboard:**
```
streamlit>=1.28.0          # Interactive UI
plotly>=5.17.0             # Visualizations
```

**Utilities:**
```
python-dotenv>=1.0.0       # Environment variables
pathlib                     # Path handling (built-in)
```

**Why It Exists:**
- **Reproducibility:** Exact versions for consistent behavior
- **Installation:** One-command setup
- **Documentation:** Shows what the project needs

**Usage:**
```bash
# Install all dependencies
pip install -r requirements.txt

# Install in virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### 15. `.gitignore`

**Purpose:** Tells Git which files/folders to ignore (not commit).

**Recommended Contents:**
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Jupyter
.ipynb_checkpoints/
*.ipynb

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database (optional - commit if you want to share test data)
# invoices.db

# Auto-generated
vendor_registry.json

# OS
.DS_Store
Thumbs.db

# Output
output/
outputs/
Manual review/
```

**Why It Exists:**
- **Clean repository:** Only track source code
- **Security:** Don't commit API keys (.env)
- **Size:** Don't commit generated files
- **Privacy:** Don't commit local configurations

**When to Edit:**
- Adding new temporary directories
- Excluding large generated files
- Protecting sensitive data

---

### 16. `vendor_registry.json`

**Purpose:** Auto-generated JSON file storing vendor patterns.

**Generated By:** `core/vendor_registry.py` on first run

**Contents:**
```json
{
  "pacific_food": {
    "vendor_id": "pacific_food",
    "vendor_name": "Pacific Food Importers",
    "name_patterns": [
      "pacific\\s+food\\s+importers?",
      "pacific\\s+food"
    ],
    "invoice_prefix_patterns": ["^37"],
    "invoice_number_regex": "^37\\d{4}$",
    "invoice_number_min_length": 6,
    "invoice_number_max_length": 6,
    "column_mappings": {
      "quantity": "SHIPPED",
      "unit_price": "Price",
      "line_total": "Amount",
      "description": "DESCRIPTION"
    },
    "confidence": 1.0,
    "sample_count": 4,
    "last_updated": "2025-11-24T01:39:27.583836",
    "notes": "Invoices start with 37 (370-379). Use SHIPPED column."
  },
  "franks": { ... }
}
```

**Why It Exists:**
- **Persistence:** Saves vendor patterns between runs
- **Sharing:** Can be committed to Git
- **Learning:** Updates automatically based on success/failure
- **Human-editable:** Can manually tweak patterns

**When to Edit:**
- Manually: Adjust regex patterns, column mappings
- Programmatically: Use `vendor_registry.add_vendor()`
- Learning: Automatic updates via `learn_from_invoice()`

**Should You Commit It?**
- **Yes:** Share patterns across team
- **No:** If patterns are environment-specific

---

### 17. `invoices.db`

**Purpose:** SQLite database storing extracted invoice data.

**Created By:** `core/database.py` on first run

**Contents:**
- **invoices** table: 127 rows (example)
- **line_items** table: 542 rows (example)

**Schema:**
```sql
-- Invoices
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    invoice_number TEXT UNIQUE,
    vendor_name TEXT,
    invoice_date DATE,
    total_amount REAL,
    extraction_method TEXT,
    confidence_score REAL,
    source_pdf_name TEXT,
    created_at TIMESTAMP
);

-- Line Items
CREATE TABLE line_items (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER,
    description TEXT,
    quantity REAL,
    unit_price REAL,
    line_total REAL,
    line_order INTEGER,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
```

**Why It Exists:**
- **Persistence:** Store extraction results permanently
- **Querying:** SQL queries for filtering/aggregation
- **Analytics:** Power the Streamlit dashboard
- **Portability:** Single file, easy to backup/share

**Should You Commit It?**
- **No (usually):** Contains processed data, can be regenerated
- **Maybe:** If you want to share test data with team

**Management:**
```bash
# View database
sqlite3 invoices.db "SELECT * FROM invoices LIMIT 5;"

# Backup
cp invoices.db invoices_backup.db

# Empty
python scripts/empty_db.py

# Delete
rm invoices.db  # Will be recreated on next run
```

---

## 🚀 Main Applications

### 18. `main.py`

**Purpose:** Command-line interface (CLI) for batch invoice processing.

**Features:**

1. **Single File Processing:**
   ```bash
   python main.py invoice.pdf
   python main.py invoice.png
   ```

2. **Batch Processing:**
   ```bash
   # Process directory
   python main.py data/

   # Recursive
   python main.py data/ -r

   # Custom output
   python main.py data/ -o results/
   ```

3. **Database Integration:**
   ```bash
   # Auto-save to database (default)
   python main.py invoice.pdf

   # Skip database
   python main.py invoice.pdf --no-db

   # Custom database
   python main.py invoice.pdf --db my_invoices.db
   ```

4. **API Key Options:**
   ```bash
   # From environment
   export ANTHROPIC_API_KEY="your-key"
   python main.py invoice.pdf

   # From command line
   python main.py invoice.pdf --api-key "your-key"

   # From .env file
   echo "ANTHROPIC_API_KEY=your-key" > .env
   python main.py invoice.pdf
   ```

**Output:**
```
============================================================
Processing: data/invoice_378093.pdf
============================================================

Converting PDF to images: invoice_378093.pdf (DPI: 200)

Processing page 1/1...
  [1/4] Trying regex extraction (fastest, free)...
  ✓ Regex extraction successful (confidence: 95%)

✓ Extraction successful!

  Page 1:
    Invoice #: 378093
    Date: 2025-07-15
    Vendor: Pacific Food Importers
    Total: $522.75
    Line Items: 6

✓ Saved to database: 1 invoice(s)
    Invoice ID: 127 (#378093)

✓ Results saved to: outputs/invoice_378093_extracted.json
```

**Why It Exists:**
- **Automation:** Process invoices without UI
- **Batch operations:** Handle hundreds of files
- **Scripting:** Integrate into workflows
- **CI/CD:** Automated testing/processing

**Usage Examples:**
```bash
# Basic usage
python main.py invoice.pdf

# Process directory with stats
python main.py data/ --stats

# Export to CSV
python main.py data/ --export-csv

# Recursive with custom output
python main.py data/ -r -o results/ --export-csv

# Debug mode (set before running)
DEBUG_REGEX=true python main.py invoice.pdf
```

---

### 19. `streamlit_app.py`

**Purpose:** Interactive web dashboard for invoice management and analytics.

**Features:**

**1. Upload & Extract Tab:**
- Drag-and-drop file upload
- Batch processing
- Real-time extraction progress
- Result visualization
- Manual review workflow (download/move failed extractions)
- Extract from `data/` folder

**2. Database Browser Tab:**
- View all invoices
- Filter by vendor, date, extraction method
- Line items viewer
- Export to CSV/JSON
- Empty database button
- Summary statistics

**3. Analytics Tab:**
- Time series charts (invoices over time)
- Spend by vendor (bar chart)
- Extraction methods distribution (pie chart)
- Summary statistics (avg, median, min, max, std dev)

**4. Evaluation Tab:**
- Method performance comparison
- Cost optimization analysis
- Accuracy metrics display
- Savings calculator

**5. About Tab:**
- System documentation
- Architecture overview
- Performance metrics
- Tech stack information

**UI Features:**
- **Responsive design:** Works on desktop/mobile
- **Clean interface:** Minimal, professional look
- **Real-time updates:** Database refreshes automatically
- **Error handling:** Graceful failure messages
- **Progress tracking:** Visual feedback during processing

**Why It Exists:**
- **User-friendly:** Non-technical users can process invoices
- **Exploration:** Browse and analyze data visually
- **Management:** Centralized invoice operations
- **Demonstration:** Showcase system capabilities

**Usage:**
```bash
# Start dashboard
streamlit run streamlit_app.py

# Open browser at http://localhost:8501

# Custom port
streamlit run streamlit_app.py --server.port 8080

# Server mode (accessible externally)
streamlit run streamlit_app.py --server.address 0.0.0.0
```

**Configuration:**
- Page title: "Invoice Extraction Dashboard"
- Layout: Wide
- Icon: 📄
- Sidebar: Hidden (using tabs instead)

---

## 📖 Documentation Files

### 20. `README.md`

**Purpose:** Main project documentation and entry point.

**Contents:**
1. **Overview:** High-level system description
2. **Quick Start:** Installation and usage
3. **Performance Metrics:** Accuracy, cost, speed
4. **Project Structure:** File organization
5. **Configuration:** Settings and options
6. **API Documentation:** CLI and Python usage
7. **Testing:** How to run tests
8. **Technical Details:** Data formats, schema
9. **Key Innovations:** What makes this special
10. **Scalability:** Production deployment
11. **Limitations:** Current constraints
12. **Future Work:** Planned enhancements

**Why It Exists:**
- **Onboarding:** Help new users get started
- **Reference:** Quick lookup for features
- **Marketing:** Showcase capabilities
- **Documentation:** Centralized knowledge

**Should Be Updated When:**
- Adding new features
- Changing usage patterns
- Updating dependencies
- Modifying architecture

---

### 21. `TRADE_OFFS_ANALYSIS.md`

**Purpose:** Detailed comparison of extraction methods with trade-off analysis.

**Contents:**
1. **Method Comparison:** Regex vs LayoutLMv3 vs OCR vs Vision
2. **Cost Analysis:** Detailed cost breakdowns
3. **Speed Benchmarks:** Performance measurements
4. **Accuracy Comparison:** Method-specific F1 scores
5. **Use Case Recommendations:** When to use each method
6. **Hybrid Strategy Justification:** Why 4-tier approach
7. **Scaling Considerations:** Production implications

**Why It Exists:**
- **Justification:** Explain design decisions
- **Education:** Help others understand trade-offs
- **Reference:** Guide for similar projects
- **Technical depth:** Deep dive into architecture

---

### 22. `Doc.md`

**Purpose:** Additional documentation (purpose unclear from filename).

**Recommended Contents:**
- Implementation notes
- Design decisions
- API changes log
- Migration guides
- Advanced usage examples

---

## 📂 Data & Output Directories

### 23. `data/`

**Purpose:** Input directory for invoice files (PDFs and images).

**Structure:**
```
data/
├── invoice_378093.pdf
├── invoice_378094.pdf
├── frank_20065629.pdf
└── invoices/
    ├── 2025-07/
    │   ├── invoice_001.pdf
    │   └── invoice_002.pdf
    └── 2025-08/
        └── invoice_003.pdf
```

**Supported Formats:**
- PDF (`.pdf`)
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- TIFF (`.tiff`, `.tif`)
- BMP (`.bmp`)
- GIF (`.gif`)

**Usage:**
```bash
# Process all files in data/
python main.py data/

# Process recursively
python main.py data/ -r
```

**Why It Exists:**
- **Organization:** Centralized input location
- **Batch processing:** Process multiple files easily
- **Testing:** Store test invoices
- **Production:** Incoming invoice drop folder

---

### 24. `output/` or `outputs/`

**Purpose:** Extraction results (JSON files, CSV exports).

**Note:** README says `outputs/` (plural), actual folder is `output/` (singular) - should be standardized.

**Structure:**
```
output/
├── json/
│   ├── invoice_378093_extracted.json
│   ├── invoice_378094_extracted.json
│   └── frank_20065629_extracted.json
└── csv/
    ├── invoices_export_20251124.csv
    └── pacific_food_invoices.csv
```

**Contents:**
- Extracted invoice data (JSON)
- CSV exports from database
- Processing logs
- Error reports

**Why It Exists:**
- **Results storage:** Keep extraction outputs
- **Backup:** Preserve JSON for re-import
- **Sharing:** Export data for other systems
- **Archival:** Historical extraction records

---

### 25. `Manual review/`

**Purpose:** Failed extractions requiring human review.

**Auto-Created By:** Streamlit dashboard when extraction fails

**Structure:**
```
Manual review/
├── invoice_xyz_1.pdf
├── invoice_xyz_1.json
├── invoice_abc_2.pdf
└── invoice_abc_2.json
```

**Contents:**
- Original PDF/image file
- Extraction attempt results (JSON)
- Partial extraction data
- Error details

**Why It Exists:**
- **Workflow:** Separate failed extractions
- **Human review:** Manual data entry queue
- **Quality control:** Catch edge cases
- **Learning:** Analyze failures to improve system

---

## 🎯 Usage Scenarios

### Scenario 1: First-Time Setup
```bash
# 1. Clone/download project
git clone <repo-url>
cd invoice-extraction

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Tesseract (if not installed)
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
# Windows: Download from GitHub

# 5. Set API key
export ANTHROPIC_API_KEY="your-key-here"
# Or create .env file

# 6. Test with sample invoice
python main.py data/sample_invoice.pdf

# 7. View results
cat output/sample_invoice_extracted.json

# 8. Launch dashboard
streamlit run streamlit_app.py
```

### Scenario 2: Batch Processing
```bash
# Process all invoices in data/
python main.py data/ -o results/ --export-csv

# Check results
ls results/json/
ls results/csv/

# View database
sqlite3 invoices.db "SELECT COUNT(*) FROM invoices;"
```

### Scenario 3: Debugging Failed Extraction
```bash
# 1. Run diagnostics
python scripts/diagnose_extraction.py

# 2. Enable debug mode
DEBUG_REGEX=true python main.py problematic_invoice.pdf

# 3. Check OCR quality
# (diagnose_extraction.py shows OCR text)

# 4. Review regex patterns
# Edit core/regex_extractor.py if needed

# 5. Test with specific tier
# Modify core/config.py to disable tiers

# 6. Manual review
# Check Manual review/ folder in dashboard
```

### Scenario 4: Adding New Vendor
```python
# Method 1: Using vendor registry (recommended)
from core.vendor_registry import get_vendor_registry

registry = get_vendor_registry()
registry.add_vendor(
    vendor_id="new_vendor",
    vendor_name="New Vendor Inc",
    name_patterns=[r"new\s+vendor"],
    invoice_prefix_patterns=["^NV"],
    invoice_number_regex=r"^NV\d{6}$",
    invoice_number_length=(8, 8),
    column_mappings={"quantity": "Qty"}
)

# Method 2: Using pattern suggestion
samples = [
    {"invoice_number": "NV123456"},
    {"invoice_number": "NV123457"}
]
suggestion = registry.suggest_vendor_pattern(samples, "New Vendor Inc")
# Review suggestion and add manually
```

### Scenario 5: Running Tests
```bash
# 1. Ensure database has test data
python main.py data/test_invoices/ --db test_invoices.db

# 2. Run evaluation
python tests/evaluate_extraction.py

# 3. Check results
cat evaluation_results.json

# 4. Quick test
python tests/test_evaluation.py
```

---

## 🔍 Quick Reference

### Important File Locations

| What | Where | Why |
|------|-------|-----|
| Main CLI | `main.py` | Process invoices from command line |
| Dashboard | `streamlit_app.py` | Interactive web UI |
| Config | `core/config.py` | All settings in one place |
| Database | `invoices.db` | Extracted data storage |
| Input files | `data/` | Place PDFs/images here |
| Results | `output/` | Extracted JSON/CSV files |
| Tests | `tests/` | Evaluation & ground truth |
| Diagnostics | `scripts/diagnose_extraction.py` | Debug extraction issues |
| Vendor patterns | `vendor_registry.json` | Auto-generated, editable |

### Key Commands

```bash
# Process single invoice
python main.py invoice.pdf

# Process directory
python main.py data/

# Launch dashboard
streamlit run streamlit_app.py

# Run evaluation
python tests/evaluate_extraction.py

# Debug extraction
python scripts/diagnose_extraction.py

# Empty database
python scripts/empty_db.py
```

### Configuration Quick Edit

```python
# core/config.py

# Enable/disable extraction tiers
USE_REGEX = True          # Fast, free
USE_LAYOUTLMV3 = True     # Local ML
USE_OCR = True            # OCR + Claude
USE_VISION = True         # Vision API

# Adjust confidence thresholds
REGEX_CONFIDENCE_THRESHOLD = 0.60
LAYOUTLMV3_CONFIDENCE_THRESHOLD = 0.50

# Change models
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
TEXT_PARSING_MODEL = "claude-3-haiku-20240307"
```

---

## 📞 Support & Troubleshooting

### Common Issues

**1. "ANTHROPIC_API_KEY not set"**
```bash
# Solution
export ANTHROPIC_API_KEY="your-key"
# Or create .env file
```

**2. "Tesseract not found"**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

**3. "LayoutLMv3 model error"**
```python
# Disable LayoutLMv3 in config.py
USE_LAYOUTLMV3 = False
```

**4. "Database locked"**
```bash
# Close all connections
python scripts/empty_db.py
# Select option 4 (show stats only)
```

**5. "Invoice not extracted"**
```bash
# Run diagnostics
python scripts/diagnose_extraction.py

# Enable debug mode
DEBUG_REGEX=true python main.py invoice.pdf
```

---

## 🎓 Learning Path

**For New Users:**
1. Read `README.md` - Overview and quick start
2. Run `main.py` with sample invoice
3. Launch `streamlit_app.py` to see dashboard
4. Read this file (`FILE_DOCUMENTATION.md`) for details

**For Developers:**
1. Read `core/config.py` - Understand settings
2. Study `core/invoice_extractor.py` - Main logic
3. Review `core/regex_extractor.py` - Pattern extraction
4. Read `TRADE_OFFS_ANALYSIS.md` - Design decisions
5. Explore `tests/evaluate_extraction.py` - Testing

**For Contributors:**
1. Understand vendor registry (`core/vendor_registry.py`)
2. Learn error correction (`core/ocr_corrector.py`)
3. Study database schema (`core/database.py`)
4. Review diagnostics (`scripts/diagnose_extraction.py`)

---

## 📝 Maintenance Checklist

**Daily/Weekly:**
- [ ] Monitor extraction success rate
- [ ] Review `Manual review/` folder
- [ ] Check database size (`invoices.db`)
- [ ] Verify API costs

**Monthly:**
- [ ] Run evaluation tests
- [ ] Update vendor patterns if needed
- [ ] Review and clean test data
- [ ] Backup `invoices.db`

**Before Deployment:**
- [ ] Run full test suite
- [ ] Update `requirements.txt`
- [ ] Review `config.py` settings
- [ ] Update documentation
- [ ] Create database backup

**After Major Changes:**
- [ ] Re-run evaluation
- [ ] Update `TRADE_OFFS_ANALYSIS.md`
- [ ] Test with real invoices
- [ ] Update `README.md` if needed

---

## 🎉 Summary

This invoice extraction system consists of **25+ files** organized into:

- **8 Core Modules** - Extraction pipeline, database, config
- **2 Main Applications** - CLI and dashboard
- **5 Utility Scripts** - Diagnostics, testing, management
- **4 Test Files** - Evaluation and ground truth
- **6+ Config/Doc Files** - Settings, documentation, patterns

**Key Design Principles:**
1. **Modularity** - Each file has a single, clear purpose
2. **Configurability** - Settings in one place (`config.py`)
3. **Testability** - Comprehensive evaluation framework
4. **Maintainability** - Clear documentation, clean code
5. **Extensibility** - Easy to add vendors, methods

**Most Important Files to Understand:**
1. `core/invoice_extractor.py` - Main orchestrator
2. `core/config.py` - Configuration hub
3. `core/database.py` - Data persistence
4. `core/vendor_registry.py` - Pattern management
5. `main.py` - CLI interface
6. `streamlit_app.py` - Web interface

**Start Here:**
- **New users:** `README.md` → `main.py`
- **Developers:** `core/config.py` → `core/invoice_extractor.py`
- **Contributors:** This file → `TRADE_OFFS_ANALYSIS.md`

---

**Built with ❤️ for intelligent document processing**

*Last updated: November 2024*
