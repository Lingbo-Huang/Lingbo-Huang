#!/usr/bin/env python3
"""Refresh the profile's activity card using only GitHub's API and stdlib.

GITHUB_TOKEN is the only credential source. No raw API response, repository
names, private contribution details, or credentials are written to disk.
The trend includes private counts the user has already chosen to share on
their GitHub profile. The commit/PR/issue breakdown is explicitly public.
API reference: https://docs.github.com/en/graphql/reference/users
"""

import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


LOGIN = "Lingbo-Huang"
ROOT = Path(__file__).resolve().parents[1]
QUERY = """
query ProfileActivity($login: String!, $trendFrom: DateTime!, $summaryFrom: DateTime!, $to: DateTime!) {
  user(login: $login) {
    trend: contributionsCollection(from: $trendFrom, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
    summary: contributionsCollection(from: $summaryFrom, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
      commitContributionsByRepository(maxRepositories: 100) {
        repository { visibility }
        contributions { totalCount }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { visibility }
        contributions { totalCount }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { visibility }
        contributions { totalCount }
      }
    }
  }
}
"""

PALETTES = {
    "light": {
        "bg": "#F3F7FC", "panel": "#FFFFFF", "stroke": "#D5E2F2",
        "ink": "#183350", "muted": "#526D8B", "accent": "#275DD7",
        "soft": "#DCE9FF", "teal": "#167A85", "grid": "#E2EBF5",
    },
    "dark": {
        "bg": "#101B2C", "panel": "#152338", "stroke": "#2A3D56",
        "ink": "#E4EEFC", "muted": "#A2B7D1", "accent": "#83ABFF",
        "soft": "#233B62", "teal": "#71D0CC", "grid": "#263950",
    },
}


def request_data(variables):
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN must be set; existing cards were preserved.")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{LOGIN}-profile-activity",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as error:
            if error.code in (429, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"GitHub API HTTP {error.code}; existing cards were preserved.") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError("GitHub API unavailable; existing cards were preserved.") from None
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        raise RuntimeError("GitHub GraphQL returned incomplete data; existing cards were preserved.")
    return payload["data"]["user"]


def daily_counts(collection, start, end):
    result = {}
    for week in collection["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            date = dt.date.fromisoformat(day["date"])
            if start <= date <= end:
                count = day["contributionCount"]
                if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                    raise ValueError("Invalid contribution count")
                result[date] = count
    expected = {start + dt.timedelta(days=i) for i in range((end - start).days + 1)}
    if set(result) != expected:
        raise ValueError("Incomplete daily contribution data")
    return result


def public_count(groups):
    # GraphQL's repository grouping is capped. Fail rather than publish a
    # silently truncated metric if the profile outgrows that API limit.
    if len(groups) >= 100:
        raise ValueError("Contribution repository limit reached")
    total = 0
    for group in groups:
        if group["repository"]["visibility"] == "PUBLIC":
            count = group["contributions"]["totalCount"]
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError("Invalid public contribution count")
            total += count
    return total


def render_card(data, updated, start, end, summary_start, theme, mobile=False):
    p = PALETTES[theme]
    trend = daily_counts(data["trend"], start, end)
    summary = daily_counts(data["summary"], summary_start, end)
    total = sum(summary.values())
    if total != data["summary"]["contributionCalendar"]["totalContributions"]:
        raise ValueError("Contribution total does not match daily data")
    commits = public_count(data["summary"]["commitContributionsByRepository"])
    prs = public_count(data["summary"]["pullRequestContributionsByRepository"])
    issues = public_count(data["summary"]["issueContributionsByRepository"])
    weekly = [sum(trend[start + dt.timedelta(days=i * 7 + j)] for j in range(7)) for i in range(13)]
    active_weeks = sum(count > 0 for count in weekly)
    scale = max(10, math.ceil(max(weekly) / 10) * 10)
    range_text = f"{start:%d %b} — {end:%d %b %Y}"
    description = (
        f"GitHub contribution activity for {LOGIN}. 13 weekly totals: {', '.join(map(str, weekly))}. "
        f"{active_weeks} active weeks out of 13. Last 90 complete UTC days: {total} contributions; "
        f"{commits} public commit contributions, {prs} public pull requests opened, "
        f"and {issues} public issues opened. The total includes shared private contribution counts. "
        f"Data through {end.isoformat()}, updated {updated.isoformat()} UTC."
    )
    if mobile:
        return render_mobile(p, updated, range_text, description, start, weekly, scale, total, active_weeks, commits, prs, issues)
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="432" viewBox="0 0 1200 432" fill="none" role="img" aria-labelledby="title desc">
  <title id="title">Lingbo-Huang · GitHub activity</title>
  <desc id="desc">{html.escape(description)}</desc>
  <rect x="0.5" y="0.5" width="1199" height="431" rx="22" fill="{p['bg']}" stroke="{p['stroke']}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <circle cx="39" cy="40" r="5" fill="{p['teal']}"/>
    <text x="53" y="46" fill="{p['muted']}" font-size="14" font-weight="600">Building, consistently</text>
    <text x="34" y="89" fill="{p['ink']}" font-size="30" font-weight="650" letter-spacing="-0.7">GitHub activity</text>
    <text x="1166" y="45" fill="{p['muted']}" font-size="13" text-anchor="end">Updated {updated.isoformat()} UTC</text>
    <text x="1166" y="83" fill="{p['muted']}" font-size="14" text-anchor="end">{html.escape(range_text)} · 13 weeks</text>
    <path d="M34 110H1166" stroke="{p['stroke']}"/>
    <text x="34" y="141" fill="{p['muted']}" font-size="13" font-weight="600">Weekly contributions</text>''']
    left, top, bottom, step, bar_width = 66, 177, 318, 45, 24
    for fraction in (0, 0.5, 1):
        y = bottom - (bottom - top) * fraction
        parts.append(f'<path d="M62 {y:g}H646" stroke="{p["grid"]}" stroke-dasharray="3 5"/>')
        parts.append(f'<text x="48" y="{y+4:g}" fill="{p["muted"]}" font-size="11" text-anchor="end">{scale*fraction:g}</text>')
    for i, value in enumerate(weekly):
        height = (bottom - top) * value / scale
        x = left + i * step
        week_start = start + dt.timedelta(days=i * 7)
        week_end = week_start + dt.timedelta(days=6)
        label = f"{week_start.isoformat()} to {week_end.isoformat()}: {value} contributions"
        # A zero is a baseline mark, not a fake positive-height bar.
        if value:
            fill = p["accent"] if i == 12 else p["teal"]
            parts.append(f'<rect x="{x}" y="{bottom-height:.2f}" width="{bar_width}" height="{height:.2f}" rx="4" fill="{fill}"><title>{label}</title></rect>')
            parts.append(f'<text x="{x+bar_width/2:g}" y="{bottom-height-9:.2f}" fill="{p["muted"]}" font-size="11" text-anchor="middle">{value}</text>')
        else:
            parts.append(f'<path d="M{x} {bottom}h{bar_width}" stroke="{p["stroke"]}" stroke-width="2"><title>{label}</title></path>')
        if i in (0, 4, 8, 12):
            parts.append(f'<text x="{x+bar_width/2:g}" y="344" fill="{p["muted"]}" font-size="12" text-anchor="middle">{week_start:%d %b}</text>')
    parts.append(f'''<path d="M685 133V351" stroke="{p['stroke']}"/>
    <text x="720" y="141" fill="{p['muted']}" font-size="13" font-weight="600">Activity snapshot</text>
    <text x="720" y="205" fill="{p['ink']}" font-size="48" font-weight="650" letter-spacing="-1.5">{total:,}</text>
    <text x="720" y="230" fill="{p['muted']}" font-size="14">contributions · 90 days</text>
    <text x="971" y="205" fill="{p['ink']}" font-size="48" font-weight="650" letter-spacing="-1.5">{active_weeks}</text>
    <text x="971" y="230" fill="{p['muted']}" font-size="14">active weeks · 13 weeks</text>
    <rect x="720" y="252" width="446" height="94" rx="13" fill="{p['panel']}" stroke="{p['stroke']}"/>
    <text x="739" y="277" fill="{p['muted']}" font-size="12">Public contributions · 90 days</text>
    <text x="739" y="309" fill="{p['accent']}" font-size="25" font-weight="650">{commits}</text>
    <text x="775" y="309" fill="{p['muted']}" font-size="13">commits</text>
    <text x="895" y="309" fill="{p['accent']}" font-size="25" font-weight="650">{prs}</text>
    <text x="928" y="309" fill="{p['muted']}" font-size="13">PRs</text>
    <text x="1032" y="309" fill="{p['accent']}" font-size="25" font-weight="650">{issues}</text>
    <text x="1067" y="309" fill="{p['muted']}" font-size="13">issues</text>
    <path d="M34 371H1166" stroke="{p['stroke']}"/>
    <text x="34" y="397" fill="{p['muted']}" font-size="12">Source: GitHub GraphQL · Totals include private counts shared on the profile; breakdown is public.</text>
    <text x="1166" y="397" fill="{p['muted']}" font-size="12" text-anchor="end">Complete UTC days · Updates daily</text>
  </g>
</svg>
''')
    return "\n".join(parts)


def render_mobile(p, updated, range_text, description, start, weekly, scale, total, active_weeks, commits, prs, issues):
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="740" viewBox="0 0 600 740" fill="none" role="img" aria-labelledby="title desc">
  <title id="title">Lingbo-Huang · GitHub activity</title>
  <desc id="desc">{html.escape(description)}</desc>
  <rect x="0.5" y="0.5" width="599" height="739" rx="22" fill="{p['bg']}" stroke="{p['stroke']}"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <circle cx="33" cy="34" r="5" fill="{p['teal']}"/>
    <text x="48" y="40" fill="{p['muted']}" font-size="18" font-weight="600">Building, consistently</text>
    <text x="28" y="85" fill="{p['ink']}" font-size="36" font-weight="650">GitHub activity</text>
    <text x="28" y="117" fill="{p['muted']}" font-size="18">{html.escape(range_text)} · 13 weeks</text>
    <path d="M28 139H572" stroke="{p['stroke']}"/>
    <text x="28" y="174" fill="{p['muted']}" font-size="18" font-weight="600">Weekly contributions</text>''']
    left, top, bottom, step, width = 62, 216, 359, 39, 23
    for fraction in (0, 0.5, 1):
        y = bottom - (bottom - top) * fraction
        parts.append(f'<path d="M58 {y:g}H562" stroke="{p["grid"]}" stroke-dasharray="3 5"/>')
        parts.append(f'<text x="46" y="{y+5:g}" fill="{p["muted"]}" font-size="16" text-anchor="end">{scale*fraction:g}</text>')
    for i, value in enumerate(weekly):
        height = (bottom - top) * value / scale
        x = left + i * step
        week_start = start + dt.timedelta(days=i * 7)
        label = f"{week_start.isoformat()}: {value} contributions in 7 days"
        if value:
            fill = p["accent"] if i == 12 else p["teal"]
            parts.append(f'<rect x="{x}" y="{bottom-height:.2f}" width="{width}" height="{height:.2f}" rx="4" fill="{fill}"><title>{label}</title></rect>')
        else:
            parts.append(f'<path d="M{x} {bottom}h{width}" stroke="{p["stroke"]}" stroke-width="2"><title>{label}</title></path>')
        if i in (0, 4, 8, 12):
            parts.append(f'<text x="{x+width/2:g}" y="389" fill="{p["muted"]}" font-size="17" text-anchor="middle">{week_start:%d %b}</text>')
    parts.append(f'''<path d="M28 415H572" stroke="{p['stroke']}"/>
    <text x="28" y="480" fill="{p['ink']}" font-size="48" font-weight="650">{total:,}</text>
    <text x="28" y="510" fill="{p['muted']}" font-size="19">contributions · 90 days</text>
    <text x="331" y="480" fill="{p['ink']}" font-size="48" font-weight="650">{active_weeks}</text>
    <text x="331" y="510" fill="{p['muted']}" font-size="19">active weeks · 13 weeks</text>
    <rect x="28" y="539" width="544" height="112" rx="14" fill="{p['panel']}" stroke="{p['stroke']}"/>
    <text x="48" y="567" fill="{p['muted']}" font-size="17">Public contributions · 90 days</text>
    <text x="48" y="606" fill="{p['accent']}" font-size="30" font-weight="650">{commits}</text>
    <text x="93" y="606" fill="{p['muted']}" font-size="18">commits</text>
    <text x="242" y="606" fill="{p['accent']}" font-size="30" font-weight="650">{prs}</text>
    <text x="280" y="606" fill="{p['muted']}" font-size="18">PRs</text>
    <text x="406" y="606" fill="{p['accent']}" font-size="30" font-weight="650">{issues}</text>
    <text x="444" y="606" fill="{p['muted']}" font-size="18">issues</text>
    <text x="28" y="684" fill="{p['muted']}" font-size="17">GitHub GraphQL · Includes shared private counts.</text>
    <text x="28" y="714" fill="{p['muted']}" font-size="16">Updated {updated.isoformat()} UTC · Complete days · Daily refresh</text>
  </g>
</svg>
''')
    return "\n".join(parts)


def main():
    # Exclude the partial current UTC day so each weekly bar is comparable.
    updated = dt.datetime.now(dt.timezone.utc).date()
    end = updated - dt.timedelta(days=1)
    start = end - dt.timedelta(days=90)
    summary_start = end - dt.timedelta(days=89)
    variables = {
        "login": LOGIN,
        "trendFrom": f"{start.isoformat()}T00:00:00Z",
        "summaryFrom": f"{summary_start.isoformat()}T00:00:00Z",
        "to": f"{end.isoformat()}T23:59:59Z",
    }
    data = request_data(variables)
    # Render and validate both before writing either. API failures preserve the
    # last successful cards rather than replace real data with zeroes.
    cards = {}
    for theme in PALETTES:
        cards[f"activity-{theme}"] = render_card(data, updated, start, end, summary_start, theme)
        cards[f"activity-mobile-{theme}"] = render_card(data, updated, start, end, summary_start, theme, mobile=True)
    assets = ROOT / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name, svg in cards.items():
        target = assets / f"{name}.svg"
        temporary = target.with_suffix(".svg.tmp")
        temporary.write_text(svg, encoding="utf-8")
        temporary.replace(target)
    print(f"Updated activity cards for {LOGIN}; data through {end.isoformat()} UTC.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, TypeError, OSError) as error:
        # Deliberately do not log raw responses, request headers, or tracebacks.
        message = str(error) if isinstance(error, RuntimeError) else "Invalid activity data or output error; existing cards were preserved."
        print(message, file=sys.stderr)
        sys.exit(1)
