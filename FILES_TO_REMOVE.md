# Files No Longer Needed

## Summary

Based on the current setup analysis, here are files that are **not needed** for production:

---

## 🗑️ Files to Delete

### 1. **Test/Debug Scripts** (Not needed for production)
- ✅ `test_regex_debug.py` - Debug script for testing regex extraction
- ✅ `verify_db.py` - Database verification script
- ✅ `verify_flow.py` - Data flow verification script

**Reason:** These are development/testing utilities, not needed for production deployment.

---

### 2. **Utility Scripts** (Optional - can be kept if useful)
- ⚠️ `query_db.py` - Database query utility script

**Reason:** Useful for manual database queries but not essential for the application. Keep if you need to query the database manually.

---

### 3. **Test Data Folders** (Not needed for production)
- ✅ `extra/` folder - Contains test files:
  - `map.txt`
  - `text1.txt`
  - `text2.txt`

**Reason:** Test data files, not needed for production.

---

### 4. **Duplicate Extractor** (Consider consolidating)
- ⚠️ `invoice_extractor_enhanced.py` - Used only by `main.py`

**Current Usage:**
- `app.py` uses `invoice_extractor_with_regex.py` ✅ (better - has regex)
- `main.py` uses `invoice_extractor_enhanced.py` ⚠️ (no regex)

**Recommendation:** 
- Option 1: Update `main.py` to use `invoice_extractor_with_regex.py` instead, then delete `invoice_extractor_enhanced.py`
- Option 2: Keep both if you want different extraction strategies for CLI vs Web

---

## ✅ Files to KEEP (Essential)

### Core Application Files
- ✅ `app.py` - Flask web application
- ✅ `main.py` - CLI script
- ✅ `invoice_extractor_with_regex.py` - Main extractor (used by app.py)
- ✅ `invoice_extractor_enhanced.py` - Alternative extractor (used by main.py) - *see note above*
- ✅ `regex_extractor.py` - Required by invoice_extractor_with_regex.py
- ✅ `config.py` - Configuration management
- ✅ `database.py` - Database operations
- ✅ `formatter.py` - Output formatting (used by main.py)
- ✅ `templates/index.html` - Web UI template
- ✅ `requirements.txt` - Python dependencies
- ✅ `invoices.db` - Database file (if in use)

### Data/Output Directories
- ✅ `data/` - Input PDFs/images folder
- ✅ `output/` - Output directory for results
- ✅ `venv/` - Virtual environment (if using)

---

## 📋 Recommended Action Plan

### Immediate Deletions (Safe to remove):
```bash
# Test/Debug scripts
rm test_regex_debug.py
rm verify_db.py
rm verify_flow.py

# Test data folder
rm -rf extra/
```

### Optional Deletions (Consider first):
```bash
# Utility script (keep if you query DB manually)
rm query_db.py  # Optional

# Consider consolidating extractors
# Option: Update main.py to use invoice_extractor_with_regex.py
# Then delete: invoice_extractor_enhanced.py
```

---

## 🔄 Consolidation Option

If you want to use only the better extractor (`invoice_extractor_with_regex.py`):

1. Update `main.py` line 15:
   ```python
   # Change from:
   from invoice_extractor_enhanced import EnhancedInvoiceExtractor
   
   # To:
   from invoice_extractor_with_regex import EnhancedInvoiceExtractor
   ```

2. Update `main.py` line 31-35 to enable regex:
   ```python
   extractor = EnhancedInvoiceExtractor(
       api_key=Config.get_api_key() if Config.validate() else None,
       use_regex=True,  # Add this
       use_layoutlmv3=True,
       use_ocr=True
   )
   ```

3. Then delete `invoice_extractor_enhanced.py`

---

## Summary Count

- **Files to delete:** 3-4 files (test scripts)
- **Folders to delete:** 1 folder (`extra/`)
- **Files to consider consolidating:** 1 file (`invoice_extractor_enhanced.py`)

