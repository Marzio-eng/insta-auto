"""Step 2 of the daily task: extend data/calendar.json to the next 14 days.

Days already planned are kept (their slots may be proposed / queued / published); only missing days are
added. Content is NOT chosen here: Claude assigns media to slots when proposing them.

  python3 scripts/plan_calendar.py            # extend + validate
  python3 scripts/plan_calendar.py --check    # validate only (exit 1 on a rule violation)
"""
import argparse
import json
import os
import random
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL = os.path.join(ROOT, "data", "calendar.json")
FEED = ("post", "carousel", "reel")


def cfg(account="eliott.elite"):
    return yaml.safe_load(open(os.path.join(ROOT, "config", "accounts", f"{account}.yaml"), encoding="utf-8"))


def hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def natural_minute(lo, hi, rng):
    """Random minute of day in [lo, hi], never on :00/:15/:30/:45."""
    while True:
        t = rng.randint(lo, hi)
        if t % 15:
            return t


def story_times(n, lo, hi, gap, rng):
    for _ in range(500):
        ts = sorted(natural_minute(lo, hi, rng) for _ in range(n))
        if all(b - a >= gap for a, b in zip(ts, ts[1:])):
            return ts
    raise RuntimeError("cannot place stories")


def iso(day, minute, tz):
    return datetime.combine(day, time(minute // 60, minute % 60), tz).isoformat()


def feed_days_for_week(week_days, c, rng, today):
    """Choose feed days/types for the given ISO-week days (only the ones still to plan)."""
    days = [d for d in week_days]
    share = len(days) / 7
    n_posts = round(rng.randint(*c["cadence"]["posts"]["per_week"]) * share)
    n_reels = round(c["cadence"]["reels"]["per_week"] * share)
    n_posts = min(n_posts, len(days) - min(n_reels, len(days)))
    picked = rng.sample(days, min(len(days), n_posts + n_reels))
    kinds = ["reel"] * n_reels + ["carousel"] * n_posts
    rng.shuffle(kinds)
    return dict(zip(sorted(picked), kinds))


def music_ratio_problems(slots, c):
    """Rolling 7-day windows where stories with music < minimum."""
    m = c["music"]
    stories = [s for s in slots if s["type"] == "story" and s.get("status") != "cancelled"]
    if not stories:
        return []
    days = sorted({s["date"] for s in stories})
    bad = []
    for d in days:
        d0 = date.fromisoformat(d)
        win = [s for s in stories if d0 <= date.fromisoformat(s["date"]) < d0 + timedelta(days=m["stories_ratio_window_days"])]
        if len({s["date"] for s in win}) < m["stories_ratio_window_days"]:
            continue  # incomplete window at the end of the horizon
        r = sum(1 for s in win if s["musique"]) / len(win)
        if r < m["stories_min_with_music"]:
            bad.append((d, round(r, 2)))
    return bad


def validate(slots, c):
    errors = []
    by_day = {}
    for s in slots:
        if s.get("status") == "cancelled":
            continue
        by_day.setdefault(s["date"], []).append(s)
    for d, ss in sorted(by_day.items()):
        feed = [s for s in ss if s["type"] in FEED]
        if len(feed) > c["cadence"]["max_feed_per_day"] and not all(s.get("exception") for s in feed[1:]):
            errors.append(f"{d}: {len(feed)} feed items")
        st = sorted(hm(s["time"]) for s in ss if s["type"] == "story")
        if any(b - a < c["cadence"]["stories"]["min_gap_hours"] * 60 for a, b in zip(st, st[1:])):
            errors.append(f"{d}: stories closer than {c['cadence']['stories']['min_gap_hours']} h")
        for s in ss:
            if hm(s["time"]) % 60 == 0:
                errors.append(f"{s['id']}: round hour")
            if s["type"] == "reel" and not s["musique"] and not s.get("voix"):
                errors.append(f"{s['id']}: reel without music (only allowed when Eliott talks)")
    errors += [f"stories with music {r:.0%} < {c['music']['stories_min_with_music']:.0%} in week from {d}"
               for d, r in music_ratio_problems(slots, c)]
    return errors


def extend(cal, c, today, rng):
    tz = ZoneInfo(c["timezone"])
    horizon = [today + timedelta(days=i) for i in range(c["cadence"]["planning_horizon_days"])]
    planned = {s["date"] for s in cal["slots"]}
    todo = [d for d in horizon if d.isoformat() not in planned]
    now_min = datetime.now(tz).hour * 60 + datetime.now(tz).minute
    weeks = {}
    for d in todo:
        weeks.setdefault(d.isocalendar()[:2], []).append(d)
    st = c["cadence"]["stories"]
    for _, days in sorted(weeks.items()):
        feed = feed_days_for_week(days, c, rng, today)
        for d in days:
            lo = hm(st["window"][0])
            if d == today:
                lo = max(lo, now_min + 180)  # leave time to review the PR
            hi = hm(st["window"][1])
            n = rng.randint(*st["per_day"])
            while n and (hi - lo) < (n - 1) * st["min_gap_hours"] * 60:
                n -= 1
            for k, t in enumerate(story_times(n, lo, hi, st["min_gap_hours"] * 60, rng) if n else []):
                cal["slots"].append({"id": f"{d:%Y%m%d}-story{k + 1}", "date": d.isoformat(), "type": "story",
                                     "time": f"{t // 60:02d}:{t % 60:02d}", "scheduled_at": iso(d, t, tz),
                                     "musique": rng.random() < 0.8, "status": "planned"})
            if d in feed:
                flo, fhi = (hm(x) for x in c["cadence"]["feed_window"])
                if d == today:
                    flo = max(flo, now_min + 180)
                if flo <= fhi:
                    t = natural_minute(flo, fhi, rng)
                    kind = feed[d]
                    cal["slots"].append({"id": f"{d:%Y%m%d}-{kind}", "date": d.isoformat(), "type": kind,
                                         "time": f"{t // 60:02d}:{t % 60:02d}", "scheduled_at": iso(d, t, tz),
                                         "musique": kind == "reel", "status": "planned"})
    # enforce the music ratio by flipping planned stories to "with music"
    for _ in range(200):
        bad = music_ratio_problems(cal["slots"], c)
        if not bad:
            break
        d0 = date.fromisoformat(bad[0][0])
        cand = [s for s in cal["slots"] if s["type"] == "story" and not s["musique"] and s["status"] == "planned"
                and d0 <= date.fromisoformat(s["date"]) < d0 + timedelta(days=7)]
        if not cand:
            break
        rng.choice(cand)["musique"] = True
    cal["slots"].sort(key=lambda s: s["scheduled_at"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--from", dest="start", help="first day to plan (YYYY-MM-DD), default today")
    a = ap.parse_args()
    c = cfg()
    cal = json.load(open(CAL, encoding="utf-8"))
    tz = ZoneInfo(c["timezone"])
    today = datetime.now(tz).date()
    if a.start:
        today = max(today, date.fromisoformat(a.start))
    if not a.check:
        # drop past days that never went anywhere
        cal["slots"] = [s for s in cal["slots"] if s["date"] >= today.isoformat() or s["status"] != "planned"]
        extend(cal, c, today, random.Random(a.seed))
        cal["generated_at"] = datetime.now(tz).isoformat(timespec="seconds")
        with open(CAL, "w", encoding="utf-8") as fh:
            json.dump(cal, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    upcoming = [s for s in cal["slots"] if s["date"] >= today.isoformat()]
    errs = validate(upcoming, c)
    kinds = {}
    for s in upcoming:
        kinds[s["type"]] = kinds.get(s["type"], 0) + 1
    st = [s for s in upcoming if s["type"] == "story"]
    print(f"{len(upcoming)} slots / {len({s['date'] for s in upcoming})} days:", kinds,
          f"| stories with music {sum(s['musique'] for s in st)}/{len(st)}")
    for e in errs:
        print("RULE:", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
