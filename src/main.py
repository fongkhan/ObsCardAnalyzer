import argparse
import json
import threading
import time
from collections import deque
from pathlib import Path
import os

import cv2
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
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data[:500], f, indent=2)


def main(source=0, server_url=None, game_hint='auto'):
    cap = cv2.VideoCapture(int(source) if str(source).isdigit() else source)
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
