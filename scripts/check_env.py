"""Phase-1 health check: tools, env vars, Drive, Instagram, Business Discovery.

Usage: python3 scripts/check_env.py [--discovery keo.snb]
Prints no secret values.
"""
import argparse
import datetime as dt
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import gdrive, instagram as ig  # noqa: E402

ok = True


def report(name, good, detail=""):
    global ok
    ok &= good
    print(f"[{'OK ' if good else 'KO '}] {name}{' — ' + detail if detail else ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discovery", default="keo.snb")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        report(tool, bool(shutil.which(tool)), shutil.which(tool) or "install it (apt-get install -y ffmpeg)")
    report("python", sys.version_info >= (3, 10), sys.version.split()[0])
    for var in ("GDRIVE_SA_JSON", "GDRIVE_FOLDER_ID", "IG_TOKEN", "IG_USER_ID"):
        report(f"env {var}", bool(os.environ.get(var)), "set" if os.environ.get(var) else "missing")

    try:
        for name in ("inbox", "musique", "archive"):
            items = gdrive.list_children(gdrive.subfolder(name))
            report(f"Drive Insta/{name}", True, f"{len(items)} file(s)")
    except Exception as e:
        report("Drive", False, str(e)[:300])

    try:
        acc = ig.get(ig.user_id(), fields="username,media_count")
        report("Instagram account", True, f"@{acc['username']}, {acc['media_count']} media")
    except Exception as e:
        report("Instagram account", False, str(e)[:300])

    try:
        tok = os.environ["IG_TOKEN"]
        d = ig.get("debug_token", input_token=tok)["data"]
        exp = d.get("data_access_expires_at") or 0
        days = (dt.datetime.fromtimestamp(exp, dt.UTC) - dt.datetime.now(dt.UTC)).days if exp else None
        report("Token", d.get("is_valid", False),
               f"type={d.get('type')} expires_at={d.get('expires_at') or 'never'} "
               f"data_access_expires_in={days} days")
        missing = {"instagram_basic", "instagram_content_publish", "instagram_manage_insights",
                   "pages_read_engagement"} - set(d.get("scopes", []))
        report("Token scopes", not missing, "missing: " + ", ".join(missing) if missing else "all required")
    except Exception as e:
        report("Token", False, str(e)[:300])

    try:
        bd = ig.business_discovery(args.discovery, media_limit=3)
        report(f"Business Discovery @{args.discovery}", True,
               f"{bd['followers_count']} followers, {bd['media_count']} media")
    except Exception as e:
        report(f"Business Discovery @{args.discovery}", False, str(e)[:300])

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
