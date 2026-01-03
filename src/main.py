import argparse
import json
import threading
import time
from collections import deque
from pathlib import Path
import os

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

import requests

from card_detector import detect_cards_from_frame
from ocr import ocr_card_image
from cardmarket_client import CardmarketClient


RESULTS_FILE = Path(__file__).resolve().parents[0] / 'processed_cards.json'


class Worker(threading.Thread):
    def __init__(self, queue, client, server_url=None, game_hint: str = 'auto'):
        super().__init__(daemon=True)
        self.queue = queue
        self.client = client
        self.server_url = server_url
        # game_hint: 'auto' | 'magic' | 'pokemon'
        self.game_hint = (game_hint or 'auto')
        self.seen = set()

    def run(self):
        while True:
            if not self.queue:
                time.sleep(0.1)
                continue
            name = self.queue.popleft()
            if name in self.seen:
                continue
            self.seen.add(name)
            # determine game parameter to pass to lookup
            game = None if self.game_hint == 'auto' else self.game_hint
            info = self.client.lookup_by_name(name, game=game)
            record = {'name': name, 'info': info, 'timestamp': time.time()}
            self._persist(record)
            if self.server_url:
                try:
                    requests.post(self.server_url + '/api/update', json={**info, 'name': name})
                except Exception:
                    pass

    def _persist(self, record):
        data = []
        if RESULTS_FILE.exists():
            try:
                with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.insert(0, record)
def main(source=0, server_url=None, game_hint='auto'):
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) is not installed. Install it with: pip install opencv-python")

    def _open_capture(src):
        """Try to open a VideoCapture for the given src.

        For numeric camera indexes we attempt the default backend first and fall back to DirectShow (CAP_DSHOW).
        We also try to read one frame to verify the capture is producing frames.
        """
        is_index = str(src).isdigit()
        # try backends for camera index
        if is_index:
            idx = int(src)
            backends = [None]
            # prefer DirectShow fallback on Windows
            try:
                backends.append(cv2.CAP_DSHOW)
            except Exception:
                pass
            for b in backends:
                try:
                    cap = cv2.VideoCapture(idx) if b is None else cv2.VideoCapture(idx, b)
                except Exception:
                    cap = None
                if cap is None:
                    continue
                # give the camera a moment and try to grab a frame
                time.sleep(0.1)
                ret, _ = cap.read()
                if ret:
                    return cap
                try:
                    cap.release()
                except Exception:
                    pass
            # last attempt: open without special backend
            return cv2.VideoCapture(idx)

        # non-index: treat as file or stream URL
        try:
            cap = cv2.VideoCapture(src)
            time.sleep(0.05)
            ret, _ = cap.read()
            if ret:
                return cap
            return cap
        except Exception:
            return None

    cap = _open_capture(source)
    if cap is None or not getattr(cap, 'isOpened', lambda: False)():
        raise RuntimeError(
            f"Could not open video source '{source}'.\n"
            "- If this is a camera index, try a different index (0, 1, ...).\n"
            "- Ensure no other application (OBS, Teams, Browser) is using the camera.\n"
            "- On Windows, try running with admin privileges or allow camera access in Settings.\n"
            "- You can also pass a path to a video file instead of a camera index."
        )

    queue = deque()
    client = CardmarketClient()
    worker = Worker(queue, client, server_url=server_url, game_hint=game_hint)
    worker.start()

    print('Starting capture. Press q to quit.')
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cards = detect_cards_from_frame(frame)
        for card_img, pts in cards:
            text = ocr_card_image(card_img)
            # simple heuristic: take first line as name
            name = (text.splitlines()[0].strip() if text else '').strip()
            if name:
                queue.append(name)
                # draw bbox on frame
                cv2.polylines(frame, [pts.astype(int)], True, (0, 255, 0), 2)
                cv2.putText(frame, name[:30], tuple(pts[0].astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0),2)

        cv2.imshow('Analyzer', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='0', help='Camera index or path to video file')
    parser.add_argument('--server', default='http://127.0.0.1:5000', help='Overlay server URL')
    parser.add_argument('--game', choices=['auto', 'magic', 'pokemon'], default='auto', help='Which game API to prefer for lookups')
    args = parser.parse_args()
    # Pass game hint into client lookups via an environment variable consumed by the worker
    # (Worker will still try auto behavior when None)
    # We'll set an attribute on the CardmarketClient instance instead when needed.
    # For now simply call main; the worker/client will be consulted directly for game hints later.
    main(source=args.source, server_url=args.server, game_hint=args.game)
