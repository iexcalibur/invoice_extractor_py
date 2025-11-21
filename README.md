# Invoice Extraction System

A comprehensive invoice data extraction system that uses a hybrid approach combining multiple extraction methods: Regex patterns, LayoutLMv3, OCR, and Claude AI. The system is optimized for extracting structured data from PDF and image invoices, with special support for Frank's Quality Produce and Pacific Food Importers.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Setup](#setup)
- [Running the Project](#running-the-project)
- [File Structure](#file-structure)
- [Data Flow](#data-flow)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)

## Features

- **Multi-Method Extraction**: Hybrid approach with 4 extraction strategies
  - Regex-based extraction (fastest, free, vendor-specific)
  - LayoutLMv3 model (layout-aware, cost-effective)
  - OCR + Claude Haiku (text parsing with AI)
  - Claude Vision API (expensive fallback for complex invoices)
- **Multi-Format Support**: PDF and image files (PNG, JPG, TIFF, BMP, GIF)
- **Database Storage**: SQLite database for persistent invoice storage
- **Validation**: Automatic validation of extracted data
- **Confidence Scoring**: Confidence metrics for each extraction
- **Batch Processing**: Process single files or entire directories

## Architecture

### System Overview

The system follows a **cascading fallback architecture** where multiple extraction methods are tried in sequence until one succeeds:

```
Input (PDF/Image)
    ↓
[1] Regex Extraction (Fastest, Free)
    ├─ Success? → Return Result
    └─ Fail? → Continue
        ↓
[2] LayoutLMv3 Extraction (Layout-Aware ML)
    ├─ Success? → Return Result
    └─ Fail? → Continue
        ↓
[3] OCR + Claude Haiku (Text Parsing)
    ├─ Success? → Return Result
    └─ Fail? → Continue
        ↓
[4] Claude Vision API (Expensive Fallback)
    ├─ Success? → Return Result
    └─ Fail? → Return Error
```

### Extraction Methods

1. **Regex Extraction** (`regex_extractor.py`)
   - Fastest method (no API calls)
   - Vendor-specific patterns for known vendors
   - Currently supports: Frank's Quality Produce, Pacific Food Importers
   - Confidence threshold: 70% (configurable)

2. **LayoutLMv3 Extraction** (`invoice_extractor.py`)
   - Uses Microsoft's LayoutLMv3 model for document understanding
   - Understands document layout and structure
   - Requires transformers library and model download
   - Confidence threshold: 50% (configurable)

3. **OCR + Claude Haiku** (`invoice_extractor.py`)
   - Uses Tesseract or EasyOCR for text extraction
   - Sends extracted text to Claude Haiku for parsing
   - Cost-effective AI parsing
   - Works with any invoice format

4. **Claude Vision API** (`invoice_extractor.py`)
   - Direct image analysis using Claude Vision
   - Most expensive but most flexible
   - Handles complex layouts and handwritten text

## Setup

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR (for OCR functionality)
- poppler-utils (for PDF to image conversion)

### Installation Steps

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/Invoices
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install system dependencies:**

   **macOS:**
   ```bash
   brew install tesseract poppler
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install tesseract-ocr poppler-utils
   ```

   **Windows:**
   - Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
   - Download Poppler from: https://github.com/oschwartz10612/poppler-windows/releases
   - Add to PATH

5. **Set up Anthropic API Key (optional but recommended):**
   
   Create a `.env` file in the project root:
   ```bash
   ANTHROPIC_API_KEY=your_api_key_here
   ```
   
   Or set as environment variable:
   ```bash
   export ANTHROPIC_API_KEY=your_api_key_here
   ```

   **Note:** The system can work without an API key, but Claude-based extraction methods will be disabled.

6. **Download LayoutLMv3 model (optional):**
   
   The model will be automatically downloaded on first use if `transformers` is installed. This requires ~500MB disk space.

## Running the Project

### Basic Usage

**Process a single invoice:**
```bash
python main.py invoice.pdf
```

**Process all invoices in a directory:**
```bash
python main.py data/
```

**Process recursively with custom output:**
```bash
python main.py data/ -o results/ -r
```

**Process without database storage:**
```bash
python main.py invoice.pdf --no-db
```

**Process with custom database:**
```bash
python main.py invoice.pdf --db custom_invoices.db
```

### Command Line Options

```bash
python main.py [INPUT] [OPTIONS]

Arguments:
  INPUT                 PDF/image file or directory containing invoices

Options:
  -o, --output DIR      Output directory for JSON results (default: output)
  -r, --recursive       Process files recursively in subdirectories
  --api-key KEY        Anthropic API key (or set ANTHROPIC_API_KEY env var)
  --db PATH            SQLite database file path (default: invoices.db)
  --no-db              Disable database saving (only save JSON files)
```

### Using Jupyter Notebook

For interactive analysis and visualization:

```bash
jupyter notebook invoice_dashboard.ipynb
```

The notebook provides:
- Interactive invoice processing
- Data visualization
- Database queries
- Analysis tools

## File Structure

### Core Files

| File | Purpose | Key Components |
|------|---------|----------------|
| `main.py` | Entry point and CLI | Argument parsing, file processing, batch operations |
| `invoice_extractor.py` | Main extraction engine | `EnhancedInvoiceExtractor` class, hybrid extraction pipeline |
| `regex_extractor.py` | Regex-based extraction | `RegexInvoiceExtractor` class, vendor-specific patterns |
| `database.py` | Database operations | `InvoiceDatabase` class, SQLite schema, data normalization |
| `config.py` | Configuration management | `Config` class, environment variables, settings |

### Supporting Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python package dependencies |
| `invoice_dashboard.ipynb` | Jupyter notebook for interactive analysis |
| `invoices.db` | SQLite database (created automatically) |
| `data/` | Directory for input invoice files |
| `output/` | Directory for extracted JSON results |

### Detailed File Descriptions

#### `main.py`
- **Purpose**: Command-line interface and orchestration
- **Key Functions**:
  - `process_single_file()`: Process one invoice file
  - `process_directory()`: Batch process multiple files
  - `main()`: CLI argument parsing and execution
- **Responsibilities**:
  - File discovery and validation
  - Extractor initialization
  - Result saving (JSON + Database)
  - Progress reporting

#### `invoice_extractor.py`
- **Purpose**: Core extraction engine with hybrid approach
- **Key Class**: `EnhancedInvoiceExtractor`
- **Key Methods**:
  - `extract_robust()`: Main extraction method with fallback chain
  - `extract_with_regex()`: Regex-based extraction
  - `extract_with_layoutlmv3()`: LayoutLMv3 model extraction
  - `extract_with_ocr()`: OCR + Claude text parsing
  - `extract_with_claude()`: Claude Vision API extraction
  - `validate_extraction()`: Data validation
  - `load_images()`: PDF/image loading and preprocessing
- **Responsibilities**:
  - Image preprocessing (CLAHE, denoising)
  - Multi-method extraction orchestration
  - Confidence calculation
  - Layout structure analysis

#### `regex_extractor.py`
- **Purpose**: Fast, vendor-specific regex extraction
- **Key Class**: `RegexInvoiceExtractor`
- **Key Methods**:
  - `detect_vendor()`: Identify vendor from text
  - `extract()`: Extract invoice data using regex patterns
- **Supported Vendors**:
  - Frank's Quality Produce
  - Pacific Food Importers
- **Responsibilities**:
  - Vendor detection
  - Pattern matching for invoice fields
  - Line item extraction
  - Confidence scoring

#### `database.py`
- **Purpose**: SQLite database operations
- **Key Class**: `InvoiceDatabase`
- **Database Schema**:
  - `invoices` table: Invoice metadata and fields
  - `line_items` table: Individual line items with foreign key
- **Key Methods**:
  - `save_invoice()`: Save single invoice
  - `save_extraction_result()`: Save multi-page extraction results
  - `get_invoice()`: Retrieve invoice by ID
  - `get_all_invoices()`: Query all invoices
  - `validate_invoice()`: Data validation
- **Responsibilities**:
  - Data normalization (vendor names, dates, amounts)
  - Duplicate detection (unique constraint on invoice_number + vendor + date)
  - Data validation
  - Relationship management (invoices ↔ line_items)

#### `config.py`
- **Purpose**: Configuration management
- **Key Class**: `Config`
- **Configuration Options**:
  - API keys (Anthropic)
  - Model selection
  - PDF processing settings (DPI, format)
  - Image preprocessing parameters
  - Output settings
- **Responsibilities**:
  - Environment variable loading (.env support)
  - Configuration validation
  - Default value management

## Data Flow

### Complete Extraction Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT: PDF/Image File                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              main.py: process_single_file()                  │
│  - Validates file                                            │
│  - Initializes EnhancedInvoiceExtractor                      │
│  - Calls extract_robust()                                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│      invoice_extractor.py: extract_robust()                 │
│  - Loads images from PDF/image                               │
│  - Preprocesses images (CLAHE, denoising)                   │
│  - For each page, tries extraction methods in order:         │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Method 1:  │ │   Method 2:  │ │   Method 3:  │
│    Regex     │ │  LayoutLMv3  │ │  OCR+Claude  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       │                │                │
       └────────┬───────┴────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│              Validation & Confidence Scoring                 │
│  - validate_extraction() checks required fields              │
│  - _calculate_confidence() scores extraction quality         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Result Assembly                          │
│  - Combines page results                                     │
│  - Adds metadata (method, confidence, page numbers)          │
│  - Returns structured JSON                                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Save JSON   │ │  Save to DB  │ │  Print       │
│  to output/  │ │  (if enabled) │ │  Summary     │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Detailed Method Flow

#### Regex Extraction Flow
```
Image → OCR (Tesseract/EasyOCR) → Text
    ↓
regex_extractor.py: RegexInvoiceExtractor.extract()
    ↓
Vendor Detection (Frank's / Pacific)
    ↓
Pattern Matching:
  - Invoice number
  - Date
  - Vendor name
  - Total amount
  - Line items (quantity, description, price, amount)
    ↓
Confidence Calculation
    ↓
Return Structured Data
```

#### LayoutLMv3 Extraction Flow
```
Image → Preprocessing
    ↓
LayoutLMv3Processor (tokenization + image encoding)
    ↓
LayoutLMv3ForTokenClassification (model inference)
    ↓
Token Classification (field labels)
    ↓
Post-processing (field extraction, line item parsing)
    ↓
Confidence Calculation
    ↓
Return Structured Data
```

#### OCR + Claude Extraction Flow
```
Image → OCR (Tesseract/EasyOCR) → Text
    ↓
Layout Structure Extraction (tables, headers, regions)
    ↓
Build Prompt with OCR text + layout hints
    ↓
Claude Haiku API Call (text parsing)
    ↓
JSON Response Parsing
    ↓
Validation
    ↓
Return Structured Data
```

#### Claude Vision Extraction Flow
```
Image → Base64 Encoding
    ↓
Claude Vision API Call (image analysis)
    ↓
JSON Response Parsing
    ↓
Validation
    ↓
Return Structured Data
```

### Database Flow

```
Extraction Result (JSON)
    ↓
database.py: save_extraction_result()
    ↓
For each page:
    ├─ Validate invoice data
    ├─ Normalize fields:
    │   ├─ Vendor name (remove suffixes, title case)
    │   ├─ Invoice number (alphanumeric, uppercase)
    │   ├─ Date (convert to YYYY-MM-DD)
    │   └─ Amount (parse to float)
    │
    ├─ Check for duplicates (invoice_number + vendor + date)
    │   ├─ If exists: UPDATE
    │   └─ If new: INSERT
    │
    └─ Save line items:
        ├─ Delete old line items (if UPDATE)
        └─ Insert new line items with foreign key
    ↓
Commit Transaction
    ↓
Return Save Result
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required for Claude-based extraction
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Debug regex extraction
DEBUG_REGEX=true
```

### Configuration File (`config.py`)

Key settings can be modified in `config.py`:

```python
# API Configuration
ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
DEFAULT_MODEL: str = "claude-3-opus-20240229"
TEXT_MODEL: str = "claude-3-haiku-20240307"

# PDF Processing
PDF_DPI: int = 300
PDF_FORMAT: str = "png"
PDF_GRAYSCALE: bool = False

# Image Preprocessing
CLAHE_CLIP_LIMIT: float = 2.0
CLAHE_TILE_GRID_SIZE: tuple = (8, 8)

# Output
OUTPUT_DIR: str = "output"
SAVE_IMAGES: bool = False
```

### Extractor Initialization

You can customize extraction behavior when creating the extractor:

```python
extractor = EnhancedInvoiceExtractor(
    api_key="your_key",           # Optional
    use_regex=True,               # Enable regex extraction
    use_layoutlmv3=True,          # Enable LayoutLMv3
    use_ocr=True,                 # Enable OCR
    ocr_engine="tesseract",       # "tesseract" or "easyocr"
    regex_confidence_threshold=0.70,
    layoutlmv3_confidence_threshold=0.50
)
```

## Usage Examples

### Example 1: Process Single Invoice

```bash
python main.py data/invoice.pdf
```

**Output:**
- JSON file: `output/invoice_extracted.json`
- Database entry: `invoices.db` (if enabled)
- Console summary with extracted fields

### Example 2: Batch Process Directory

```bash
python main.py data/ -o results/ -r
```

Processes all PDFs and images recursively, saves to `results/` directory.

### Example 3: Programmatic Usage

```python
from invoice_extractor import EnhancedInvoiceExtractor
from database import InvoiceDatabase

# Initialize extractor
extractor = EnhancedInvoiceExtractor(
    api_key="your_key",
    use_regex=True,
    use_layoutlmv3=True,
    use_ocr=True
)

# Extract invoice
result = extractor.extract_robust("invoice.pdf")

# Save to database
db = InvoiceDatabase("invoices.db")
db.save_extraction_result(result, "invoice.pdf")

# Query invoices
invoices = db.get_all_invoices(limit=10)
for invoice in invoices:
    print(f"Invoice #{invoice['invoice_number']}: ${invoice['total_amount']}")
```

### Example 4: Using Jupyter Notebook

```python
# In invoice_dashboard.ipynb
from invoice_extractor import EnhancedInvoiceExtractor
from database import InvoiceDatabase
from pathlib import Path

# Initialize
extractor = EnhancedInvoiceExtractor()
db = InvoiceDatabase()

# Process folder
data_folder = Path("data")
for pdf_file in data_folder.glob("*.pdf"):
    result = extractor.extract_robust(str(pdf_file))
    if result['status'] == 'success':
        db.save_extraction_result(result, str(pdf_file))
```

## Output Format

### JSON Output Structure

```json
{
  "status": "success",
  "pdf": "path/to/invoice.pdf",
  "validated": true,
  "pages": [
    {
      "page_number": 1,
      "extraction_method": "regex",
      "invoice_number": "20065629",
      "vendor_name": "Frank's Quality Produce",
      "date": "01/15/2024",
      "total_amount": 1234.56,
      "line_items": [
        {
          "description": "PRODUCT NAME",
          "quantity": 10,
          "unit_price": 12.34,
          "line_total": 123.40
        }
      ],
      "validated": true
    }
  ]
}
```

### Database Schema

**invoices table:**
- `id` (INTEGER, PRIMARY KEY)
- `invoice_number` (TEXT, NOT NULL)
- `vendor_name` (TEXT, NOT NULL)
- `invoice_date` (DATE, NOT NULL)
- `total_amount` (REAL, NOT NULL)
- `file_path` (TEXT)
- `source_pdf_name` (TEXT)
- `extraction_method` (TEXT)
- `confidence_score` (REAL)
- `validated` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- UNIQUE(invoice_number, vendor_name, invoice_date)

**line_items table:**
- `id` (INTEGER, PRIMARY KEY)
- `invoice_id` (INTEGER, FOREIGN KEY)
- `description` (TEXT, NOT NULL)
- `quantity` (REAL, NOT NULL)
- `unit_price` (REAL, NOT NULL)
- `line_total` (REAL, NOT NULL)
- `line_order` (INTEGER)
- `created_at` (TIMESTAMP)
- UNIQUE(invoice_id, line_order)

## Troubleshooting

### Common Issues

1. **"Tesseract not found"**
   - Install Tesseract OCR and ensure it's in PATH
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`

2. **"poppler not found" (PDF conversion)**
   - Install poppler-utils
   - macOS: `brew install poppler`
   - Linux: `sudo apt-get install poppler-utils`

3. **"LayoutLMv3 model download fails"**
   - Check internet connection
   - Ensure sufficient disk space (~500MB)
   - Model downloads automatically on first use

4. **"ANTHROPIC_API_KEY not set"**
   - Set environment variable or create `.env` file
   - System works without it, but Claude methods disabled

5. **Low extraction confidence**
   - Try different preprocessing settings
   - Check image quality (increase DPI for PDFs)
   - Enable debug mode: `DEBUG_REGEX=true python main.py invoice.pdf`

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
