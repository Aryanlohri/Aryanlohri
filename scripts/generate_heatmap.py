#!/usr/bin/env python3
"""
Generates contrib-heatmap.svg from live GitHub contribution data, styled
as an animated GitHub-green heatmap (diagonal pop-in + flash).
Needs GH_TOKEN (fine-grained PAT, read:user) since the contribution
calendar is only exposed via the authenticated GraphQL API, even for
public profiles.
"""

import os
import sys
import json
import random
import urllib.request
from datetime import date, timedelta

USERNAME = "Aryanlohri"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "contrib-heatmap.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

COL_EMPTY = "#161b22"
LEVELS = ["#0e4429", "#006d32", "#26a641", "#39d353"]

CELL = 13
GAP = 3
STEP = CELL + GAP
LEFT_PAD = 34
TOP_PAD = 24
BOTTOM_SPACE = 26
COL_DELAY = 0.065
ROW_DELAY = 0.036

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}


def fetch_contributions(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME,
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level_color(count):
    if count == 0:
        return COL_EMPTY
    if count <= 2:
        return LEVELS[0]
    if count <= 5:
        return LEVELS[1]
    if count <= 9:
        return LEVELS[2]
    return LEVELS[3]


def render_svg(calendar):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    width = LEFT_PAD + len(weeks) * STEP + 9
    height = TOP_PAD + 6 * STEP + CELL + BOTTOM_SPACE

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="\'JetBrains Mono\',Consolas,monospace">',
        "<style>",
        "  text.lbl { fill:#7d8590; font-size:11px; font-weight:600; }",
        "  text.total { fill:#e6edf3; font-size:13px; font-weight:700; }",
        "  .c { transform-box:fill-box; transform-origin:center; opacity:0; animation:pop 0.55s ease-out both; }",
        "  .g { animation:pop 0.55s ease-out both, flash 0.7s ease-out both; }",
        "  @keyframes pop { 0%{opacity:0;transform:scale(.2)} 60%{opacity:1;transform:scale(1.1)} 100%{opacity:1;transform:scale(1)} }",
        "  @keyframes flash { 0%{filter:brightness(2.4)} 45%{filter:brightness(2.4)} 100%{filter:brightness(1)} }",
        "  @media (prefers-reduced-motion: reduce) { .c { opacity:1 !important; animation:none !important; } }",
        "</style>",
        f'<rect width="{width}" height="{height}" fill="#0a0a0a"/>',
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" fill="none" stroke="#2a2a2a"/>',
    ]

    prev_month = None
    for wi, week in enumerate(weeks):
        d = week["contributionDays"][0]["date"]
        m = int(d.split("-")[1])
        if m != prev_month:
            x = LEFT_PAD + wi * STEP
            parts.append(f'<text class="lbl" x="{x}" y="16">{MONTHS[m-1]}</text>')
            prev_month = m

    for row, label in WEEKDAY_LABELS.items():
        y = TOP_PAD + row * STEP + 11
        parts.append(f'<text class="lbl" x="2" y="{y}">{label}</text>')

    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]
            x = LEFT_PAD + wi * STEP
            y = TOP_PAD + di * STEP
            color = level_color(count)
            cls = "c e" if count == 0 else "c g"
            delay = round(wi * COL_DELAY + di * ROW_DELAY, 3)
            parts.append(
                f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2.5" fill="{color}" style="animation-delay:{delay}s"/>'
            )

    total_y = height - 6
    parts.append(f'<text class="total" x="{LEFT_PAD}" y="{total_y}">{total:,} contributions in the last year</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def synthetic_calendar():
    """
    Fallback so the file still renders something sensible before the
    workflow's first authenticated run. Modeled loosely on a working
    student dev: heavier on weekdays, quiet weekends, a couple of
    multi-week dead zones (exams), and a few high-intensity streaks
    (project pushes) rather than uniform noise.
    """
    random.seed(11)
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7 * 52 + (6 - today.weekday()))
    start -= timedelta(days=(start.weekday() + 1) % 7)

    total_days = 53 * 7
    all_days = [start + timedelta(days=i) for i in range(total_days)]

    # a few quiet stretches (exam season / breaks), ~10-18 days each
    quiet_zones = []
    for _ in range(3):
        zone_start = random.randint(0, total_days - 20)
        zone_len = random.randint(10, 18)
        quiet_zones.append(range(zone_start, zone_start + zone_len))

    # a few high-intensity streaks (shipping something), ~4-8 days each
    hot_zones = []
    for _ in range(4):
        zone_start = random.randint(0, total_days - 10)
        zone_len = random.randint(4, 8)
        hot_zones.append(range(zone_start, zone_start + zone_len))

    def in_any(i, zones):
        return any(i in z for z in zones)

    weeks = []
    total = 0
    idx = 0
    for _ in range(53):
        days = []
        for _ in range(7):
            d = all_days[idx]
            if d > today:
                count = 0
            elif in_any(idx, quiet_zones):
                count = 0 if random.random() < 0.75 else 1
            else:
                is_weekend = d.weekday() >= 5
                base = 1.6 if is_weekend else 3.4
                if in_any(idx, hot_zones):
                    base += 6
                # skip-day chance keeps it looking human, not a daily streak
                skip_chance = 0.5 if is_weekend else 0.22
                count = 0 if random.random() < skip_chance else max(0, round(random.gauss(base, 2.2)))
            total += count
            days.append({"date": d.isoformat(), "contributionCount": count})
            idx += 1
        weeks.append({"contributionDays": days})

    return {"totalContributions": total, "weeks": weeks}


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("No GH_TOKEN set — writing a synthetic preview heatmap.", file=sys.stderr)
        calendar = synthetic_calendar()
    else:
        calendar = fetch_contributions(token)

    svg = render_svg(calendar)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT_PATH} ({calendar['totalContributions']} contributions)")


if __name__ == "__main__":
    main()
