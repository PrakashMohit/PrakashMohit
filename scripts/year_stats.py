#!/usr/bin/env python3
"""
Generate a "Contributions in <current year>" card for the profile README.

Reads the contribution calendar straight from GitHub's GraphQL API for
Jan 1 .. today of the current year, so the numbers match what the profile page
shows for that year (including private contributions *if* the profile setting
"Include private contributions on my profile" is on).

Writes assets/year-stats.svg.
Standard library only. Needs GITHUB_TOKEN (or GH_TOKEN) in the environment.
"""

import calendar
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("PROFILE_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "PrakashMohit"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
OUT_DIR = Path(__file__).resolve().parent.parent / "assets"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

# One self-contained dark card (own background + border). It reads well on both GitHub
# themes, so the README needs no fragile light/dark <picture> switching.
THEME = dict(
    bg="#0d1117", border="#30363d", title="#e6edf3", muted="#8b949e", value="#e6edf3",
    accent="#58a6ff", tile="#161b22", future="#161b22",
    levels=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
)
LEVEL_INDEX = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def fetch(year: int, now: datetime) -> dict:
    if not TOKEN:
        sys.exit("GITHUB_TOKEN (or GH_TOKEN) is not set")
    variables = {
        "login": USER,
        "from": f"{year}-01-01T00:00:00Z",
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "year-stats"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        sys.exit(f"GraphQL error: {payload.get('errors') or 'user not found'}")
    return payload["data"]["user"]["contributionsCollection"]


def summarise(collection: dict, year: int, today: date) -> dict:
    days = {}
    for week in collection["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"])
            if d.year == year and d <= today:
                days[d] = (day["contributionCount"], LEVEL_INDEX.get(day["contributionLevel"], 0))

    # the calendar lists every day, so consecutive entries are consecutive dates
    longest = run = 0
    for d in sorted(days):
        run = run + 1 if days[d][0] > 0 else 0
        longest = max(longest, run)

    # current streak: walk back from today (today may still be empty, so start from yesterday then)
    cursor = today if days.get(today, (0, 0))[0] > 0 else today - timedelta(days=1)
    current = 0
    while days.get(cursor, (0, 0))[0] > 0:
        current += 1
        cursor -= timedelta(days=1)

    return dict(
        days=days,
        total=sum(count for count, _ in days.values()),
        active_days=sum(1 for count, _ in days.values() if count > 0),
        commits=collection["totalCommitContributions"],
        prs=collection["totalPullRequestContributions"],
        reviews=collection["totalPullRequestReviewContributions"],
        issues=collection["totalIssueContributions"],
        private=collection["restrictedContributionsCount"],
        longest=longest,
        current=current,
    )


def render(year: int, today: date, s: dict) -> str:
    c = THEME
    width, pad = 880, 28
    cell, gap = 12, 3
    pitch = cell + gap

    # heatmap geometry: Sunday-first weeks across the whole calendar year
    jan1, dec31 = date(year, 1, 1), date(year, 12, 31)
    first_col_start = jan1 - timedelta(days=(jan1.weekday() + 1) % 7)   # Sunday on/before Jan 1
    weeks = ((dec31 - first_col_start).days // 7) + 1
    grid_w = weeks * pitch - gap
    grid_x = pad + 30
    grid_y = 196

    tiles = [
        (f"{s['total']:,}", "CONTRIBUTIONS"),
        (f"{s['commits']:,}", "COMMITS"),
        (f"{s['prs']:,}", "PULL REQUESTS"),
        (f"{s['active_days']:,}", "ACTIVE DAYS"),
        (f"{s['current']:,}", "CURRENT STREAK"),
        (f"{s['longest']:,}", "LONGEST STREAK"),
    ]
    tile_w = (width - 2 * pad - 5 * 10) / 6
    parts = []
    for i, (value, label) in enumerate(tiles):
        x = pad + i * (tile_w + 10)
        accent = c["accent"] if i == 0 else c["value"]
        parts.append(
            f'<rect x="{x:.1f}" y="70" width="{tile_w:.1f}" height="84" rx="10" fill="{c["tile"]}" stroke="{c["border"]}"/>'
            f'<text x="{x + 16:.1f}" y="112" font-size="30" font-weight="600" fill="{accent}">{value}</text>'
            f'<text x="{x + 16:.1f}" y="136" font-size="10" letter-spacing="0.6" fill="{c["muted"]}">{escape(label)}</text>'
        )

    # month labels + cells
    last_month = 0
    for w in range(weeks):
        col_start = first_col_start + timedelta(days=7 * w)
        x = grid_x + w * pitch
        for r in range(7):
            d = col_start + timedelta(days=r)
            if d.year != year:
                continue
            if d > today:
                fill, opacity, title = c["future"], "0.55", ""
            else:
                count, level = s["days"].get(d, (0, 0))
                fill, opacity = c["levels"][level], "1"
                title = f"{count} contribution{'s' if count != 1 else ''} on {d.strftime('%b')} {d.day}"
            parts.append(
                f'<rect x="{x}" y="{grid_y + r * pitch}" width="{cell}" height="{cell}" rx="3" fill="{fill}" '
                f'opacity="{opacity}">' + (f"<title>{escape(title)}</title>" if title else "") + "</rect>"
            )
        month_day = next((col_start + timedelta(days=i) for i in range(7)
                          if (col_start + timedelta(days=i)).year == year
                          and (col_start + timedelta(days=i)).month != last_month
                          and (col_start + timedelta(days=i)).day <= 7), None)
        if month_day and (w == 0 or month_day.month != last_month):
            parts.append(f'<text x="{x}" y="{grid_y - 10}" font-size="10" fill="{c["muted"]}">{calendar.month_abbr[month_day.month]}</text>')
            last_month = month_day.month

    for r, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="{pad}" y="{grid_y + r * pitch + 10}" font-size="10" fill="{c["muted"]}">{label}</text>')

    legend_y = grid_y + 7 * pitch + 22
    legend_x = pad + 30 + grid_w - (5 * pitch + 78)
    parts.append(f'<text x="{legend_x}" y="{legend_y + 10}" font-size="10" fill="{c["muted"]}">Less</text>')
    for i, colour in enumerate(c["levels"]):
        parts.append(f'<rect x="{legend_x + 30 + i * pitch}" y="{legend_y}" width="{cell}" height="{cell}" rx="3" fill="{colour}"/>')
    parts.append(f'<text x="{legend_x + 30 + 5 * pitch + 4}" y="{legend_y + 10}" font-size="10" fill="{c["muted"]}">More</text>')

    note = f"Jan 1 – {today.strftime('%b')} {today.day}, {year}  ·  updated automatically"
    if s["private"]:
        note += f"  ·  includes {s['private']:,} private"
    height = legend_y + 40

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{FONT}" role="img" aria-label="{USER} contributions in {year}: {s["total"]}">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f'<text x="{pad}" y="38" font-size="17" font-weight="600" fill="{c["title"]}">Contributions in {year}</text>'
        f'<text x="{pad}" y="56" font-size="11" fill="{c["muted"]}">{escape(note)}</text>'
        + "".join(parts) + "</svg>\n"
    )


def main() -> None:
    now = datetime.now(timezone.utc)
    year, today = now.year, now.date()
    summary = summarise(fetch(year, now), year, today)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "year-stats.svg").write_text(render(year, today, summary), encoding="utf-8", newline="\n")
    print(f"{USER} {year}: {summary['total']} contributions, {summary['commits']} commits, "
          f"{summary['prs']} PRs, {summary['active_days']} active days, "
          f"streak {summary['current']} (longest {summary['longest']}), private {summary['private']}")


if __name__ == "__main__":
    main()
