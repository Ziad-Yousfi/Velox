"""
Inline SVG icons for the Gaming Launcher.
Using embedded SVG strings avoids file I/O and large PNG assets.
All icons are 24x24 viewBox, stroke-based for crisp rendering at any size.
"""

# ── Helper ─────────────────────────────────────────────────────────────

def colorize(svg: str, color: str) -> str:
    """Replace the placeholder stroke/fill color in an SVG string."""
    return svg.replace("{COLOR}", color)


# ── Icon SVG Templates ─────────────────────────────────────────────────

ICON_PLUS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <line x1="12" y1="5" x2="12" y2="19"/>
  <line x1="5" y1="12" x2="19" y2="12"/>
</svg>"""

ICON_PLAY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="{COLOR}" stroke="none">
  <polygon points="6,4 20,12 6,20"/>
</svg>"""

ICON_INFO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <line x1="12" y1="16" x2="12" y2="12"/>
  <line x1="12" y1="8" x2="12.01" y2="8"/>
</svg>"""

ICON_SETTINGS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0
    0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33
    1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65
    1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2
    2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68
    15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65
    1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2
    2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65
    1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0
    0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1
    2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0
    0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
</svg>"""

ICON_CLOSE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <line x1="18" y1="6" x2="6" y2="18"/>
  <line x1="6" y1="6" x2="18" y2="18"/>
</svg>"""

ICON_MINIMIZE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <line x1="5" y1="12" x2="19" y2="12"/>
</svg>"""

ICON_MAXIMIZE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
</svg>"""

ICON_ARROW_LEFT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <polyline points="15 18 9 12 15 6"/>
</svg>"""

ICON_ARROW_RIGHT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <polyline points="9 18 15 12 9 6"/>
</svg>"""

ICON_DELETE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"/>
  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4
    a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
</svg>"""

ICON_STOP = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="{COLOR}" stroke="none">
  <rect x="6" y="6" width="12" height="12" rx="1"/>
</svg>"""

ICON_GAMEPAD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="1.5"
  stroke-linecap="round" stroke-linejoin="round">
  <line x1="6" y1="12" x2="10" y2="12"/>
  <line x1="8" y1="10" x2="8" y2="14"/>
  <line x1="15" y1="13" x2="15.01" y2="13"/>
  <line x1="18" y1="11" x2="18.01" y2="11"/>
  <rect x="2" y="6" width="20" height="12" rx="5" ry="5"/>
</svg>"""

ICON_FOLDER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0
    0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
</svg>"""

ICON_IMAGE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="{COLOR}" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
  <circle cx="8.5" cy="8.5" r="1.5"/>
  <polyline points="21 15 16 10 5 21"/>
</svg>"""
