import cv2
import numpy as np
import pytesseract
import threading
import time
from card_search import search_card_generic
from file_logger import log_card_history, write_current_card

# Configure pytesseract path if needed (e.g. Windows default)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class CardDetector:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.running = False
        self.current_frame = None
        self.current_card_info = None
        self.processed_frame = None
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            print(f"Cannot open camera {self.camera_index}")
            self.running = False
            return
        
        # Start processing thread
        threading.Thread(target=self._process_loop, daemon=True).start()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def _process_loop(self):
        last_search_time = 0
        search_cooldown = 2.0  # Seconds between API calls to avoid spam

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            with self.lock:
                self.current_frame = frame.copy()

            # Process every few frames to save CPU? Or every frame for smoothness?
            # Let's do every frame but specific heavy tasks less often.
            
            # 1. Detect card contour
            warped, debug_image = self.detect_card(frame)
            
            with self.lock:
                self.processed_frame = debug_image

            if warped is not None:
                # Check sharpness/stability?
                
                # 2. Extract Text (OCR)
                # Only do this if we haven't searched recently or if it looks stabilize
                now = time.time()
                if now - last_search_time > search_cooldown:
                    text = self.extract_text(warped)
                    print(f"OCR Text: {text[:50]}...") # Debug log
                    
                    # 3. Search API
                    if len(text) > 5:
                        result = search_card_generic(text)
                        if result:
                            # Verify if it's different from current
                            if self.current_card_info is None or result['name'] != self.current_card_info.get('name'):
                                print(f"Found Card: {result['name']}")
                                self.current_card_info = result
                                log_card_history(result)
                                # Save warped image temporarily for logging
                                cv2.imwrite("temp_card.jpg", warped)
                                write_current_card(result, "temp_card.jpg")
                                last_search_time = now
            else:
                 # No card detected
                 pass

            time.sleep(0.01)

    def detect_card(self, frame):
        """
        Finds the largest rectangular contour.
        Returns (warped_card_image, debug_frame_with_contours)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        # Canny edge detection
        edges = cv2.Canny(blur, 50, 150)
        
        # Dialate to close gaps
        kernel = np.ones((5,5),np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        largest_area = 0
        best_cnt = None
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 5000: # Minimum area filter
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                if len(approx) == 4:
                    if area > largest_area:
                        largest_area = area
                        best_cnt = approx

        debug_frame = frame.copy()
        warped = None
        
        if best_cnt is not None:
            cv2.drawContours(debug_frame, [best_cnt], -1, (0, 255, 0), 2)
            warped = self.warp_perspective(frame, best_cnt)

        return warped, debug_frame

    def warp_perspective(self, frame, contour):
        pts = contour.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")

        # Order points: top-left, top-right, bottom-right, bottom-left
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        (tl, tr, br, bl) = rect

        # Width of new image
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        # Height of new image
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(frame, M, (maxWidth, maxHeight))
        return warped

    def extract_text(self, image):
        # Preprocessing for OCR
        # Convert to gray
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Thresholding
        # thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Tesseract configuration
        # Assume generic English for now
        try:
            text = pytesseract.image_to_string(gray, lang='eng')
            return text
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
