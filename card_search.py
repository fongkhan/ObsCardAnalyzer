import requests
import urllib.parse

def search_card_generic(text):
    """
    Searches for a card based on extracted text.
    Currently prioritizes Magic: The Gathering via Scryfall.
    Future: Add Pokemon/Yugioh handlers.
    """
    if not text or len(text.strip()) < 3:
        return None

    # Clean text slightly
    query = text.strip()
    
    # Try Scryfall (MTG)
    try:
        # Fuzzy search is good for OCR errors
        url = f"https://api.scryfall.com/cards/named?fuzzy={urllib.parse.quote(query)}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "game": "MTG",
                "name": data.get("name"),
                "type": data.get("type_line"),
                "set": data.get("set_name"),
                "image_url": data.get("image_uris", {}).get("border_crop") or data.get("image_uris", {}).get("normal"),
                "stats": f"{data.get('power', '')}/{data.get('toughness', '')}" if 'power' in data else ""
            }
    except Exception as e:
        print(f"Scryfall search error: {e}")

    # Try Pokemon TCG
    return search_pokemon(query)

def search_pokemon(text):
    """
    Searches Pokemon TCG API.
    """
    try:
        # Simple name search
        url = f"https://api.pokemontcg.io/v2/cards?q=name:\"{urllib.parse.quote(text)}\"&pageSize=1"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                card = data['data'][0]
                return {
                    "game": "Pokemon",
                    "name": card.get("name"),
                    "type": " ".join(card.get("types", [])) + " " + card.get("supertype", ""),
                    "set": card.get("set", {}).get("name"),
                    "image_url": card.get("images", {}).get("large") or card.get("images", {}).get("small"),
                    "stats": f"HP {card.get('hp')}" if 'hp' in card else ""
                }
    except Exception as e:
        print(f"Pokemon search error: {e}")

    return None
