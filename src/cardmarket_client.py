import os
import time
import requests
from requests.exceptions import RequestException
from urllib.parse import quote_plus

# Try to import the official PokéTCG SDK; if present we'll prefer it for Pokemon lookups.
try:
    import pokemontcgsdk as _pokemontcgsdk
    from pokemontcgsdk import Card as _PokeCard
    SDK_AVAILABLE = True
except Exception:
    _pokemontcgsdk = None
    _PokeCard = None
    SDK_AVAILABLE = False


class CardmarketClient:
    """Client that uses free public APIs for card lookup:
    - Magic: Scryfall (https://scryfall.com/docs/api)
    - Pokemon: PokéTCG (https://pokemontcg.io/)

    The class keeps the name `CardmarketClient` to avoid changing imports elsewhere, but it
    does not contact Cardmarket; it attempts Scryfall first then falls back to PokéTCG.
    """

    def __init__(self, pokemon_api_key: str | None = None, timeout: float = 10.0, retries: int = 2):
        self.session = requests.Session()
        self.timeout = timeout
        self.retries = max(1, int(retries))
        self.pokemon_api_key = pokemon_api_key or os.environ.get("POKEMON_TCG_KEY")
        if self.pokemon_api_key:
            # PokéTCG accepts X-Api-Key header when provided
            self.session.headers.update({"X-Api-Key": self.pokemon_api_key})
        # If SDK is available, configure its API key too
        if SDK_AVAILABLE and self.pokemon_api_key:
            try:
                # SDK exposes a config object
                try:
                    _pokemontcgsdk.config.api_key = self.pokemon_api_key
                except Exception:
                    # older/newer versions may use a dict-like config
                    setattr(_pokemontcgsdk.config, 'api_key', self.pokemon_api_key)
            except Exception:
                # ignore SDK config failures and fall back to requests method
                pass

    def lookup_by_name(self, name: str, game: str | None = None) -> dict:
        """Lookup a card by name. If `game` is provided ('magic' or 'pokemon') it queries that API.
        Otherwise it tries Scryfall (Magic) first, then PokéTCG.
        Returns a dict with at minimum `found` (bool) and other game-specific fields.
        """
        name = (name or "").strip()
        if not name:
            return {"found": False, "error": "empty name"}

        if game == "pokemon":
            return self._lookup_pokemon(name)
        if game == "magic":
            return self._lookup_scryfall(name)

        # Default: try Magic (Scryfall) then Pokemon
        s = self._lookup_scryfall(name)
        if s.get("found"):
            return s
        return self._lookup_pokemon(name)

    def _lookup_scryfall(self, name: str) -> dict:
        try:
            url = f"https://api.scryfall.com/cards/named?fuzzy={quote_plus(name)}"
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code != 200:
                return {"found": False, "status": r.status_code}
            j = r.json()
            image_url = None
            if isinstance(j.get("image_uris"), dict):
                image_url = j["image_uris"].get("normal") or j["image_uris"].get("large")
            else:
                # some card objects (prints) have other structures
                image_url = None
            return {
                "found": True,
                "game": "magic",
                "name": j.get("name"),
                "set": j.get("set_name"),
                "rarity": j.get("rarity"),
                "oracle_text": j.get("oracle_text"),
                "image_url": image_url,
                "prices": j.get("prices"),
                "url": j.get("scryfall_uri"),
            }
        except Exception as exc:
            return {"found": False, "error": str(exc)}

    def _lookup_pokemon(self, name: str) -> dict:
        # Prefer using the SDK when available
        if SDK_AVAILABLE and _PokeCard is not None:
            try:
                # The SDK provides Card.where which accepts a query string or kwargs.
                # Use the quoted name query to match the REST behavior.
                q = f'name:"{name}"'
                results = _PokeCard.where(q=q)
                if not results:
                    return {"found": False}
                c = results[0]
                images = c.get("images") or {}
                return {
                    "found": True,
                    "game": "pokemon",
                    "name": c.get("name"),
                    "set": (c.get("set") or {}).get("name"),
                    "rarity": c.get("rarity"),
                    "types": c.get("types"),
                    "hp": c.get("hp"),
                    "image_url": images.get("large") or images.get("small"),
                    "url": c.get("id"),
                }
            except Exception as exc:
                # Fall back to REST method on SDK error
                pass

        # Fallback: use REST API
        url = f"https://api.pokemontcg.io/v2/cards?q=name:\"{quote_plus(name)}\""
        last_exc = None
        for attempt in range(1, self.retries + 1):
            try:
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code != 200:
                    return {"found": False, "status": r.status_code}
                j = r.json()
                data = j.get("data") or []
                if not data:
                    return {"found": False}
                c = data[0]
                images = c.get("images") or {}
                return {
                    "found": True,
                    "game": "pokemon",
                    "name": c.get("name"),
                    "set": (c.get("set") or {}).get("name"),
                    "rarity": c.get("rarity"),
                    "types": c.get("types"),
                    "hp": c.get("hp"),
                    "image_url": images.get("large") or images.get("small"),
                    "url": c.get("id"),
                }
            except RequestException as exc:
                last_exc = exc
                # simple backoff
                if attempt < self.retries:
                    time.sleep(1 * attempt)
                continue
        return {"found": False, "error": str(last_exc) if last_exc is not None else "unknown"}


if __name__ == "__main__":
    c = CardmarketClient()
    for sample in ["Black Lotus", "Pikachu"]:
        print("Query:", sample)
        print(c.lookup_by_name(sample))

