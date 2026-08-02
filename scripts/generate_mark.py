#!/usr/bin/env python3
"""
Regenerates al-mark.svg: monochrome glitched portrait plus a live
"last commit" line pulled from the GitHub REST API.

Pure grayscale, no color tint. Animation layers:
1. one-time reveal on load (CSS keyframes)
2. grain flicker — animated film-grain texture, old-camera feel
3. ambient particles — faint flecks drifting upward, dust in still air
4. contour shimmer — a soft diagonal light sweep passing over the linework
"""

import os
import sys
import json
import base64
import random
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
    url = f"https://api.github.com/users/{USERNAME}/repos?sort=pushed&direction=desc&per_page=1"
    req = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(req) as resp:
        repos = json.load(resp)
    if not repos:
        return None
    repo = repos[0]["name"]

    url = f"https://api.github.com/repos/{USERNAME}/{repo}/commits?per_page=1"
    req = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(req) as resp:
        commits = json.load(resp)
    if not commits:
        return None

    commit = commits[0]
    message = commit["commit"]["message"].split("\n")[0]
    ts = commit["commit"]["committer"]["date"]
    return repo, message, ts


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


def particles_svg():
    random.seed(42)
    parts = []
    for i in range(13):
        x = round(random.uniform(20, 300), 1)
        r = round(random.uniform(1.0, 1.7), 2)
        dur = round(random.uniform(6, 10), 2)
        delay = round(random.uniform(0, 9), 2)
        peak = round(random.uniform(0.22, 0.4), 2)
        parts.append(
            f'<circle class="particle" cx="{x}" cy="300" r="{r}" fill="#f5f5f5" '
            f'style="--peak:{peak}; animation-duration:{dur}s; animation-delay:{delay}s;"/>'
        )
    return "\n      ".join(parts)


def build_svg(portrait_b64, caption):
    particles = particles_svg()
    return f'''<svg width="320" height="320" viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" font-family="'JetBrains Mono','Courier New',monospace">
  <defs>
    <clipPath id="frame"><rect x="0" y="0" width="320" height="320"/></clipPath>
    <clipPath id="inner"><rect x="0" y="0" width="320" height="290"/></clipPath>
    <image id="portrait" width="320" height="320" preserveAspectRatio="xMidYMid slice"
      xlink:href="data:image/png;base64,{portrait_b64}"/>

    <filter id="grain1" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="3" result="n"/>
      <feColorMatrix in="n" type="saturate" values="0"/>
      <feComponentTransfer><feFuncA type="linear" slope="0.5"/></feComponentTransfer>
    </filter>
    <filter id="grain2" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="9" result="n"/>
      <feColorMatrix in="n" type="saturate" values="0"/>
      <feComponentTransfer><feFuncA type="linear" slope="0.5"/></feComponentTransfer>
    </filter>

    <linearGradient id="shimmerGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#f5f5f5" stop-opacity="0"/>
      <stop offset="50%" stop-color="#f5f5f5" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#f5f5f5" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <style>
    .reveal {{ animation: revealIn 0.9s cubic-bezier(.16,1,.3,1) both; }}
    @keyframes revealIn {{
      0%   {{ opacity: 0; transform: translateY(-16px); }}
      100% {{ opacity: 1; transform: translateY(0); }}
    }}

    .cap {{ opacity: 0; animation: capIn 0.5s ease-out 0.8s both; }}
    @keyframes capIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}

    /* grain flicker — two noise fields cross-fading fast, old-camera feel */
    .grainA {{ animation: grainFlicker 0.5s steps(1) infinite; }}
    .grainB {{ animation: grainFlicker 0.5s steps(1) infinite reverse; }}
    @keyframes grainFlicker {{ 0%, 49% {{ opacity: 0.07; }} 50%, 100% {{ opacity: 0; }} }}

    /* ambient particles — flecks drifting upward, staggered */
    .particle {{ opacity: 0; animation-name: drift; animation-timing-function: linear; animation-iteration-count: infinite; }}
    @keyframes drift {{
      0%   {{ transform: translateY(0); opacity: 0; }}
      10%  {{ opacity: var(--peak); }}
      85%  {{ opacity: var(--peak); }}
      100% {{ transform: translateY(-330px); opacity: 0; }}
    }}

    /* contour shimmer — soft diagonal light passing over the figure, on a loop */
    .shimmer {{ animation: sweep 5.5s ease-in-out infinite; mix-blend-mode: screen; }}
    @keyframes sweep {{
      0%   {{ transform: translate(-260px, -80px) rotate(24deg); opacity: 0; }}
      10%  {{ opacity: 0.5; }}
      50%  {{ opacity: 0.5; }}
      60%  {{ opacity: 0; }}
      100% {{ transform: translate(260px, 80px) rotate(24deg); opacity: 0; }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      .reveal, .cap {{ animation: none !important; opacity: 1 !important; transform: none !important; }}
      .grainA, .grainB, .particle, .shimmer {{ animation: none !important; opacity: 0 !important; }}
    }}
  </style>

  <g clip-path="url(#frame)">
    <g class="reveal">
      <rect width="320" height="320" fill="#0a0a0a"/>

      <g stroke="#161616" stroke-width="1">
        <line x1="80" y1="0" x2="80" y2="320"/>
        <line x1="160" y1="0" x2="160" y2="320"/>
        <line x1="240" y1="0" x2="240" y2="320"/>
        <line x1="0" y1="107" x2="320" y2="107"/>
        <line x1="0" y1="213" x2="320" y2="213"/>
      </g>

      <use xlink:href="#portrait" x="0" y="0"/>

      <g clip-path="url(#inner)">
        <rect class="grainA" x="0" y="0" width="320" height="320" filter="url(#grain1)" opacity="0"/>
        <rect class="grainB" x="0" y="0" width="320" height="320" filter="url(#grain2)" opacity="0"/>

        <g>
          {particles}
        </g>

        <rect class="shimmer" x="-40" y="-160" width="70" height="480" fill="url(#shimmerGrad)"/>
      </g>

      <rect x="0" y="292" width="320" height="28" fill="#0a0a0a" opacity="0.8"/>
    </g>
  </g>

  <rect x="0.5" y="0.5" width="319" height="319" fill="none" stroke="#2a2a2a" stroke-width="1"/>
  <text class="cap" x="16" y="310" fill="#8a8a8a" font-size="10.5" letter-spacing="1"
        textLength="290" lengthAdjust="spacingAndGlyphs">{caption}</text>
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
        repo, message, ts = result
        caption = f"LAST COMMIT \u2014 {truncate(message, 30)} \u00b7 {relative_time(ts)}"
    else:
        caption = "LAST COMMIT \u2014 UNAVAILABLE"

    svg = build_svg(portrait_b64, caption)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT_PATH} ({caption})")


if __name__ == "__main__":
    main()
