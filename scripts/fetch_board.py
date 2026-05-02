#!/usr/bin/env python3
# /// script
# dependencies = ["requests"]
# ///
"""Fetch source URLs from a Pinterest board via the Pinterest API v5.

Usage:
    PINTEREST_TOKEN=xxx python scripts/fetch_board.py <board_id>
    PINTEREST_TOKEN=xxx python scripts/fetch_board.py --list-boards

Outputs one source URL per line to stdout. Pins with no source URL are skipped.

Getting started:
    1. Go to https://developers.pinterest.com/ and create an app
    2. Under your app, generate a user access token with boards:read and pins:read scopes
    3. Run with --list-boards to find your board IDs
    4. Run with a board_id to dump all source URLs from that board
"""

import json
import os
import sys

import requests

API_BASE = "https://api.pinterest.com/v5"


def get_token():
    token = os.environ.get("PINTEREST_TOKEN")
    if not token:
        print("Error: set PINTEREST_TOKEN env var", file=sys.stderr)
        sys.exit(1)
    return token


def api_get(path, token, params=None):
    resp = requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
    )
    resp.raise_for_status()
    return resp.json()


def list_boards(token):
    bookmark = None
    while True:
        params = {"page_size": 100}
        if bookmark:
            params["bookmark"] = bookmark
        data = api_get("/boards", token, params)
        for board in data.get("items", []):
            print(f"{board['id']}\t{board['name']}")
        bookmark = data.get("bookmark")
        if not bookmark:
            break


def fetch_board_urls(board_id, token):
    bookmark = None
    seen = set()
    while True:
        params = {"page_size": 100, "fields": "id,link,title"}
        if bookmark:
            params["bookmark"] = bookmark
        data = api_get(f"/boards/{board_id}/pins", token, params)
        for pin in data.get("items", []):
            url = pin.get("link")
            if url and url not in seen:
                seen.add(url)
                print(url)
        bookmark = data.get("bookmark")
        if not bookmark:
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    token = get_token()

    if sys.argv[1] == "--list-boards":
        list_boards(token)
    else:
        fetch_board_urls(sys.argv[1], token)
