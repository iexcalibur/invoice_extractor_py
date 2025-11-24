import cv2
import numpy as np
from PIL import Image
import pytesseract


def preprocess_invoice_image_enhanced(image: Image.Image, debug: bool = False) -> Image.Image:
    img_array = np.array(image)
    
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    scale_factor = 2.0
    width = int(gray.shape[1] * scale_factor)
    height = int(gray.shape[0] * scale_factor)
    upscaled = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)
    
    if debug:
        cv2.imwrite('debug_01_upscaled.png', upscaled)
    
    denoised = cv2.fastNlMeansDenoising(upscaled, h=10)
    
    if debug:
        cv2.imwrite('debug_02_denoised.png', denoised)
    
    binary = cv2.adaptiveThreshold(
        denoised, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        blockSize=11,  
        C=2  
    )
    
    if debug:
        cv2.imwrite('debug_03_binary.png', binary)
    
    kernel = np.ones((2, 2), np.uint8)
    morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    if debug:
        cv2.imwrite('debug_04_morphed.png', morphed)
    
    kernel_sharpen = np.array([[-1,-1,-1],
                                [-1, 9,-1],
                                [-1,-1,-1]])
    sharpened = cv2.filter2D(morphed, -1, kernel_sharpen)
    
    if debug:
        cv2.imwrite('debug_05_sharpened.png', sharpened)
    
    result = Image.fromarray(sharpened)
    
    return result


def extract_text_with_enhanced_ocr(image: Image.Image, debug: bool = False) -> str:
    enhanced_image = preprocess_invoice_image_enhanced(image, debug=debug)
    
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$.,/-: "()"'
    
    text = pytesseract.image_to_string(enhanced_image, config=custom_config)
    
    if debug:
        print(f"[DEBUG] OCR extracted {len(text)} characters")
        if "INVOKE" in text:
            print(f"[DEBUG] WARNING: Found 'INVOKE' - OCR misread 'INVOICE'")
        if "INVOICE" in text:
            print(f"[DEBUG] OK: Found 'INVOICE' correctly")
    
    return text


if __name__ == "__main__":
    from PIL import Image
    
    img = Image.open("path/to/invoice_with_invoke_error.png")
    
    text = extract_text_with_enhanced_ocr(img, debug=True)
    
    print("\n" + "="*80)
    print("EXTRACTED TEXT (first 500 chars):")
    print("="*80)
    print(text[:500])
    
    if "INVOICE" in text and "INVOKE" not in text:
        print("\nSUCCESS: 'INVOICE' correctly recognized!")
    elif "INVOKE" in text:
        print("\nWARNING: STILL MISREAD: 'INVOICE' read as 'INVOKE'")
        print("   May need further preprocessing adjustments")
    else:
        print("\nNOTE: Neither 'INVOICE' nor 'INVOKE' found")
