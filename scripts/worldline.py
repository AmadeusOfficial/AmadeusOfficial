"""Worldline math, D-Mail parsing and rendering for the profile README."""

import copy
import hashlib
import html
import re
from datetime import datetime, timedelta

INITIAL_DIVERGENCE = "0.571024"
STEINS_GATE = "1.048596"
MAX_DMAIL_BYTES = 36
RATE_LIMIT = timedelta(hours=1)
HISTORY_SIZE = 5

FIELD_LABELS = {
    "alpha": "α Attractor Field",
    "beta": "β Attractor Field",
    "gamma": "γ Attractor Field",
    "steins_gate": "Steins;Gate",
}

_TITLE_RE = re.compile(r"^\s*d-?mail\s*[:：]\s*(.*)$", re.IGNORECASE | re.DOTALL)

_INLINE_ESCAPES = {
    "|": "&#124;",
    "[": "&#91;",
    "]": "&#93;",
    "`": "&#96;",
    "@": "&#64;",
    "*": "&#42;",
    "_": "&#95;",
}


def initial_state():
    return {
        "divergence": INITIAL_DIVERGENCE,
        "field": "alpha",
        "history": [],
        "last_sent": {},
    }


def parse_title(title):
    match = _TITLE_RE.match(title or "")
    if not match:
        return None
    return match.group(1).strip()


def truncate_bytes(text, limit=MAX_DMAIL_BYTES):
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    return encoded[:limit].decode("utf-8", errors="ignore")


def divergence_for(seed):
    """Map a seed to a divergence value; the attractor field depends on the roll."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    roll = int.from_bytes(digest[:4], "big") % 1000
    n = int.from_bytes(digest[4:8], "big")
    if roll < 8:
        return STEINS_GATE, "steins_gate"
    if roll < 500:
        return "0.%06d" % (300000 + n % 400000), "alpha"
    if roll < 950:
        return "1.%06d" % (100000 + n % 40000), "beta"
    return "2.%06d" % (600000 + n % 100000), "gamma"


def process(state, title, sender, number, now):
    """Apply one D-Mail. Returns (new_state, result); rejected mail leaves state untouched."""
    message = parse_title(title)
    if message is None:
        return state, {"accepted": False, "reason": "not_dmail"}
    message = truncate_bytes(message)
    if not message:
        return state, {"accepted": False, "reason": "empty"}

    last = state["last_sent"].get(sender)
    if last and now - datetime.fromisoformat(last) < RATE_LIMIT:
        retry_at = datetime.fromisoformat(last) + RATE_LIMIT
        return state, {"accepted": False, "reason": "rate_limited", "retry_at": retry_at.isoformat()}

    new_state = copy.deepcopy(state)
    before = state["divergence"]
    value, field = divergence_for(f"{number}|{sender}|{message}|{now.isoformat()}")
    entry = {
        "number": number,
        "sender": sender,
        "message": message,
        "from": before,
        "to": value,
        "field": field,
        "sent_at": now.isoformat(),
    }
    new_state["divergence"] = value
    new_state["field"] = field
    new_state["history"] = ([entry] + new_state["history"])[:HISTORY_SIZE]
    new_state["last_sent"][sender] = now.isoformat()
    return new_state, {"accepted": True, "from": before, "to": value, "field": field, "message": message}


def escape_inline(text):
    escaped = html.escape(text, quote=True)
    return "".join(_INLINE_ESCAPES.get(ch, ch) for ch in escaped)


def render_status(divergence, field):
    return f"**Current worldline:** `{divergence}` · {FIELD_LABELS[field]}"


def render_history(history):
    if not history:
        return "_No D-Mail has reached this worldline yet. Be the first to change the past._"
    rows = [
        "| Sent (UTC) | Sender | Message | Worldline shift |",
        "| --- | --- | --- | --- |",
    ]
    for entry in history:
        sent = datetime.fromisoformat(entry["sent_at"]).strftime("%Y-%m-%d %H:%M")
        rows.append(
            f"| {sent} | [@{entry['sender']}](https://github.com/{entry['sender']}) "
            f"| {escape_inline(entry['message'])} "
            f"| `{entry['from']}` → `{entry['to']}` |"
        )
    return "\n".join(rows)


def replace_block(text, marker, content):
    start = f"<!-- {marker}:START -->"
    end = f"<!-- {marker}:END -->"
    head, sep, rest = text.partition(start)
    if not sep:
        raise ValueError(f"missing {start}")
    _, sep, tail = rest.partition(end)
    if not sep:
        raise ValueError(f"missing {end}")
    return f"{head}{start}\n{content}\n{end}{tail}"


_TUBE_W = 64
_TUBE_H = 132
_TUBE_GAP = 10
_PAD_X = 40
_TUBE_Y = 36


def render_svg(divergence, field):
    """Draw the divergence meter as a row of nixie tubes."""
    glow = "#7CFFA4" if field == "steins_gate" else "#FF8C1A"
    width = _PAD_X * 2 + len(divergence) * _TUBE_W + (len(divergence) - 1) * _TUBE_GAP
    height = 230
    tubes = []
    for i, ch in enumerate(divergence):
        x = _PAD_X + i * (_TUBE_W + _TUBE_GAP)
        cx = x + _TUBE_W / 2
        ghost = "" if ch == "." else (
            f'<text x="{cx}" y="{_TUBE_Y + 98}" class="ghost">8</text>'
        )
        tubes.append(
            f'<g class="tube" style="animation-delay:{(i * 0.37) % 2.3:.2f}s">'
            f'<rect x="{x}" y="{_TUBE_Y}" width="{_TUBE_W}" height="{_TUBE_H}" rx="26" class="glass"/>'
            f'<rect x="{x + 6}" y="{_TUBE_Y + 6}" width="{_TUBE_W - 12}" height="10" rx="5" class="shine"/>'
            f"{ghost}"
            f'<text x="{cx}" y="{_TUBE_Y + 98}" class="digit" filter="url(#glow)">{ch}</text>'
            f'<rect x="{x + 8}" y="{_TUBE_Y + _TUBE_H}" width="{_TUBE_W - 16}" height="12" rx="3" class="base"/>'
            "</g>"
        )
    label = "".join(ch if ch in "αβγ" else ch.upper() for ch in FIELD_LABELS[field])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Divergence {divergence}, {label}">'
        "<defs>"
        '<linearGradient id="glassFill" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#2a2420"/><stop offset="1" stop-color="#0c0a09"/>'
        "</linearGradient>"
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="3.5" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
        "</defs>"
        "<style>"
        ".bg{fill:#0b0b0d}"
        ".glass{fill:url(#glassFill);stroke:#5a4b3c;stroke-width:1.5}"
        ".shine{fill:#ffffff;opacity:.06}"
        ".base{fill:#3a3027}"
        f".digit{{fill:{glow};font:700 72px 'Courier New',Consolas,monospace;text-anchor:middle}}"
        ".ghost{fill:#ffffff;opacity:.025;font:700 72px 'Courier New',Consolas,monospace;text-anchor:middle}"
        f".label{{fill:{glow};font:600 15px 'Courier New',Consolas,monospace;letter-spacing:4px;text-anchor:middle}}"
        ".tube{animation:flicker 4.2s infinite}"
        "@keyframes flicker{0%,92%,100%{opacity:1}93%{opacity:.72}95%{opacity:.95}97%{opacity:.8}}"
        "@media (prefers-reduced-motion:reduce){.tube{animation:none}}"
        "</style>"
        f'<rect width="{width}" height="{height}" rx="18" class="bg"/>'
        + "".join(tubes)
        + f'<text x="{width / 2}" y="{height - 20}" class="label">{html.escape(label)}</text>'
        "</svg>\n"
    )
