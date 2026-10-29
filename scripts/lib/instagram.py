"""Instagram Graph API (Instagram API with Facebook Login, host graph.facebook.com).

Credentials come from IG_TOKEN / IG_USER_ID only; never log or persist the token.
"""
import os
import time

import requests

GRAPH_VERSION = os.environ.get("IG_GRAPH_VERSION", "v26.0")
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


class GraphError(RuntimeError):
    pass


def _call(method, path, **params):
    params["access_token"] = os.environ["IG_TOKEN"]
    r = requests.request(method, f"{BASE}/{path}", params=params, timeout=60)
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:500]}
    if r.status_code >= 400 or "error" in body:
        err = body.get("error", body)
        raise GraphError(f"{method} /{path} -> HTTP {r.status_code}: {err}")
    return body


def get(path, **params):
    return _call("GET", path, **params)


def post(path, **params):
    return _call("POST", path, **params)


def user_id():
    return os.environ["IG_USER_ID"]


def account_info():
    return get(user_id(), fields="username,media_count,followers_count")


def business_discovery(username, media_limit=12):
    fields = (f"business_discovery.username({username}){{username,name,biography,followers_count,"
              f"follows_count,media_count,media.limit({media_limit}){{id,caption,media_type,media_product_type,"
              f"timestamp,like_count,comments_count,permalink}}}}")
    return get(user_id(), fields=fields)["business_discovery"]


def create_container(**params):
    return post(f"{user_id()}/media", **params)["id"]


def container_status(container_id):
    return get(container_id, fields="status_code,status")


def wait_ready(container_id, timeout=600, every=10):
    deadline = time.time() + timeout
    while True:
        st = container_status(container_id)
        if st.get("status_code") == "FINISHED":
            return st
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise GraphError(f"container {container_id} {st}")
        if time.time() > deadline:
            raise GraphError(f"container {container_id} not ready after {timeout}s: {st}")
        time.sleep(every)


def publish(container_id):
    return post(f"{user_id()}/media_publish", creation_id=container_id)["id"]
