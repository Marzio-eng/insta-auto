"""Create an Instagram media container from a public JPEG URL WITHOUT publishing it.

Usage: python3 scripts/test_container.py <image_url>
An unpublished container simply expires after 24 h.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import instagram as ig  # noqa: E402

url = sys.argv[1]
cid = ig.create_container(image_url=url, caption="test — not published")
print("container id:", cid)
print("status:", ig.wait_ready(cid, timeout=120, every=5))
print("NOT published (media_publish was not called).")
