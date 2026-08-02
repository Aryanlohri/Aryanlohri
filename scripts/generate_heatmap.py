#!/usr/bin/env python3
"""
Generates contrib-heatmap.svg from live GitHub contribution data.
Run manually (needs GH_TOKEN env var) or via the scheduled workflow,
which supplies GITHUB_TOKEN automatically.
"""

import os
import sys
import json
import urllib.request

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
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level_color(count):
    # monochrome scale, matches the dark/grey palette used site-wide
    if count == 0:
        return "#161616"
    if count < 3:
        return "#3a3a3a"
    if count < 6:
        return "#666666"
    if count < 10:
        return "#a0a0a0"
    return "#f5f5f5"


def render_svg(calendar):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    cell = 11
    gap = 3
    left_pad = 28
    top_pad = 40
    width = left_pad + len(weeks) * (cell + gap) + 10
    height = top_pad + 7 * (cell + gap) + 20

    svg = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="\'JetBrains Mono\',monospace">',
        f'<rect width="{width}" height="{height}" fill="#0a0a0a"/>',
        f'<text x="{left_pad}" y="20" fill="#8a8a8a" font-size="11" letter-spacing="2">'
        f'{total} CONTRIBUTIONS IN THE LAST YEAR</text>',
    ]

    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            x = left_pad + wi * (cell + gap)
            y = top_pad + di * (cell + gap)
            color = level_color(day["contributionCount"])
            svg.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{color}"><title>{day["date"]}: {day["contributionCount"]}</title></rect>'
            )

    svg.append("</svg>")
    return "\n".join(svg)


def placeholder_svg():
    # used if no token is available (e.g. local test run) so the file
    # still renders something sensible instead of failing
    return render_svg({
        "totalContributions": 0,
        "weeks": [{"contributionDays": [{"date": "", "contributionCount": 0} for _ in range(7)]} for _ in range(53)],
    })


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("No token found, writing placeholder heatmap.", file=sys.stderr)
        svg = placeholder_svg()
    else:
        calendar = fetch_contributions(token)
        svg = render_svg(calendar)

    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
