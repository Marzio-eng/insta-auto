"""Google Drive access through a service account (GDRIVE_SA_JSON / GDRIVE_FOLDER_ID).

The key JSON is only ever read from the environment, never written to disk.
"""
import base64
import json
import os
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

SCOPE = "https://www.googleapis.com/auth/drive"
API = "https://www.googleapis.com/drive/v3"
FOLDER_MIME = "application/vnd.google-apps.folder"

_token = {"value": None, "exp": 0}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def access_token() -> str:
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    sa = json.loads(os.environ["GDRIVE_SA_JSON"])
    now = int(time.time())
    header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = _b64(json.dumps({
        "iss": sa["client_email"], "scope": SCOPE, "aud": sa["token_uri"],
        "iat": now, "exp": now + 3600,
    }).encode())
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = key.sign(f"{header}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256())
    r = requests.post(sa["token_uri"], data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": f"{header}.{claims}.{_b64(sig)}",
    }, timeout=30)
    r.raise_for_status()
    body = r.json()
    _token.update(value=body["access_token"], exp=now + body.get("expires_in", 3600))
    return _token["value"]


def _get(path, **params):
    params.setdefault("supportsAllDrives", "true")
    r = requests.get(f"{API}/{path}", params=params,
                     headers={"Authorization": f"Bearer {access_token()}"}, timeout=60)
    r.raise_for_status()
    return r.json()


def list_children(folder_id, folders_only=False):
    q = f"'{folder_id}' in parents and trashed = false"
    if folders_only:
        q += f" and mimeType = '{FOLDER_MIME}'"
    files, page = [], None
    while True:
        body = _get("files", q=q, pageSize=1000, pageToken=page or "",
                    includeItemsFromAllDrives="true",
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, md5Checksum)")
        files += body["files"]
        page = body.get("nextPageToken")
        if not page:
            return files


def subfolder(name, parent=None):
    parent = parent or os.environ["GDRIVE_FOLDER_ID"]
    for f in list_children(parent, folders_only=True):
        if f["name"] == name:
            return f["id"]
    raise LookupError(f"Drive folder '{name}' not found under {parent}")


def download(file_id, dest):
    with requests.get(f"{API}/files/{file_id}", params={"alt": "media", "supportsAllDrives": "true"},
                      headers={"Authorization": f"Bearer {access_token()}"}, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)


def move(file_id, src_folder, dst_folder):
    r = requests.patch(f"{API}/files/{file_id}",
                       params={"addParents": dst_folder, "removeParents": src_folder,
                               "supportsAllDrives": "true"},
                       headers={"Authorization": f"Bearer {access_token()}"}, timeout=60)
    r.raise_for_status()
