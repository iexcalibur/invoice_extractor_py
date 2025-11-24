# 📄 Invoice Extraction System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Accuracy](https://img.shields.io/badge/Accuracy-100%25-brightgreen.svg)]()
[![Cost Savings](https://img.shields.io/badge/Cost%20Savings-96%25-success.svg)]()

> **Intelligent invoice data extraction using hybrid AI approach**  
> Combining Regex → LayoutLMv3 → OCR → Claude Vision for optimal accuracy and cost-efficiency

<img width="1506" height="891" alt="Screenshot 2025-11-24 at 11 41 54 PM" src="https://github.com/user-attachments/assets/543a2694-5049-4747-81d8-7d03769a80e6" />


## 🎯 Overview

This system automatically extracts structured data from invoice PDFs and images using a sophisticated 4-tier hybrid approach. It achieves **100% accuracy** while reducing costs by **92-96%** compared to pure LLM solutions.

### Key Features

- ✅ **Hybrid AI Extraction**: 4-tier intelligent fallback system
- ✅ **Cost Optimized**: 96% cheaper than pure Vision LLM  
- ✅ **High Accuracy**: 100% F1 score on evaluation set
- ✅ **Production Ready**: Database, exports, comprehensive error handling
- ✅ **Interactive Dashboard**: Beautiful Streamlit UI
- ✅ **Batch Processing**: Handle thousands of invoices
- ✅ **Export Functionality**: CSV, JSON, Database storage

---

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API key (optional)
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Usage

#### Interactive Dashboard (Recommended)

```bash
streamlit run streamlit_app.py
```

#### Command Line

```bash
# Process single invoice
python main.py invoice.pdf

# Batch with CSV export
python main.py data/ --export-csv
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| **Accuracy** | 100% F1 Score |
| **Cost Savings** | 92-96% vs pure LLM |
| **Speed** | ~2s average per invoice |

---

## 📁 Project Structure

```
Invoices/
│
├── main.py                        # CLI application
├── streamlit_app.py               # Interactive dashboard (Streamlit UI)
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── vendor_registry.json           # Vendor patterns configuration
├── invoices.db                    # SQLite database
│
├── doc/                           # Documentation
│   ├── PROJECT_DOCUMENTATION.md   # Complete project documentation
│   ├── FILE_DOCUMENTATION.md      # Detailed file documentation
│   ├── DATA_FLOW_DIAGRAM.md       # System architecture & data flow
│   └── TRADE_OFFS_ANALYSIS.md     # Method comparison analysis
│
├── core/                          # Core extraction modules
│   ├── __init__.py
│   ├── config.py                  # Configuration settings
│   ├── database.py                # SQLite database interface
│   ├── invoice_extractor.py       # Main orchestrator (4-tier extraction)
│   ├── regex_extractor.py         # Tier 1: Regex pattern matching
│   ├── enhanced_ocr.py            # OCR preprocessing & enhancement
│   ├── ocr_corrector.py           # OCR error correction
│   └── vendor_registry.py         # Vendor pattern registry system
│
├── components/                    # Streamlit UI components
│   ├── __init__.py
│   ├── about.py                   # About tab component
│   ├── analytics.py               # Analytics & insights tab
│   ├── database.py                # Database browser tab
│   ├── evaluation.py              # Evaluation & metrics tab
│   ├── overview.py                # Overview dashboard tab
│   ├── styles.py                  # CSS styles and theming
│   ├── upload.py                  # File upload & extraction tab
│   └── utils.py                    # Utility functions for UI
│
├── scripts/                       # Utility scripts
│   ├── diagnose_extraction.py     # Debugging & diagnostics
│   └── empty_db.py                # Database management
│
├── tests/                         # Testing & evaluation
│   ├── evaluate_extraction.py     # Ground truth evaluation
│   ├── test_evaluation.py          # Automated tests
│   └── ground_truth.json          # Test data & expected results
│
├── data/                          # Input directory (place invoices here)
│   └── *.pdf                      # Invoice PDF files
│
├── output/                        # Output directory 
│
└── venv/                          # Python virtual environment 
```

---

## 🏗️ Architecture & Approach

### 4-Tier Hybrid Extraction Pipeline

The system uses an intelligent fallback approach that automatically escalates through extraction methods based on confidence:

1. **Tier 1: Regex Pattern Matching** (FREE, <0.1s)
   - Pattern-based extraction for known vendors
   - 100% accuracy for supported formats

2. **Tier 2: LayoutLMv3** (FREE, ~2s)
   - Local transformer model for structured documents
   - 85-95% accuracy

3. **Tier 3: OCR + Claude LLM** (~$0.01, ~5s)
   - OCR text extraction with LLM parsing
   - 90-95% accuracy

4. **Tier 4: Claude Vision** (~$0.05, ~10s)
   - Multimodal AI for complex layouts
   - 95-99% accuracy

**Why Hybrid?** This approach achieves **92-96% cost savings** compared to pure Vision LLM while maintaining **100% accuracy** on evaluation set.

---

## 🛠️ Technologies & Libraries

### Core Technologies
- **Python 3.9+**: Core programming language
- **Anthropic Claude API**: LLM & Vision AI (Tiers 3 & 4)
- **LayoutLMv3**: Microsoft's Document AI transformer (Tier 2)
- **Tesseract OCR**: Google's OCR engine (Tier 3)
- **Streamlit**: Interactive web dashboard
- **SQLite**: Database for invoice storage
- **Plotly**: Data visualizations

### Key Python Libraries
- `anthropic`: Claude API client
- `transformers`: LayoutLMv3 model
- `pytesseract`: OCR integration
- `pandas`: Data manipulation
- `streamlit`: Web UI framework
- `plotly`: Interactive charts

---

## 📝 Limitations & Future Work

### Current Limitations
- **Vendor Coverage**: Optimized for 2 vendors (Frank's Quality Produce, Pacific Food Importers)
- **Language**: English only
- **Layout**: Best for standard invoice formats
- **Handwriting**: Limited support

### Planned Enhancements
- [ ] Support more vendors (auto-learn patterns via vendor registry)
- [ ] Multi-language support
- [ ] Fine-tune LayoutLMv3 on invoice dataset
- [ ] Field-level confidence scores
- [ ] REST API endpoint
- [ ] Docker containerization

---

## 📚 Documentation

For detailed documentation, see the [`doc/`](doc/) folder:

- **[PROJECT_DOCUMENTATION.md](doc/PROJECT_DOCUMENTATION.md)**: Complete project overview, architecture, and usage
- **[FILE_DOCUMENTATION.md](doc/FILE_DOCUMENTATION.md)**: Detailed documentation for each module
- **[DATA_FLOW_DIAGRAM.md](doc/DATA_FLOW_DIAGRAM.md)**: System architecture and data flow diagrams
- **[TRADE_OFFS_ANALYSIS.md](doc/TRADE_OFFS_ANALYSIS.md)**: Comparison of extraction methods

---

