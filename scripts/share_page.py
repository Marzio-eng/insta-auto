"""Build the phone share page for a semi-automatic ("musique": true) publication.

Usage: python3 scripts/share_page.py <queue_or_spec.json> <out.html>
Spec keys: id, type, caption, media_url, scheduled_at (optional), sons_conseilles (optional), voix (optional).
"""
import html
import json
import os
import sys
from datetime import datetime

TEMPLATE = os.path.join(os.path.dirname(__file__), "templates", "share.html")
FORMATS = {"story": "Story", "reel": "Reel", "post": "Publication", "carousel": "Publication"}
MONTHS = "janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.".split()


def render(spec):
    media_url = spec.get("media_url") or spec["media"][0]["url"]
    when = ""
    if spec.get("scheduled_at"):
        t = datetime.fromisoformat(spec["scheduled_at"])
        when = f"{t.day} {MONTHS[t.month - 1]} · {t:%H:%M}"
    data = {
        "media_url": media_url,
        "file_name": f"{spec['id']}{os.path.splitext(media_url.split('?')[0])[1] or '.jpg'}",
        "format": FORMATS[spec["type"]],
        "caption": spec.get("caption", ""),
        "when": when,
        "sounds": [{"title": s["titre"], "artist": s["artiste"], "why": s["pourquoi"], "passage": s.get("passage", "")}
                   for s in spec.get("sons_conseilles", [])],
        "volume_hint": ("Tu parles dans la vidéo : garde le son d'origine à 100 % et baisse la musique à ~10-20 %."
                        if spec.get("voix") else ""),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (open(TEMPLATE, encoding="utf-8").read()
            .replace("__TITLE__", html.escape(f"{FORMATS[spec['type']]} · eliott.elite"))
            .replace("__DATA__", payload))


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        fh.write(render(spec))
    print("written", sys.argv[2])
