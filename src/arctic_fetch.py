import json
import urllib.request
import urllib.parse

BASE = "https://arctic-shift.photon-reddit.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 ArcticShiftFetcher/1.0",
    "Accept": "application/json",
}

def getpostorcomment(kind: str, id_: str):
    if kind not in {"posts", "comments"}:
        raise ValueError("kind must be 'posts' or 'comments'")

    params = urllib.parse.urlencode({"ids": id_})
    url = f"{BASE}/api/{kind}/ids?{params}"

    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))

    return data
