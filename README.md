
# ObsCardAnalyzer (prototype)

ObsCardAnalyzer is a lightweight Python prototype to detect trading-card-like objects from a video source (camera or file), extract the card name using OCR, look up card data using free public APIs (Scryfall for Magic: The Gathering and PokéTCG for Pokémon), and expose results as a Browser Source overlay for OBS. Detected cards are also persisted to a JSON file for later review.

This repo is a starting point — it's intentionally simple and designed to be extended.

What you'll find here
- `src/card_detector.py` — OpenCV-based contour detection + perspective warp to extract card images from frames.
- `src/ocr.py` — OCR helpers using Tesseract; attempts name-region OCR before falling back to full-image OCR.
- `src/cardmarket_client.py` — unified client that queries Scryfall (MTG) and PokéTCG (Pokemon). Prefers the `pokemontcgsdk` SDK when installed; falls back to REST requests. Includes a small persistent cache.
- `src/server.py` — Flask overlay server (serves `/overlay` and `/api/update`, `/api/latest`). Use as an OBS Browser Source.
- `src/main.py` — main application: video capture → detection → OCR → enqueue → lookup worker → overlay sync + persistence.
- `requirements.txt` — Python dependencies for the prototype.

Requirements

- Python 3.10+ (3.11/3.13 tested in the project venv). Use a virtual environment.
- System Tesseract OCR (required by `pytesseract`). On Windows, install a build and add `tesseract.exe` to PATH. Example installers:
	- Windows: https://github.com/UB-Mannheim/tesseract/wiki or official builds linked from https://tesseract-ocr.github.io/

Install Python dependencies (PowerShell):

```powershell
& "E:/Program Files/git/ObsCardAnalyzer/.venv/Scripts/Activate.ps1"
python -m pip install -r "E:/Program Files/git/ObsCardAnalyzer/requirements.txt"
```

If you prefer not to use the included virtualenv, create one and install into it:

```powershell
python -m venv .venv
& ".venv/Scripts/Activate.ps1"
python -m pip install -r requirements.txt
```

Optional: PokéTCG SDK and API key

The project supports the official PokéTCG SDK (`pokemontcgsdk`). The SDK is included in `requirements.txt`. To use the SDK with your API key (recommended for reliability and higher rate limits), set the `POKEMON_TCG_KEY` environment variable before running:

```powershell
$env:POKEMON_TCG_KEY = 'your-pokemontcg-key'
```

You can obtain a (free) PokéTCG API key at https://pokemontcg.io/ (check their docs).

Quick start — run the overlay and analyzer

1. Start the overlay server (one terminal):

```powershell
python "E:/Program Files/git/ObsCardAnalyzer/src/server.py"
```

2. In another terminal start the analyzer and point it at your camera (index 0), or a video file. Use `--game` to prefer a specific API:

```powershell
python "E:/Program Files/git/ObsCardAnalyzer/src/main.py" --source 0 --server http://127.0.0.1:5000 --game auto

# or force Pokemon lookups
python "E:/Program Files/git/ObsCardAnalyzer/src/main.py" --source 0 --game pokemon
```

3. In OBS, add a Browser Source with the URL `http://127.0.0.1:5000/overlay`.
	 - Set the Browser Source dimensions to match your intended overlay area (e.g., 400x200).
	 - Enable "Shutdown source when not visible" if you want the overlay to stop when hidden.
	 - If you want a transparent overlay, enable CSS transparency in the Browser Source and set the OBS window to allow transparency.

CLI flags

- `--source` — camera index (0,1,...) or path/URL of a video file/stream.
- `--server` — overlay server URL (default: `http://127.0.0.1:5000`).
- `--game` — `auto`|`magic`|`pokemon` — which API to prefer. Default `auto` tries Scryfall first, then PokéTCG.

Outputs and artifacts

- `src/processed_cards.json` — persistent list of processed card lookup records (most recent first).
- `src/card_cache.json` — simple cache used by the API client to avoid repeated lookups.

How it works (short)

1. `src/main.py` captures frames using OpenCV. It locates card-like contours and uses a perspective transform to produce a normalized card image (`src/card_detector.py`).
2. `src/ocr.py` attempts to read the card name from the top portion of the card (where names are typically printed) and falls back to full-card OCR.
3. Detected names are queued and processed by a background `Worker` thread which uses `src/cardmarket_client.py` to lookup data.
4. Results are persisted and posted to the Flask overlay at `/api/update`; the overlay polls `/api/latest` to display recent cards.

Troubleshooting

- Camera errors (OpenCV MSMF warnings, cannot grab frame):
	- Ensure no other app (OBS, browser, Teams/Zoom) has exclusive access to the camera.
	- Try a different camera index (`--source 1`).
	- On Windows prefer DirectShow backend; the application already tries `CAP_DSHOW` fallback. You can also test with a video file to confirm the rest of the pipeline.
	- Check Windows Settings → Privacy → Camera to ensure apps have camera access and that your terminal/Python can access it.

- Tesseract errors: install the Windows build and add `tesseract.exe` to your PATH. Verify with:

```powershell
tesseract --version
```

- PokéTCG timeouts or failures:
	- Set `POKEMON_TCG_KEY` to your API key. The client prefers the SDK (`pokemontcgsdk`) if present.
	- Network issues or API outages can cause read timeouts; the client uses retries with backoff and a persistent cache.

Notes and next steps

- This prototype uses a simple contour detector. For reliable detection in a real stream (varying angles, occlusion) consider a trained object detector (YOLOv8, Faster R-CNN) to produce tighter crops for OCR.
- OCR accuracy varies with fonts and artwork. If OCR fails often, consider training a small OCR model or using template/template-matching to locate the name text region more precisely per game/card style.
- The overlay is intentionally simple HTML/JS. You can style it or extend it to show more fields and nicer layouts.

Development

Run tests or quick checks by executing small scripts against `src/cardmarket_client.py` or `src/server.py`. Example quick client check:

```powershell
& ".venv/Scripts/Activate.ps1"
python -c "import sys; sys.path.insert(0, 'src'); from cardmarket_client import CardmarketClient; c=CardmarketClient(); print(c.lookup_by_name('Black Lotus'))"
```

Contributing and License

This project is an early prototype. Contributions welcome — open an issue, or submit a PR with improvements, tests, or platform-specific fixes.

---

If you'd like, I can also add a short Windows Troubleshooting guide (screenshots) and example sample images/videos for testing.

Additional notes

- PokéTCG API: this prototype supports PokéTCG via the official SDK `pokemontcgsdk` or via direct REST as fallback. To use the SDK, set your API key in the environment variable `POKEMON_TCG_KEY` or pass it into the `CardmarketClient` constructor. Example:

```powershell
$env:POKEMON_TCG_KEY = 'your-key-here'
python src/main.py --game pokemon
```

- CLI `--game` flag: when running `src/main.py` you can pass `--game magic` or `--game pokemon` to prefer Scryfall (Magic) or PokéTCG respectively. The default `--game auto` will try Magic first and fall back to Pokemon.

- Caching: API results are cached in `src/card_cache.json` to reduce repeated lookups.

