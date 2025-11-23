"""
SOLUTION 1: Improve OCR Preprocessing (PERMANENT FIX)
This fixes the root cause instead of patching the symptom
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract


def preprocess_invoice_image_enhanced(image: Image.Image, debug: bool = False) -> Image.Image:
    """
    Enhanced image preprocessing specifically for invoice OCR
    
    Fixes common OCR issues:
    - "INVOICE" being read as "INVOKE" 
    - Missing characters
    - Poor text recognition
    
    Args:
        image: PIL Image
        debug: If True, save intermediate images
        
    Returns:
        Enhanced PIL Image
    """
    # Convert PIL to OpenCV format
    img_array = np.array(image)
    
    # Convert to grayscale if color
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # 1. Increase resolution (upscale before processing)
    # This helps OCR recognize small text better
    scale_factor = 2.0
    width = int(gray.shape[1] * scale_factor)
    height = int(gray.shape[0] * scale_factor)
    upscaled = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)
    
    if debug:
        cv2.imwrite('debug_01_upscaled.png', upscaled)
    
    # 2. Denoise (remove noise while preserving edges)
    denoised = cv2.fastNlMeansDenoising(upscaled, h=10)
    
    if debug:
        cv2.imwrite('debug_02_denoised.png', denoised)
    
    # 3. Adaptive thresholding (better than simple threshold)
    # This handles varying lighting conditions
    binary = cv2.adaptiveThreshold(
        denoised, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        blockSize=11,  # Size of pixel neighborhood
        C=2  # Constant subtracted from mean
    )
    
    if debug:
        cv2.imwrite('debug_03_binary.png', binary)
    
    # 4. Morphological operations (clean up text)
    # Remove small artifacts and connect broken characters
    kernel = np.ones((2, 2), np.uint8)
    morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    if debug:
        cv2.imwrite('debug_04_morphed.png', morphed)
    
    # 5. Sharpen (make text edges crisper)
    kernel_sharpen = np.array([[-1,-1,-1],
                                [-1, 9,-1],
                                [-1,-1,-1]])
    sharpened = cv2.filter2D(morphed, -1, kernel_sharpen)
    
    if debug:
        cv2.imwrite('debug_05_sharpened.png', sharpened)
    
    # Convert back to PIL Image
    result = Image.fromarray(sharpened)
    
    return result


def extract_text_with_enhanced_ocr(image: Image.Image, debug: bool = False) -> str:
    """
    Extract text using enhanced preprocessing + optimized Tesseract config
    
    Args:
        image: PIL Image
        debug: Print debug info
        
    Returns:
        Extracted OCR text
    """
    # Preprocess image
    enhanced_image = preprocess_invoice_image_enhanced(image, debug=debug)
    
    # Use optimized Tesseract configuration
    # PSM 6: Assume a single uniform block of text
    # OEM 3: Default OCR Engine Mode (best available)
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$.,/-: "()"'
    
    # Extract text
    text = pytesseract.image_to_string(enhanced_image, config=custom_config)
    
    if debug:
        print(f"[DEBUG] OCR extracted {len(text)} characters")
        # Check for common misreads
        if "INVOKE" in text:
            print(f"[DEBUG] ⚠️ Found 'INVOKE' - OCR misread 'INVOICE'")
        if "INVOICE" in text:
            print(f"[DEBUG] ✅ Found 'INVOICE' correctly")
    
    return text


# How to use in your invoice_extractor.py:
"""
In invoice_extractor.py, replace the OCR extraction in extract_with_regex():

OLD CODE:
    if TESSERACT_AVAILABLE:
        ocr_text = pytesseract.image_to_string(image)

NEW CODE:
    if TESSERACT_AVAILABLE:
        from enhanced_ocr import extract_text_with_enhanced_ocr
        ocr_text = extract_text_with_enhanced_ocr(image, debug=DEBUG_MODE)
"""

if __name__ == "__main__":
    # Test the enhanced OCR
    from PIL import Image
    
    # Load your problematic invoice
    img = Image.open("path/to/invoice_with_invoke_error.png")
    
    # Extract text with enhancement
    text = extract_text_with_enhanced_ocr(img, debug=True)
    
    print("\n" + "="*80)
    print("EXTRACTED TEXT (first 500 chars):")
    print("="*80)
    print(text[:500])
    
    # Check if INVOICE is correctly recognized
    if "INVOICE" in text and "INVOKE" not in text:
        print("\n✅ SUCCESS: 'INVOICE' correctly recognized!")
    elif "INVOKE" in text:
        print("\n⚠️ STILL MISREAD: 'INVOICE' read as 'INVOKE'")
        print("   May need further preprocessing adjustments")
    else:
        print("\n❓ Neither 'INVOICE' nor 'INVOKE' found")
