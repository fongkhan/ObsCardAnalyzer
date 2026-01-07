import json
import os
import shutil
from datetime import datetime

HISTORY_FILE = "history.jsonl"
CURRENT_CARD_TXT = "current_card.txt"
CURRENT_CARD_IMG = "current_card.jpg"

def log_card_history(card_data):
    """
    Appends card data to a JSONL history file.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "card": card_data
    }
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def write_current_card(card_data, image_path=None):
    """
    Updates current_card.txt and optionally copies the card image.
    current_card.txt format:
    Name: CardName
    Type: CardType
    ...
    """
    # Write text info
    lines = []
    if card_data:
        for key, value in card_data.items():
            lines.append(f"{key}: {value}")
    else:
        lines.append("No card detected")

    with open(CURRENT_CARD_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Handle image
    if image_path and os.path.exists(image_path):
        try:
            shutil.copy(image_path, CURRENT_CARD_IMG)
        except Exception as e:
            print(f"Error copying image: {e}")
