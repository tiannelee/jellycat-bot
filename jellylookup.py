import requests
from bs4 import BeautifulSoup

BASE = "https://jellyjournal.com"

class JellyLookupError(Exception):
    pass

def lookup_jellycat_by_sku(sku: str) -> dict | None:
    """
    Look up a Jellycat on Jelly Journal by SKU.
    Returns {"sku": "OT6SDP", "name": "...", "url": "..."} or None if not found.
    Raises JellyLookupError on network / unexpected issues.
    """
    sku = sku.upper()
    url = f"{BASE}/jellycat.php"
    try:
        resp = requests.get(url, params={"sku": sku}, timeout=10)
    except requests.RequestException as e:
        raise JellyLookupError(f"Network error talking to Jelly Journal: {e}") from e

    if resp.status_code != 200:
        # Treat non-200 as "not found" instead of crashing
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    h = soup.find("h1")
    if not h:
        # No proper title = likely not a valid item page
        return None

    name = h.get_text(strip=True)

    # Extra sanity: if this is some generic error page, name will look wrong.
    # You can make this stricter if needed.
    if not name or "Jellycat Library" in name:
        return None

    return {
        "sku": sku,
        "name": name,
        "url": resp.url,
    }
