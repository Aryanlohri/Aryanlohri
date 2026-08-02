#!/usr/bin/env python3
"""
Regenerates al-mark.svg: the glitched portrait plus a live "last commit"
line pulled from the GitHub REST API. Run manually or via the scheduled
workflow (which supplies GH_TOKEN automatically).

Uses CSS keyframe animations (not SMIL) for the reveal/fade — GitHub's
image proxy runs CSS animations reliably on embedded SVGs but generally
does not run SMIL <animate> elements.
"""

import os
import sys
import json
import base64
import urllib.request
from datetime import datetime, timezone

USERNAME = "Aryanlohri"
ROOT = os.path.join(os.path.dirname(__file__), "..")
PORTRAIT_PATH = os.path.join(ROOT, "assets", "portrait.png")
OUT_PATH = os.path.join(ROOT, "al-mark.svg")


def _headers(token):
    h = {"Accept": "application/vnd.github+json", "User-Agent": USERNAME}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_last_commit(token):
    # 1. find the most recently pushed repo
    url = f"https://api.github.com/users/{USERNAME}/repos?sort=pushed&direction=desc&per_page=1"
    req = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(req) as resp:
        repos = json.load(resp)
    if not repos:
        return None
    repo = repos[0]["name"]

    # 2. pull its latest commit on the default branch
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/commits?per_page=1"
    req = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(req) as resp:
        commits = json.load(resp)
    if not commits:
        return None

    commit = commits[0]
    message = commit["commit"]["message"].split("\n")[0]
    sha = commit["sha"][:7]
    ts = commit["commit"]["committer"]["date"]
    return repo, message, sha, ts


def relative_time(iso_ts):
    then = datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    seconds = int((now - then).total_seconds())

    if seconds < 60:
        return "JUST NOW"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}M AGO"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}H AGO"
    days = hours // 24
    if days < 30:
        return f"{days}D AGO"
    months = days // 30
    if months < 12:
        return f"{months}MO AGO"
    years = months // 12
    return f"{years}Y AGO"


def truncate(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "\u2026"


def build_svg(portrait_b64, caption):
    return f'''<svg width="320" height="320" viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" font-family="'JetBrains Mono','Courier New',monospace">
  <defs>
    <clipPath id="frame"><rect x="0" y="0" width="320" height="320"/></clipPath>
    <filter id="redTint" x="-20%" y="-20%" width="140%" height="140%">
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/>
    </filter>
    <filter id="cyanTint" x="-20%" y="-20%" width="140%" height="140%">
      <feColorMatrix type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/>
    </filter>
    <image id="portrait" width="320" height="320" preserveAspectRatio="xMidYMid slice"
      xlink:href="data:image/png;base64,{portrait_b64}"/>
  </defs>

  <style>
    .reveal {{ animation: revealIn 0.9s cubic-bezier(.16,1,.3,1) both; }}
    @keyframes revealIn {{
      0%   {{ opacity: 0; transform: translateY(-16px); }}
      100% {{ opacity: 1; transform: translateY(0); }}
    }}
    .cap {{ opacity: 0; animation: capIn 0.5s ease-out 0.8s both; }}
    @keyframes capIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .reveal, .cap {{ animation: none !important; opacity: 1 !important; transform: none !important; }}
    }}
  </style>

  <g clip-path="url(#frame)">
    <g class="reveal" style="transform-box: fill-box; transform-origin: center;">
      <rect width="320" height="320" fill="#0a0a0a"/>

      <g stroke="#161616" stroke-width="1">
        <line x1="80" y1="0" x2="80" y2="320"/>
        <line x1="160" y1="0" x2="160" y2="320"/>
        <line x1="240" y1="0" x2="240" y2="320"/>
        <line x1="0" y1="107" x2="320" y2="107"/>
        <line x1="0" y1="213" x2="320" y2="213"/>
      </g>

      <use xlink:href="#portrait" x="-4" y="0" filter="url(#redTint)" opacity="0.65"/>
      <use xlink:href="#portrait" x="4" y="0" filter="url(#cyanTint)" opacity="0.65"/>
      <use xlink:href="#portrait" x="0" y="0"/>

      <rect x="0" y="150" width="320" height="2" fill="#f5f5f5" opacity="0.05"/>
      <rect x="0" y="188" width="320" height="1" fill="#f5f5f5" opacity="0.07"/>
      <rect x="0" y="60" width="320" height="1" fill="#f5f5f5" opacity="0.05"/>

      <rect x="0" y="292" width="320" height="28" fill="#0a0a0a" opacity="0.72"/>
    </g>
  </g>

  <rect x="0.5" y="0.5" width="319" height="319" fill="none" stroke="#2a2a2a" stroke-width="1"/>
  <text class="cap" x="16" y="310" fill="#8a8a8a" font-size="10.5" letter-spacing="1.5">{caption}</text>
</svg>
'''


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    with open(PORTRAIT_PATH, "rb") as f:
        portrait_b64 = base64.b64encode(f.read()).decode()

    try:
        result = fetch_last_commit(token)
    except Exception as e:
        print(f"Could not fetch commit data: {e}", file=sys.stderr)
        result = None

    if result:
        repo, message, sha, ts = result
        caption = f"LAST COMMIT \u2014 {truncate(message, 26)} \u00b7 {relative_time(ts)}"
    else:
        caption = "LAST COMMIT \u2014 UNAVAILABLE"

    svg = build_svg(portrait_b64, caption)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT_PATH} ({caption})")


if __name__ == "__main__":
    main()
