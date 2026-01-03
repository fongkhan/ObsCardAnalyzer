import cv2
import pytesseract

def preprocess_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th

def ocr_card_image(img):
    """Return the OCR text from a card image.

    Strategy:
    - Attempt OCR on a cropped top region where card names typically appear.
    - If that yields nothing, fallback to whole-card OCR.
    """
    def clean(t: str) -> str:
        return (t or '').strip()

    h, w = img.shape[:2]
    # crop top ~20% of the card for name (adjustable)
    top_h = max(20, int(h * 0.20))
    name_region = img[0:top_h, 0:w]
    th = preprocess_for_ocr(name_region)
    config = "--psm 7"  # treat as a single text line
    name_text = pytesseract.image_to_string(th, config=config)
    name_text = clean(name_text)
    if name_text:
        return name_text

    # fallback to whole-image OCR with block mode
    th_full = preprocess_for_ocr(img)
    config2 = "--psm 6"
    text = pytesseract.image_to_string(th_full, config=config2)
    return clean(text)

if __name__ == "__main__":
    print("ocr module")
