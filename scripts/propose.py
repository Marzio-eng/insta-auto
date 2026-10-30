"""Step 3 of the daily task: turn Claude's proposal into final media + queue file + PR.

A proposal file (written by Claude after choosing content) covers one PR: one post/reel, or all the
stories of one day.

{
  "group": "20261031-carousel",
  "items": [{
    "slot": "20261031-carousel",          # calendar slot id
    "caption": "blue hour.",
    "musique": false,
    "sons_conseilles": [{"titre": "", "artiste": "", "pourquoi": "", "passage": ""}],
    "voix": false,
    "why": "…",
    "location_id": null,
    "media": [                            # images: focus [x,y] 0..1, zoom, rotate (deg), gamma (null = auto)
      {"library_id": "m0089", "focus": [0.5, 0.5], "zoom": 1.0, "rotate": 0},
      # videos: start, duration (s), focus_x, keep_audio
      {"library_id": "m0084", "start": 0.5, "duration": 5, "focus_x": 0.6, "keep_audio": true}
    ]
  }]
}

  python3 scripts/propose.py render work/proposals/<group>.json   # media, share pages, queue files, PR body
  python3 scripts/propose.py ship   <group>                        # push media to main, push PR branch
  python3 scripts/propose.py mark   <group> <pr_number>            # calendar + library bookkeeping on main
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from lib import media  # noqa: E402
import share_page  # noqa: E402
import sync_inbox  # noqa: E402
import yaml  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work", "proposals")
CAL = os.path.join(ROOT, "data", "calendar.json")
LIB = os.path.join(ROOT, "data", "library.json")
CFG = yaml.safe_load(open(os.path.join(ROOT, "config", "accounts", "eliott.elite.yaml"), encoding="utf-8"))
MEDIA_URL = CFG["media_host"]["base_url"]
SHARE_URL = CFG["semi_auto"]["share_base_url"]
DAYS_FR = "lundi mardi mercredi jeudi vendredi samedi dimanche".split()
MONTHS_FR = "janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.".split()
SIZES = {"post": (1080, 1350), "carousel": (1080, 1350), "story": (1080, 1920), "reel": (1080, 1920)}


def load(p):
    return json.load(open(p, encoding="utf-8"))


def dump(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2 if "queue" in p or "proposals" in p else 1)
        fh.write("\n")


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def fr_when(iso):
    t = datetime.fromisoformat(iso)
    return f"{DAYS_FR[t.weekday()]} {t.day} {MONTHS_FR[t.month - 1]} · {t:%H:%M}"


def queue_name(slot):
    return f"{slot['date']}_{slot['type']}_{slot['id']}.json"


# ------------------------------------------------------------------ render

def check_reuse(spec, cal, lib):
    """2 uses max, >= 60 days apart, in a different format (config `reuse`)."""
    r = CFG["reuse"]
    errors = []
    for item in spec["items"]:
        slot = cal[item["slot"]]
        when = date.fromisoformat(slot["date"])
        for m in item["media"]:
            e = lib[m["library_id"]]
            if not e.get("usable", True):
                errors.append(f"{e['id']} is marked unusable")
            uses = [u for u in e["uses"] if u.get("status") not in ("cancelled", "late") and u.get("slot") != slot["id"]]
            if len(uses) >= r["max_uses"]:
                errors.append(f"{e['id']} already used {len(uses)} times")
            for u in uses:
                if abs((when - date.fromisoformat(u["date"])).days) < r["min_gap_days"]:
                    errors.append(f"{e['id']} used on {u['date']} (< {r['min_gap_days']} days)")
                fmt = lambda t: "feed" if t in ("post", "carousel") else t  # noqa: E731
                if r["require_different_format"] and fmt(u["format"]) == fmt(slot["type"]):
                    errors.append(f"{e['id']} already used as {u['format']}")
    if errors:
        raise SystemExit("reuse rules: " + "; ".join(errors))


def render(spec_path):
    spec = load(spec_path)
    group = spec["group"]
    stage = os.path.join(WORK, group)
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(os.path.join(stage, "queue"))
    cal = {s["id"]: s for s in load(CAL)["slots"]}
    lib = {e["id"]: e for e in load(LIB)}
    posts = []
    check_reuse(spec, cal, lib)
    for item in spec["items"]:
        slot = cal[item["slot"]]
        kind = slot["type"]
        size = SIZES[kind]
        out_media = []
        for n, m in enumerate(item["media"], 1):
            entry = lib[m["library_id"]]
            src = sync_inbox.ensure_local(entry)
            if entry["kind"] == "image":
                tmp = os.path.join(stage, f"{n}.jpg")
                media.render_image(src, tmp, size, tuple(m.get("focus", (0.5, 0.5))), m.get("zoom", 1.0),
                                   m.get("rotate", 0.0), m.get("gamma"))
                ext, mk = "jpg", "image"
            else:
                tmp = os.path.join(stage, f"{n}.mp4")
                media.render_video(src, tmp, size, m.get("start", 0), m.get("duration"), m.get("focus_x", 0.5),
                                   m.get("zoom", 1.0), m.get("gamma", 1.0), m.get("keep_audio", True))
                ext, mk = "mp4", "video"
            digest = hashlib.sha1(open(tmp, "rb").read()).hexdigest()[:6]
            name = f"{slot['id']}_{n}_{digest}.{ext}"
            shutil.move(tmp, os.path.join(ROOT, "docs", "media", name))
            out_media.append({"url": f"{MEDIA_URL}/{name}", "kind": mk, "library_id": m["library_id"],
                              "render": {k: v for k, v in m.items() if k != "library_id"}})
        post = {"id": slot["id"], "account": CFG["handle"], "type": kind if len(out_media) > 1 or kind != "carousel" else "post",
                "scheduled_at": slot["scheduled_at"], "caption": item.get("caption", ""),
                "media": out_media, "musique": bool(item["musique"]), "voix": bool(item.get("voix")),
                "sons_conseilles": item.get("sons_conseilles", []) if item["musique"] else [],
                "library_ids": [m["library_id"] for m in item["media"]], "why": item.get("why", "")}
        if item.get("location_id"):
            post["location_id"] = item["location_id"]
        if post["musique"]:
            post["share_page"] = f"{SHARE_URL}/{slot['id']}.html"
            with open(os.path.join(ROOT, "docs", "share", f"{slot['id']}.html"), "w", encoding="utf-8") as fh:
                fh.write(share_page.render(post))
        dump(os.path.join(stage, "queue", queue_name(slot)), post)
        posts.append((slot, post))
    write_pr(stage, group, posts, lib)
    print("rendered", group, "->", stage)


def write_pr(stage, group, posts, lib):
    first = posts[0][1]
    stories = first["type"] == "story"
    if stories:
        t = datetime.fromisoformat(first["scheduled_at"])
        title = f"Stories du {DAYS_FR[t.weekday()]} {t.day} {MONTHS_FR[t.month - 1]} ({len(posts)})"
    else:
        label = {"post": "Post", "carousel": "Carrousel", "reel": "Reel"}[first["type"]]
        title = f"{label} · {fr_when(first['scheduled_at'])} · « {first['caption'] or '—'} »"
    deadline = min(datetime.fromisoformat(p["scheduled_at"]) for _, p in posts)
    lines = []
    for slot, p in posts:
        mode = "🎵 **Semi-auto** : tu publies toi-même avec le son" if p["musique"] else "🤖 **Auto** : publié par l'API"
        lines.append(f"### {'Story' if stories else ''} {fr_when(p['scheduled_at'])}  \n{mode}\n")
        imgs = []
        for m in p["media"]:
            if m["kind"] == "image":
                imgs.append(f'<img src="{m["url"]}" width="{180 if stories else 220}">')
            else:
                imgs.append(f'🎬 [vidéo]({m["url"]})')
        lines.append(" ".join(imgs) + "\n")
        lines.append(f"**Légende** : {('`' + p['caption'] + '`') if p['caption'] else '_(aucune)_'}\n")
        if p["musique"]:
            lines.append(f"**Page de partage** : {p['share_page']}\n")
            if p["sons_conseilles"]:
                lines.append("**Sons conseillés** :\n" + "\n".join(
                    f"{i}. **{s['titre']}** — {s['artiste']}{' (passage ' + s['passage'] + ')' if s.get('passage') else ''} — _{s['pourquoi']}_"
                    for i, s in enumerate(p["sons_conseilles"], 1)) + "\n")
        if p["voix"]:
            lines.append("🎙️ Parole détectée : son d'origine conservé.\n")
        lines.append(f"**Pourquoi** : {p['why']}\n")
        lines.append("<sub>Médias : " + ", ".join(f"`{i}` {lib[i]['description']['summary']}" for i in p["library_ids"]) + "</sub>\n")
    limit = deadline - timedelta(hours=CFG["cadence"]["approval_deadline_hours"])
    body = (f"**Merge = validation.** À valider avant **{fr_when(limit.isoformat())}** "
            f"(2 h avant), sinon pas de publication.\n\n" + "\n".join(lines) +
            f"\n---\nFichier(s) : " + ", ".join(f"`queue/{queue_name(s)}`" for s, _ in posts) +
            "\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n")
    with open(os.path.join(stage, "pr.md"), "w", encoding="utf-8") as fh:
        fh.write(body)
    with open(os.path.join(stage, "title.txt"), "w", encoding="utf-8") as fh:
        fh.write(title)


# ------------------------------------------------------------------ ship / mark

def ship(group):
    stage = os.path.join(WORK, group)
    git("checkout", "main")
    git("pull", "--rebase", "origin", "main")
    git("add", "docs/media", "docs/share")
    if git("diff", "--cached", "--name-only"):
        git("commit", "-m", f"media: {group}")
        git("push", "origin", "main")
    branch = f"prop/{group}"
    git("checkout", "-B", branch, "main")
    for f in os.listdir(os.path.join(stage, "queue")):
        shutil.copy(os.path.join(stage, "queue", f), os.path.join(ROOT, "queue", f))
        git("add", os.path.join("queue", f))
    git("commit", "-m", open(os.path.join(stage, "title.txt"), encoding="utf-8").read())
    git("push", "-f", "-u", "origin", branch)
    git("checkout", "main")
    print("branch", branch, "| title:", open(os.path.join(stage, "title.txt"), encoding="utf-8").read())
    print("body:", os.path.join(stage, "pr.md"))


def mark(group, pr):
    stage = os.path.join(WORK, group)
    cal = load(CAL)
    lib = load(LIB)
    byid = {e["id"]: e for e in lib}
    for f in os.listdir(os.path.join(stage, "queue")):
        post = load(os.path.join(stage, "queue", f))
        for s in cal["slots"]:
            if s["id"] == post["id"]:
                s.update(status="proposed", pr=int(pr), musique=post["musique"], library_ids=post["library_ids"])
        for lid in post["library_ids"]:
            byid[lid]["uses"].append({"format": post["type"], "date": post["scheduled_at"][:10],
                                      "slot": post["id"], "status": "proposed", "pr": int(pr)})
    dump(CAL, cal)
    dump(LIB, lib)
    git("add", "data/calendar.json", "data/library.json")
    git("commit", "-m", f"plan: {group} proposed in PR #{pr}")
    git("push", "origin", "main")


if __name__ == "__main__":
    {"render": lambda: render(sys.argv[2]), "ship": lambda: ship(sys.argv[2]),
     "mark": lambda: mark(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
