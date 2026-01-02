import cv2
import pytesseract

def preprocess_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th

def ocr_card_image(img):
    """Return the OCR text from a card image."""
    th = preprocess_for_ocr(img)
    config = "--psm 6"  # assume a block of text
    text = pytesseract.image_to_string(th, config=config)
    return text.strip()

if __name__ == "__main__":
    print("ocr module")
