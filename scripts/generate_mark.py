#!/usr/bin/env python3
"""
Regenerates al-mark.svg: monochrome glitched portrait plus a live
"last commit" line pulled from the GitHub REST API.

Pure grayscale, no color tint. Animation layers:
1. one-time reveal on load (CSS keyframes)
2. grain flicker — animated film-grain texture, old-camera feel
3. ambient particles — faint flecks drifting upward, dust in still air
5. pulse border glow — the frame softly breathes
6. VHS jitter — occasional quick horizontal jump on the figure only
7. typewriter caption — the commit line types itself out on a loop
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

CAPTION_X = 16
CAPTION_BOX_WIDTH = 288


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


def typewriter_timing(caption_len):
    reveal_dur = max(1.0, round(caption_len * 0.06, 2))
    hold_dur = 1.8
    gap_dur = 0.35
    total = round(reveal_dur + hold_dur + gap_dur, 2)
    reveal_pct = round(reveal_dur / total * 100, 2)
    hold_end_pct = round((reveal_dur + hold_dur) / total * 100, 2)
    steps = max(caption_len, 1)
    return total, reveal_pct, hold_end_pct, steps


def build_svg(portrait_b64, caption):
    particles = particles_svg()
    total, reveal_pct, hold_end_pct, steps = typewriter_timing(len(caption))
    cursor_x = CAPTION_X + CAPTION_BOX_WIDTH + 4
    BAR = 30
    H = 320 + BAR

    return f'''<svg width="320" height="{H}" viewBox="0 0 320 {H}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" font-family="'JetBrains Mono','Courier New',monospace">
  <defs>
    <clipPath id="frame"><rect x="0" y="0" width="320" height="320"/></clipPath>
    <clipPath id="inner"><rect x="0" y="0" width="320" height="290"/></clipPath>
    <clipPath id="capClip"><rect class="capClipRect" x="{CAPTION_X}" y="297" width="0" height="16"/></clipPath>
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
    <filter id="borderGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3"/>
    </filter>

  </defs>

  <style>
    .reveal {{ animation: revealIn 0.9s cubic-bezier(.16,1,.3,1) both; }}
    @keyframes revealIn {{
      0%   {{ opacity: 0; transform: translateY(-16px); }}
      100% {{ opacity: 1; transform: translateY(0); }}
    }}

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

    /* VHS jitter — occasional quick horizontal jump, figure only */
    .jitter {{ animation: vhsJitter 6s steps(1) infinite; }}
    @keyframes vhsJitter {{
      0%, 92%, 100% {{ transform: translateX(0); }}
      93% {{ transform: translateX(-3px); }}
      94% {{ transform: translateX(2px); }}
      95% {{ transform: translateX(-1px); }}
      96% {{ transform: translateX(0); }}
    }}

    /* pulse border glow — frame softly breathes */
    .glowRect {{ animation: glowPulse 3s ease-in-out infinite; }}
    @keyframes glowPulse {{ 0%, 100% {{ opacity: 0; }} 50% {{ opacity: 0.4; }} }}
    .borderMain {{ animation: borderPulse 3s ease-in-out infinite; }}
    @keyframes borderPulse {{ 0%, 100% {{ stroke: #2a2a2a; }} 50% {{ stroke: #565656; }} }}

    /* typewriter caption — types out, holds, resets, loops */
    .capClipRect {{ animation: typeLoop {total}s steps({steps}) infinite; }}
    @keyframes typeLoop {{
      0%    {{ width: 0; }}
      {reveal_pct}%  {{ width: {CAPTION_BOX_WIDTH}px; }}
      {hold_end_pct}% {{ width: {CAPTION_BOX_WIDTH}px; }}
      100%  {{ width: 0; }}
    }}
    .capCursor {{ animation: blink 0.9s steps(1) infinite; }}
    @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}

    @media (prefers-reduced-motion: reduce) {{
      .reveal {{ animation: none !important; opacity: 1 !important; transform: none !important; }}
      .grainA, .grainB, .particle, .jitter, .glowRect, .borderMain, .capCursor {{ animation: none !important; }}
      .capClipRect {{ animation: none !important; width: {CAPTION_BOX_WIDTH}px !important; }}
    }}
  </style>

  <rect width="320" height="{H}" fill="#0a0a0a"/>

  <!-- terminal title bar -->
  <rect x="0" y="0" width="320" height="{BAR}" fill="#111111"/>
  <line x1="0" y1="{BAR}" x2="320" y2="{BAR}" stroke="#2a2a2a" stroke-width="1"/>
  <circle cx="16" cy="15" r="4.5" fill="#4a4a4a"/>
  <circle cx="30" cy="15" r="4.5" fill="#4a4a4a"/>
  <circle cx="44" cy="15" r="4.5" fill="#4a4a4a"/>
  <text x="304" y="19" fill="#5a5a5a" font-size="10" letter-spacing="1" text-anchor="end">~/portrait.sh</text>

  <g transform="translate(0,{BAR})">
    <g clip-path="url(#frame)">
      <g class="reveal">
        <rect width="320" height="320" fill="#0a0a0a"/>

        <g class="jitter">
          <use xlink:href="#portrait" x="0" y="0" transform="translate(-10, 0) scale(1.08)"/>
        </g>

        <g clip-path="url(#inner)">
          <rect class="grainA" x="0" y="0" width="320" height="320" filter="url(#grain1)" opacity="0"/>
          <rect class="grainB" x="0" y="0" width="320" height="320" filter="url(#grain2)" opacity="0"/>

          <g>
            {particles}
          </g>

        </g>

        <rect x="0" y="292" width="320" height="28" fill="#0a0a0a" opacity="0.8"/>
      </g>
    </g>

    <rect class="glowRect" x="0.5" y="0.5" width="319" height="319" fill="none" stroke="#f5f5f5" stroke-width="2" filter="url(#borderGlow)" opacity="0"/>
    <rect class="borderMain" x="0.5" y="0.5" width="319" height="319" fill="none" stroke="#2a2a2a" stroke-width="1"/>

    <g clip-path="url(#capClip)">
      <text x="{CAPTION_X}" y="310" fill="#8a8a8a" font-size="10.5" letter-spacing="1"
            textLength="{CAPTION_BOX_WIDTH}" lengthAdjust="spacingAndGlyphs">{caption}</text>
    </g>
    <rect class="capCursor" x="{cursor_x}" y="299" width="2" height="12" fill="#f5f5f5"/>
  </g>

  <rect x="0.5" y="0.5" width="319" height="{H-1}" fill="none" stroke="#2a2a2a" stroke-width="1"/>
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
