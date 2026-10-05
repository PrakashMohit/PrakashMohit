#!/usr/bin/env python3
"""
Build the static profile cards: assets/hero.svg, assets/experience.svg, assets/stack.svg.

Run it by hand when the wording or the tool list changes (needs internet once, to
fetch the monochrome brand marks from simple-icons, which are CC0):

    python scripts/build_cards.py

The contributions card is separate: scripts/year_stats.py (refreshed by the Action).
Standard library only.
"""

import re
import urllib.request
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

BG, BORDER, TILE = "#0d1117", "#30363d", "#161b22"
TITLE, TEXT, MUTED, ACCENT = "#e6edf3", "#c9d1d9", "#8b949e", "#58a6ff"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

# Experience boxes, shown side by side. "period" and "lines" are optional; add them and
# re-run the script (a box grows to fit, and both boxes stay the same height).
EXPERIENCE = [
    dict(
        role="Research Intern",
        org=["Department of Computer Science", "IIT Madras"],
        period=None,
        lines=[],
    ),
    dict(
        role="Industry Interaction and placement systems",
        org=["IIT Madras"],
        period=None,
        lines=[
            "Finding opportunities and scraping job posts",
            "Data cleaning and AI-based extraction",
            "Keeping track of recruiter contacts",
            "Placement dashboards and an AI interviewer",
        ],
    ),
]

# name shown -> simple-icons slug (None = plain text chip, no mark)
STACK = [
    ("Focus", [
        ("LLMs", None), ("VLMs", None), ("RAG", None), ("Agents", None), ("vLLM", None),
    ]),
    ("AI & ML", [
        ("PyTorch", "pytorch"), ("TensorFlow", "tensorflow"), ("OpenCV", "opencv"), ("NVIDIA", "nvidia"),
        ("Ollama", "ollama"), ("pandas", "pandas"),
    ]),
    ("Languages", [
        ("Python", "python"), ("C++", "cplusplus"), ("JavaScript", "javascript"), ("HTML", "html5"), ("CSS", "css"),
    ]),
    ("Web & data", [
        ("Flask", "flask"), ("FastAPI", "fastapi"), ("React", "react"), ("Vue", "vuedotjs"),
        ("SQLite", "sqlite"), ("PostgreSQL", "postgresql"), ("Supabase", "supabase"),
    ]),
    ("Tooling", [
        ("Docker", "docker"), ("Linux", "linux"), ("Git", "git"), ("GitHub", "github"),
        ("Selenium", "selenium"), ("Figma", "figma"),
    ]),
]


def icon_path(slug: str) -> str:
    request = urllib.request.Request(f"https://cdn.simpleicons.org/{slug}/ffffff", headers={"User-Agent": "Mozilla/5.0"})
    svg = urllib.request.urlopen(request, timeout=30).read().decode("utf-8")
    match = re.search(r'<path[^>]*\sd="([^"]+)"', svg)
    if not match:
        raise SystemExit(f"no path found for icon '{slug}'")
    return match.group(1)


def text_width(text: str, size: float, mono: bool = False) -> float:
    return len(text) * size * (0.6 if mono else 0.56)


def wrap(text: str, size: float, max_width: float) -> list:
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        # running text is narrower than the chip-sizing estimate in text_width(); 0.52em
        # still leaves a margin for wider fonts (Helvetica, SF) on other systems
        if current and len(trial) * size * 0.52 > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    return lines + [current] if current else lines


def experience() -> str:
    width, gap, pad = 880, 24, 26
    box_w = (width - gap) / 2
    inner = box_w - 2 * pad

    # lay out each box once to learn how tall it needs to be
    laid_out, tallest = [], 0
    for item in EXPERIENCE:
        rows, y = [], 66
        for line in wrap(item["role"], 17, inner):
            rows.append(("title", y, line))
            y += 24
        y -= 2
        for line in item["org"]:
            rows.append(("org", y + 14, line))
            y += 20
        if item.get("period"):
            rows.append(("period", y + 14, item["period"]))
            y += 20
        if item["lines"]:
            y += 10
        for bullet in item["lines"]:
            for n, part in enumerate(wrap(bullet, 13, inner - 18)):
                rows.append(("dot" if n == 0 else "cont", y + 15, part))
                y += 20
            y += 4
        laid_out.append(rows)
        tallest = max(tallest, y)
    height = tallest + 30

    parts = []
    for index, rows in enumerate(laid_out):
        x = index * (box_w + gap)
        parts.append(f'<rect x="{x + 0.5:.1f}" y="0.5" width="{box_w - 1:.1f}" height="{height - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>')
        parts.append(f'<text x="{x + box_w - pad:.1f}" y="40" font-family="{MONO}" font-size="12" text-anchor="end" fill="{BORDER}">0{index + 1}</text>')
        parts.append(f'<rect x="{x + pad:.1f}" y="28" width="22" height="3" rx="1.5" fill="{ACCENT}"/>')
        for kind, y, text in rows:
            tx = x + pad
            if kind == "title":
                parts.append(f'<text x="{tx:.1f}" y="{y}" font-size="17" font-weight="600" fill="{TITLE}">{escape(text)}</text>')
            elif kind in ("org", "period"):
                parts.append(f'<text x="{tx:.1f}" y="{y}" font-size="13" fill="{MUTED}">{escape(text)}</text>')
            elif kind == "dot":
                parts.append(f'<circle cx="{tx + 3:.1f}" cy="{y - 4.5}" r="2.5" fill="{ACCENT}"/>'
                             f'<text x="{tx + 16:.1f}" y="{y}" font-size="13" fill="{TEXT}">{escape(text)}</text>')
            else:
                parts.append(f'<text x="{tx + 16:.1f}" y="{y}" font-size="13" fill="{TEXT}">{escape(text)}</text>')
    summary = "; ".join(
        item["role"] + ", " + ", ".join(item["org"]) + (": " + "; ".join(item["lines"]) if item["lines"] else "")
        for item in EXPERIENCE)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'font-family="{SANS}" role="img" aria-label="Experience. {escape(summary)}.">' + "".join(parts) + "</svg>\n")


def hero() -> str:
    width, height, pad = 880, 270, 48
    headline = "I can make it "
    chips = ["LLMs", "Agents", "Computer vision", "Robotics"]
    chip_svg, x = [], pad
    for label in chips:
        w = text_width(label, 12) + 26
        chip_svg.append(
            f'<rect x="{x:.1f}" y="206" width="{w:.1f}" height="28" rx="14" fill="none" stroke="{BORDER}"/>'
            f'<text x="{x + w / 2:.1f}" y="224.5" font-size="12" text-anchor="middle" fill="{MUTED}">{escape(label)}</text>'
        )
        x += w + 10
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{SANS}" role="img" aria-label="Prakash Mohit. I can make it happen. A confused yet learning polymath in Prayagraj, India.">
  <defs>
    <radialGradient id="glow" cx="0.88" cy="0.05" r="0.75">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity="0.20"/>
      <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="#ffffff" fill-opacity="0.06"/>
    </pattern>
    <style>
      @keyframes blink {{ 50% {{ fill-opacity: 0; }} }}
      .cur {{ animation: blink 1.1s step-end infinite; }}
    </style>
  </defs>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="url(#grid)"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="url(#glow)"/>
  <text x="{pad}" y="62" font-size="12" font-weight="600" letter-spacing="3" fill="{ACCENT}">PRAKASH MOHIT</text>
  <text x="{width - pad}" y="62" font-size="12" text-anchor="end" fill="{MUTED}">Prayagraj, India</text>
  <text x="{pad}" y="142" font-family="{MONO}" font-size="46" font-weight="600" fill="{TITLE}" xml:space="preserve">{escape(headline)}<tspan fill="{ACCENT}">happen.</tspan><tspan class="cur" fill="{ACCENT}">_</tspan></text>
  <text x="{pad}" y="182" font-size="17" fill="{MUTED}">A confused yet learning polymath.</text>
  {"".join(chip_svg)}
</svg>
'''


def stack() -> str:
    width, pad, label_w = 880, 28, 112
    chip_h, gap, row_gap, group_gap = 30, 8, 8, 18
    x0 = pad + label_w
    right = width - pad
    parts, y = [], 78
    cache = {}
    for group, items in STACK:
        parts.append(f'<text x="{pad}" y="{y + 20}" font-size="11" font-weight="600" letter-spacing="1" fill="{MUTED}">{escape(group.upper())}</text>')
        x = x0
        for name, slug in items:
            w = text_width(name, 13) + (46 if slug else 28)
            if x + w > right:
                x, y = x0, y + chip_h + row_gap
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{chip_h}" rx="8" fill="{TILE}" stroke="{BORDER}"/>')
            if slug:
                cache.setdefault(slug, icon_path(slug))
                parts.append(f'<g transform="translate({x + 11:.1f},{y + 7})"><path transform="scale(0.667)" d="{cache[slug]}" fill="{TEXT}"/></g>')
                tx = x + 34
            else:
                tx = x + 14
            fill = TEXT if slug else ACCENT
            parts.append(f'<text x="{tx:.1f}" y="{y + 19.5}" font-size="13" fill="{fill}">{escape(name)}</text>')
            x += w + gap
        y += chip_h + group_gap
    height = y + 4
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{SANS}" role="img" aria-label="Tools I build with: focus areas, AI and machine learning, languages, web and data, tooling.">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>
  <text x="{pad}" y="38" font-size="17" font-weight="600" fill="{TITLE}">What I build with</text>
  <text x="{pad}" y="56" font-size="11" fill="{MUTED}">Grouped by what I use them for</text>
  {"".join(parts)}
</svg>
'''


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "hero.svg").write_text(hero(), encoding="utf-8", newline="\n")
    (OUT / "experience.svg").write_text(experience(), encoding="utf-8", newline="\n")
    (OUT / "stack.svg").write_text(stack(), encoding="utf-8", newline="\n")
    print("wrote assets/hero.svg, assets/experience.svg and assets/stack.svg")


if __name__ == "__main__":
    main()
