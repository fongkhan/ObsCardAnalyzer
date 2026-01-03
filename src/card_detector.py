import cv2
import numpy as np

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts, width=400, height=600):
    rect = order_points(pts)
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (width, height))
    return warped

def detect_cards_from_frame(frame, min_area=5000):
    """Return list of (card_image, bbox_pts) found in the frame."""
    orig = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cards = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2)
            # filter by aspect ratio (width / height) - many cards are roughly portrait
            # compute bounding rect to estimate ratio after ordering
            try:
                warped = four_point_transform(orig, pts)
            except Exception:
                continue
            h, w = warped.shape[:2]
            if h == 0:
                continue
            ratio = float(w) / float(h)
            # typical trading card is around 0.63 (width/height) when portrait; accept a broad range
            if not (0.4 <= ratio <= 1.5):
                # still allow landscape cards; this filtering reduces false positives
                pass
            cards.append((warped, pts))
    return cards

if __name__ == "__main__":
    print("card_detector module - import into your application")
