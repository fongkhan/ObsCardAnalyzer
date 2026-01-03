# ObsCardAnalyzer (prototype)

This repository contains a Python prototype to detect trading-card-like objects in a video source, OCR the card name, look up (stub) Cardmarket data, and present results via a simple Flask overlay suitable for OBS Browser Source. It also persists detected cards to a JSON file.

Key pieces
- `src/card_detector.py` — find card-shaped contours and extract normalized card images.
- `src/ocr.py` — preprocess and run Tesseract OCR on card images.
- `src/cardmarket_client.py` — placeholder/stub for Cardmarket lookup.
- `src/server.py` — Flask app that serves overlay and accepts updates from the main process.
- `src/main.py` — capture loop, detection, OCR, enqueueing and worker to lookup/persist results.

Quick setup

1. Create and activate a Python 3.10+ venv.
2. Install system Tesseract (required by `pytesseract`). On Windows, install from https://github.com/tesseract-ocr/tesseract and ensure `tesseract.exe` is on PATH.
3. Install Python deps:

```powershell
python -m pip install -r "E:/Program Files/git/ObsCardAnalyzer/requirements.txt"
```

Run

1. Start the Flask overlay:

```powershell
python src/server.py
```

2. In another terminal, run the analyzer pointing at a camera index or video file (0 for default camera):

```powershell
python src/main.py --source 0
```

3. In OBS, add a Browser Source pointing to http://127.0.0.1:5000/overlay (adjust size as needed).

Notes & next steps
- Cardmarket client is currently a stub — you should provide API credentials and implement real HTTP logic in `src/cardmarket_client.py`.
- Detection is a simple contour-based approach; for improved accuracy use an object detector (YOLO/Detectron) trained on card images.
- OCR quality depends on the card artwork and fonts. Consider template matching, a custom OCR model, or sending cropped names to an external OCR provider.

Additional notes

- PokéTCG API: this prototype supports PokéTCG via the official SDK `pokemontcgsdk` or via direct REST as fallback. To use the SDK, set your API key in the environment variable `POKEMON_TCG_KEY` or pass it into the `CardmarketClient` constructor. Example:

```powershell
$env:POKEMON_TCG_KEY = 'your-key-here'
python src/main.py --game pokemon
```

- CLI `--game` flag: when running `src/main.py` you can pass `--game magic` or `--game pokemon` to prefer Scryfall (Magic) or PokéTCG respectively. The default `--game auto` will try Magic first and fall back to Pokemon.

- Caching: API results are cached in `src/card_cache.json` to reduce repeated lookups.

