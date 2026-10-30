"""Minimal GitHub REST client for the Actions runner (GITHUB_TOKEN, GITHUB_REPOSITORY)."""
import os

import requests

API = "https://api.github.com"


def _headers():
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _repo():
    return os.environ["GITHUB_REPOSITORY"]


def create_issue(title, body, labels=(), assignees=()):
    r = requests.post(f"{API}/repos/{_repo()}/issues", headers=_headers(), timeout=30,
                      json={"title": title, "body": body, "labels": list(labels), "assignees": list(assignees)})
    if r.status_code == 422 and assignees:  # assignee not allowed -> retry without it
        return create_issue(title, body, labels, ())
    r.raise_for_status()
    return r.json()


def get_issue(number):
    r = requests.get(f"{API}/repos/{_repo()}/issues/{number}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def comment(number, body):
    r = requests.post(f"{API}/repos/{_repo()}/issues/{number}/comments", headers=_headers(), timeout=30,
                      json={"body": body})
    r.raise_for_status()


def find_open_issue(title):
    r = requests.get(f"{API}/repos/{_repo()}/issues", headers=_headers(), timeout=30,
                     params={"state": "open", "per_page": 100})
    r.raise_for_status()
    return next((i for i in r.json() if i["title"] == title and "pull_request" not in i), None)
