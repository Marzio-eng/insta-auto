"""Step 1 of the daily task: pull new files from Drive Insta/inbox and register them.

  python3 scripts/sync_inbox.py download   # fetch inbox -> work/inbox, add stub entries to data/library.json
  python3 scripts/sync_inbox.py previews   # contact sheets in work/previews for Claude to look at
  python3 scripts/sync_inbox.py archive    # move every *described* inbox file to Insta/archive

Descriptions (place, mood, category, quality, usage ideas) are written by Claude after looking
at the previews; `archive` only moves files whose library entry has a description.
"""
import concurrent.futures as cf
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from lib import gdrive, media  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "data", "library.json")
WORK = os.path.join(ROOT, "work")
INBOX_DIR = os.path.join(WORK, "inbox")
PREVIEWS = os.path.join(WORK, "previews")


def load_lib():
    return json.load(open(LIB, encoding="utf-8"))


def save_lib(lib):
    with open(LIB, "w", encoding="utf-8") as fh:
        json.dump(lib, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def local_path(entry):
    return os.path.join(INBOX_DIR, f"{entry['id']}{os.path.splitext(entry['source_name'])[1].lower()}")


def ensure_local(entry):
    """Download the original from Drive (inbox or archive) if not cached."""
    path = local_path(entry)
    if not os.path.exists(path):
        os.makedirs(INBOX_DIR, exist_ok=True)
        gdrive.download(entry["drive_id"], path + ".part")
        os.rename(path + ".part", path)
    return path


def download():
    lib = load_lib()
    known_md5 = {e["md5"]: e for e in lib}
    known_drive = {e["drive_id"] for e in lib}
    files = gdrive.list_children(gdrive.subfolder("inbox"))
    new, dupes = [], []
    for f in sorted(files, key=lambda x: x["name"]):
        if f["id"] in known_drive or media.kind(f["name"]) is None:
            continue
        if f.get("md5Checksum") in known_md5:
            dupes.append(f)
            known_md5[f["md5Checksum"]].setdefault("duplicate_drive_ids", []).append(f["id"])
            continue
        n = sum(1 for e in lib if e["id"].startswith("m")) + len(new) + 1
        entry = {"id": f"m{n:04d}", "source_name": f["name"], "drive_id": f["id"], "md5": f.get("md5Checksum"),
                 "kind": media.kind(f["name"]), "size_mb": round(int(f.get("size", 0)) / 1e6, 1),
                 "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "drive_folder": "inbox",
                 "description": None, "uses": []}
        new.append(entry)
        known_md5[entry["md5"]] = entry

    def fetch(entry):
        path = ensure_local(entry)
        try:
            meta = media.image_meta(path) if entry["kind"] == "image" else media.video_meta(path)
            if entry["kind"] == "image":
                img = media.load_image(path)
                meta.update(luma=media.luma_stats(img), sharpness=media.sharpness(img))
            elif meta.get("has_audio"):
                meta["audio"] = media.speech_score(path)
        except Exception as e:  # keep going, flag the file
            meta = {"error": f"{type(e).__name__}: {e}"}
        entry["meta"] = meta
        return entry

    with cf.ThreadPoolExecutor(8) as pool:
        for i, entry in enumerate(pool.map(fetch, new), 1):
            if i % 25 == 0:
                print(f"  {i}/{len(new)}")
    lib += new
    save_lib(lib)
    print(f"new: {len(new)}, duplicates skipped: {len(dupes)}, library size: {len(lib)}")


def previews(only_undescribed=True, per_sheet=12):
    """Labelled contact sheets: 4 columns, images as-is, videos as 3 frames side by side."""
    from PIL import Image, ImageDraw
    lib = [e for e in load_lib() if not only_undescribed or not e.get("description")]
    os.makedirs(PREVIEWS, exist_ok=True)
    tiles = []
    for e in lib:
        path = ensure_local(e)
        try:
            if e["kind"] == "image":
                im = media.load_image(path)
                im.thumbnail((360, 360))
            else:
                d = e["meta"].get("duration") or 1
                frames = media.video_frames(path, [d * 0.1, d * 0.5, d * 0.9], width=200)
                h = max(f.height for f in frames)
                im = Image.new("RGB", (sum(f.width for f in frames) + 4 * (len(frames) - 1), h), "black")
                x = 0
                for f in frames:
                    im.paste(f, (x, 0))
                    x += f.width + 4
                im.thumbnail((360, 360))
        except Exception as ex:
            im = Image.new("RGB", (360, 200), "gray")
            ImageDraw.Draw(im).text((10, 90), str(ex)[:50], fill="white")
        tiles.append((e, im))
    sheets = []
    for s in range(0, len(tiles), per_sheet):
        chunk = tiles[s:s + per_sheet]
        cols, cw, chh = 4, 370, 400
        sheet = Image.new("RGB", (cols * cw, ((len(chunk) - 1) // cols + 1) * chh), (20, 20, 20))
        dr = ImageDraw.Draw(sheet)
        for i, (e, im) in enumerate(chunk):
            x, y = (i % cols) * cw + 5, (i // cols) * chh + 5
            sheet.paste(im, (x, y + 30))
            m = e.get("meta", {})
            label = f"{e['id']} {e['kind'][0].upper()} {m.get('width')}x{m.get('height')}"
            if e["kind"] == "video":
                label += f" {m.get('duration')}s v{m.get('audio', {}).get('voice_ratio', '-')}"
            dr.text((x, y + 4), label, fill=(255, 220, 160))
            dr.text((x, y + 16), (m.get("taken_at") or "")[:16], fill=(170, 170, 170))
        out = os.path.join(PREVIEWS, f"sheet_{s // per_sheet + 1:02d}.jpg")
        sheet.save(out, quality=80)
        sheets.append(out)
    print("\n".join(sheets))


def archive():
    lib = load_lib()
    inbox, arch = gdrive.subfolder("inbox"), gdrive.subfolder("archive")
    moved = 0
    for e in lib:
        if e.get("drive_folder") == "inbox" and e.get("description"):
            for fid in [e["drive_id"], *e.get("duplicate_drive_ids", [])]:
                gdrive.move(fid, inbox, arch)
            e["drive_folder"] = "archive"
            moved += 1
    save_lib(lib)
    print(f"moved to archive: {moved}")


if __name__ == "__main__":
    {"download": download, "previews": previews, "archive": archive}[sys.argv[1]]()
