"""Publisher, run every 15 min by .github/workflows/publish.yml.

For every queue/*.json whose time has come:
  - "musique": false -> publish through the Instagram API, move to published/ with the media id;
  - "musique": true  -> open an issue assigned to Eliott with the share-page link, move to queue/manual/.
For every queue/manual/*.json whose issue is closed: find the post Eliott made by hand and record it.

Never publishes a file merged less than `approval_deadline_hours` before its time (it goes to queue/late/,
the daily task reschedules it). Changes are written to disk; the workflow commits them.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import requests
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from lib import github, instagram as ig  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE, MANUAL, LATE, FAILED = (os.path.join(ROOT, "queue", d) for d in ("", "manual", "late", "failed"))
PUBLISHED = os.path.join(ROOT, "published")
MAX_ATTEMPTS = 4          # first try + 3 retries
STALE_AFTER = timedelta(hours=3)   # missed by more than this -> not published (e.g. a story at 3 am)
SAFARI_LINE = "👉 Appui long sur le lien → Ouvrir dans Safari"

log = lambda *a: print(datetime.now(timezone.utc).strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def now():
    return datetime.now(timezone.utc)


def config(account):
    return yaml.safe_load(open(os.path.join(ROOT, "config", "accounts", f"{account}.yaml"), encoding="utf-8"))


def load(path):
    return json.load(open(path, encoding="utf-8"))


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def move(src, dest_dir, data):
    save(os.path.join(dest_dir, os.path.basename(src)), data)
    os.remove(src)


def approved_at(path):
    """When the file reached main: committer date of the first-parent commit that added it (= the merge)."""
    rel = os.path.relpath(path, ROOT)
    out = subprocess.run(["git", "log", "--first-parent", "-m", "--diff-filter=A", "--format=%cI", "--", rel],
                         cwd=ROOT, capture_output=True, text=True).stdout.split()
    return datetime.fromisoformat(out[-1]) if out else None


def media_online(urls):
    for u in urls:
        try:
            r = requests.head(u, timeout=20, allow_redirects=True)
        except requests.RequestException:
            return False
        if r.status_code != 200:
            return False
    return True


# ------------------------------------------------------------------ API publishing

def _child(item, carousel=False, story=False):
    p = {"video_url": item["url"], "media_type": "STORIES" if story else "VIDEO"} if item["kind"] == "video" \
        else {"image_url": item["url"]}
    if story and item["kind"] != "video":
        p["media_type"] = "STORIES"
    if carousel:
        p["is_carousel_item"] = "true"
    return p


def create_container(post):
    media, kind = post["media"], post["type"]
    extra = {k: post[k] for k in ("location_id",) if post.get(k)}
    if kind == "story":
        return ig.create_container(**_child(media[0], story=True))
    if kind == "reel":
        p = {"media_type": "REELS", "video_url": media[0]["url"], "caption": post.get("caption", ""),
             "share_to_feed": "true", **extra}
        if post.get("cover_url"):
            p["cover_url"] = post["cover_url"]
        return ig.create_container(**p)
    if kind == "post" or len(media) == 1:
        return ig.create_container(image_url=media[0]["url"], caption=post.get("caption", ""), **extra)
    # carousel: children first, each must be FINISHED
    children = []
    for item in media:
        cid = ig.create_container(**_child(item, carousel=True))
        ig.wait_ready(cid, timeout=600)
        children.append(cid)
    return ig.create_container(media_type="CAROUSEL", children=",".join(children),
                               caption=post.get("caption", ""), **extra)


def publish_api(path, post):
    if not post.get("ig_media_id"):
        cid = post.get("container_id")
        if not cid:
            cid = create_container(post)
            post["container_id"] = cid
            save(path, post)
        ig.wait_ready(cid, timeout=900)
        post["ig_media_id"] = ig.publish(cid)
        post["published_at"] = now().isoformat(timespec="seconds")
        save(path, post)   # persist at once: a crash after this point must never publish twice
    info = ig.get(post["ig_media_id"], fields="permalink,timestamp")
    post["permalink"] = info.get("permalink")
    log("published", os.path.basename(path), post["ig_media_id"], post.get("permalink"))
    move(path, PUBLISHED, post)
    drop_heavy_media(post)


def drop_heavy_media(post):
    """Videos are only needed until Instagram has fetched them; images stay (light, used in PR previews)."""
    still_needed = set()
    for f in glob.glob(os.path.join(QUEUE, "**", "*.json"), recursive=True):
        still_needed |= {m["url"] for m in load(f).get("media", [])}
    for m in post.get("media", []):
        if m["kind"] == "video" and m["url"] not in still_needed:
            local = os.path.join(ROOT, "docs", "media", m["url"].split("/media/", 1)[1].split("?")[0])
            if os.path.exists(local):
                os.remove(local)
                log("removed", os.path.relpath(local, ROOT))


def fail(path, post, err, cfg):
    post["attempts"] = post.get("attempts", 0) + 1
    post.setdefault("errors", []).append({"at": now().isoformat(timespec="seconds"), "error": str(err)[:1500]})
    log("error", os.path.basename(path), f"attempt {post['attempts']}/{MAX_ATTEMPTS}:", err)
    if post["attempts"] < MAX_ATTEMPTS:
        save(path, post)
        return
    title = f"❌ Échec de publication : {post['id']}"
    body = (f"La publication **{post['id']}** ({post['type']}, prévue {post['scheduled_at']}) a échoué "
            f"{MAX_ATTEMPTS} fois. Elle est déplacée dans `queue/failed/`.\n\n"
            f"Dernière erreur exacte :\n```\n{err}\n```\n\nHistorique :\n"
            + "\n".join(f"- {e['at']} — `{e['error'][:300]}`" for e in post["errors"])
            + f"\n\nRun : {os.environ.get('RUN_URL', '-')}")
    issue = github.create_issue(title, body, labels=["erreur-publication"], assignees=[cfg["semi_auto"]["notify_assignee"]])
    post["issue"] = issue["number"]
    move(path, FAILED, post)


# ------------------------------------------------------------------ semi-automatic (music)

FORMAT_FR = {"story": "Story", "reel": "Reel", "post": "Publication", "carousel": "Publication"}


def notify_manual(path, post, cfg):
    when = datetime.fromisoformat(post["scheduled_at"]).strftime("%d/%m %H:%M")
    sounds = "\n".join(f"{i}. **{s['titre']}** — {s['artiste']}" + (f" (passage {s['passage']})" if s.get("passage") else "")
                       + f"\n   _{s['pourquoi']}_" for i, s in enumerate(post.get("sons_conseilles", []), 1))
    body = (f"{SAFARI_LINE}\n\n{post['share_page']}\n\n"
            f"---\n**Format** : {FORMAT_FR[post['type']]} · prévu {when}\n\n"
            f"**Légende** : {post.get('caption') or '_(aucune)_'}\n\n"
            + (f"**Sons conseillés** :\n{sounds}\n\n" if sounds else "")
            + ("🎙️ Tu parles dans la vidéo : son d'origine à 100 %, musique à ~10-20 %.\n\n" if post.get("voix") else "")
            + "Une fois publié dans Instagram, **ferme cette issue** : je retrouve la publication et je l'enregistre.")
    issue = github.create_issue(f"🎵 À publier : {FORMAT_FR[post['type']]} {when}", body,
                                labels=["publication-manuelle"], assignees=[cfg["semi_auto"]["notify_assignee"]])
    post["issue"] = issue["number"]
    post["notified_at"] = now().isoformat(timespec="seconds")
    log("notified", os.path.basename(path), "issue", issue["number"])
    move(path, MANUAL, post)


def _norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"\s+", " ", s).strip()


def find_manual_post(post):
    since = datetime.fromisoformat(post["notified_at"]) - timedelta(minutes=30)
    if post["type"] == "story":
        items = ig.get(f"{ig.user_id()}/stories", fields="id,media_type,timestamp,permalink").get("data", [])
    else:
        items = ig.get(f"{ig.user_id()}/media", fields="id,caption,media_type,media_product_type,timestamp,permalink",
                       limit=25).get("data", [])
    want = {"reel": "REELS", "story": "STORY"}.get(post["type"], "FEED")
    taken = {load(f).get("ig_media_id") for f in glob.glob(os.path.join(PUBLISHED, "*.json"))}
    cands = [m for m in items if m["id"] not in taken
             and datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")) >= since
             and (post["type"] == "story" or m.get("media_product_type", want) == want)]
    exact = [m for m in cands if post["type"] == "story" or _norm(m.get("caption")) == _norm(post.get("caption"))]
    pick = sorted(exact or cands, key=lambda m: m["timestamp"])
    return pick[0] if pick else None


def check_manual(path, post):
    issue = github.get_issue(post["issue"])
    if issue["state"] != "closed":
        return
    found = find_manual_post(post)
    if found:
        post.update(ig_media_id=found["id"], permalink=found.get("permalink"),
                    published_at=found["timestamp"], published_by="manual")
        github.comment(post["issue"], f"✅ Enregistrée : {found.get('permalink') or found['id']}")
        log("manual post recorded", os.path.basename(path), found["id"])
        move(path, PUBLISHED, post)
        drop_heavy_media(post)
        return
    post["lookups"] = post.get("lookups", 0) + 1
    if post["lookups"] >= 8:  # ~2 h after closing: give up, keep a trace
        post.update(ig_media_id=None, published_by="manual", unmatched=True)
        github.comment(post["issue"], "⚠️ Je ne retrouve pas la publication via l'API (story expirée ou légende "
                                      "modifiée ?). Enregistrée sans identifiant.")
        move(path, PUBLISHED, post)
    else:
        save(path, post)


# ------------------------------------------------------------------ main loop

def run(dry_run=False):
    for path in sorted(glob.glob(os.path.join(MANUAL, "*.json"))):
        try:
            check_manual(path, load(path))
        except Exception as e:
            log("manual check error", os.path.basename(path), e)

    for path in sorted(glob.glob(os.path.join(QUEUE, "*.json"))):
        post = load(path)
        cfg = config(post.get("account", "eliott.elite"))
        due = datetime.fromisoformat(post["scheduled_at"])
        if now() < due:
            continue
        name = os.path.basename(path)
        ok_at = approved_at(path)
        deadline = due - timedelta(hours=cfg["cadence"]["approval_deadline_hours"])
        if ok_at and ok_at > deadline:
            post["late_reason"] = f"validée {ok_at.isoformat()} après la limite {deadline.isoformat()}"
            log("late approval", name, post["late_reason"])
            move(path, LATE, post)
            continue
        if now() > due + STALE_AFTER and not post.get("container_id"):
            post["late_reason"] = f"heure dépassée de plus de {STALE_AFTER} (workflow en retard ?)"
            log("stale", name)
            move(path, LATE, post)
            continue
        if dry_run:
            log("would handle", name, "manual" if post.get("musique") else "api")
            continue
        if post.get("musique"):
            notify_manual(path, post, cfg)
            continue
        if not media_online([m["url"] for m in post["media"]]):
            log("media not online yet", name)
            continue
        try:
            publish_api(path, post)
        except Exception as e:
            fail(path, post, e, cfg)
        time.sleep(2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    run(ap.parse_args().dry_run)
