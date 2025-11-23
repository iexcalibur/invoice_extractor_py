"""
Configuration settings for invoice extraction system

This module provides centralized configuration management for the invoice
extraction pipeline, including API keys, model settings, and processing parameters.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """Central configuration for invoice extraction system"""
    
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"
    TEXT_PARSING_MODEL: str = "claude-3-haiku-20240307"
    VISION_MODEL: str = "claude-3-5-sonnet-20241022"
    
    USE_REGEX: bool = True
    USE_LAYOUTLMV3: bool = True
    USE_OCR: bool = True
    USE_VISION: bool = True
    
    REGEX_CONFIDENCE_THRESHOLD: float = 0.60
    LAYOUTLMV3_CONFIDENCE_THRESHOLD: float = 0.50
    OCR_CONFIDENCE_THRESHOLD: float = 0.60
    
    PDF_DPI: int = 200
    PDF_VISION_DPI: int = 200
    PDF_FORMAT: str = "png"
    PDF_GRAYSCALE: bool = False
    USE_PDFTOCAIRO: bool = True
    
    ENABLE_PREPROCESSING: bool = True
    CLAHE_CLIP_LIMIT: float = 2.0
    CLAHE_TILE_GRID_SIZE: tuple = (8, 8)
    DENOISE_H: int = 10
    
    OCR_ENGINE: str = "tesseract"
    TESSERACT_CONFIG: str = "--oem 3 --psm 6"
    EASYOCR_LANGUAGES: list = ['en']
    EASYOCR_GPU: bool = False
    
    DATABASE_PATH: str = "invoices.db"
    DATABASE_TIMEOUT: float = 10.0
    ENABLE_DATABASE: bool = True
    
    OUTPUT_DIR: str = "output"
    SAVE_IMAGES: bool = False
    SAVE_JSON: bool = True
    EXPORT_CSV: bool = True
    
    VALIDATION_RULES: Dict[str, Any] = {
        'invoice_number': {
            'required': True,
            'min_length': 3,
            'max_length': 50
        },
        'vendor_name': {
            'required': True,
            'min_length': 2,
            'max_length': 200
        },
        'date': {
            'required': True,
            'format': '%Y-%m-%d'
        },
        'total_amount': {
            'required': True,
            'min_value': 0.0,
            'max_value': 1000000.0
        }
    }
    
    # Vendor-specific patterns
    VENDOR_PATTERNS: Dict[str, Dict[str, str]] = {
        'franks': {
            'name': "Frank's Quality Produce",
            'invoice_prefix': '200',
            'invoice_pattern': r'200\d{6}',
        },
        'pacific': {
            'name': 'Pacific Food Importers',
            'invoice_prefix': '37',
            'invoice_pattern': r'37\d{5}',
        }
    }
    
    MAX_WORKERS: int = 4  # For parallel processing
    BATCH_SIZE: int = 10
    CACHE_ENABLED: bool = True
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = "invoice_extraction.log"
    ENABLE_DEBUG: bool = os.getenv("DEBUG", "").lower() == "true"
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate that required configuration is present and valid
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check API key if vision/llm features enabled
        if (cls.USE_VISION or cls.USE_OCR) and not cls.ANTHROPIC_API_KEY:
            errors.append(
                "ANTHROPIC_API_KEY not set but required for LLM features. "
                "Set it as environment variable or in .env file"
            )
        
        # Validate thresholds
        if not (0.0 <= cls.REGEX_CONFIDENCE_THRESHOLD <= 1.0):
            errors.append(f"REGEX_CONFIDENCE_THRESHOLD must be between 0 and 1")
        
        if not (0.0 <= cls.LAYOUTLMV3_CONFIDENCE_THRESHOLD <= 1.0):
            errors.append(f"LAYOUTLMV3_CONFIDENCE_THRESHOLD must be between 0 and 1")
        
        # Validate paths
        output_path = Path(cls.OUTPUT_DIR)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create output directory: {e}")
        
        # Check OCR engine availability
        if cls.USE_OCR:
            if cls.OCR_ENGINE == "tesseract":
                try:
                    import pytesseract
                    pytesseract.get_tesseract_version()
                except:
                    errors.append("Tesseract not available but OCR is enabled")
            elif cls.OCR_ENGINE == "easyocr":
                try:
                    import easyocr
                except ImportError:
                    errors.append("EasyOCR not installed but set as OCR engine")
        
        # Check LayoutLMv3 availability
        if cls.USE_LAYOUTLMV3:
            try:
                import transformers
                import torch
            except ImportError:
                errors.append("LayoutLMv3 requires transformers and torch packages")
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def get_api_key(cls) -> str:
        """
        Get API key with validation
        
        Returns:
            API key string
            
        Raises:
            ValueError: If API key is not configured
        """
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Please set it as an environment variable or in .env file.\n"
                "Example: export ANTHROPIC_API_KEY='your-key-here'"
            )
        return cls.ANTHROPIC_API_KEY
    
    @classmethod
    def get_summary(cls) -> str:
        """Get a human-readable configuration summary"""
        summary = []
        summary.append("=" * 60)
        summary.append("INVOICE EXTRACTION CONFIGURATION")
        summary.append("=" * 60)
        
        summary.append("\nExtraction Strategy:")
        summary.append(f"  ✓ Regex extraction: {'Enabled' if cls.USE_REGEX else 'Disabled'}")
        summary.append(f"  ✓ LayoutLMv3: {'Enabled' if cls.USE_LAYOUTLMV3 else 'Disabled'}")
        summary.append(f"  ✓ OCR + LLM: {'Enabled' if cls.USE_OCR else 'Disabled'}")
        summary.append(f"  ✓ Vision + LLM: {'Enabled' if cls.USE_VISION else 'Disabled'}")
        
        summary.append("\nModel Configuration:")
        summary.append(f"  • Default Model: {cls.DEFAULT_MODEL}")
        summary.append(f"  • Text Parsing: {cls.TEXT_PARSING_MODEL}")
        summary.append(f"  • Vision Model: {cls.VISION_MODEL}")
        
        summary.append("\nConfidence Thresholds:")
        summary.append(f"  • Regex: {cls.REGEX_CONFIDENCE_THRESHOLD:.0%}")
        summary.append(f"  • LayoutLMv3: {cls.LAYOUTLMV3_CONFIDENCE_THRESHOLD:.0%}")
        
        summary.append("\nDatabase:")
        summary.append(f"  • Path: {cls.DATABASE_PATH}")
        summary.append(f"  • Enabled: {'Yes' if cls.ENABLE_DATABASE else 'No'}")
        
        is_valid, errors = cls.validate()
        summary.append(f"\nValidation: {'✓ Passed' if is_valid else '✗ Failed'}")
        if errors:
            for error in errors:
                summary.append(f"  • {error}")
        
        summary.append("=" * 60)
        return "\n".join(summary)
    
    @classmethod
    def print_config(cls):
        """Print configuration summary"""
        print(cls.get_summary())


# Convenience function for quick validation
def validate_config() -> bool:
    """
    Validate configuration and print results
    
    Returns:
        True if configuration is valid, False otherwise
    """
    is_valid, errors = Config.validate()
    
    if is_valid:
        print("✓ Configuration is valid")
        return True
    else:
        print("✗ Configuration errors detected:")
        for error in errors:
            print(f"  • {error}")
        return False


if __name__ == "__main__":
    # When run directly, print configuration summary
    Config.print_config()