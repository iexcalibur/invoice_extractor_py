"""
Configuration settings for invoice extraction
"""

import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    DEFAULT_MODEL: str = "claude-3-opus-20240229" 
    TEXT_MODEL: str = "claude-3-haiku-20240307" 
    
    # PDF Processing Configuration
    PDF_DPI: int = 300
    PDF_FORMAT: str = "png"
    PDF_GRAYSCALE: bool = False
    USE_PDFTOCAIRO: bool = True
    
    # Image Preprocessing
    CLAHE_CLIP_LIMIT: float = 2.0
    CLAHE_TILE_GRID_SIZE: tuple = (8, 8)
    
    # Output Configuration
    OUTPUT_DIR: str = "output"
    SAVE_IMAGES: bool = False
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.ANTHROPIC_API_KEY:
            return False
        return True
    
    @classmethod
    def get_api_key(cls) -> str:
        """Get API key with validation"""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Please set it as an environment variable or in .env file"
            )
        return cls.ANTHROPIC_API_KEY

