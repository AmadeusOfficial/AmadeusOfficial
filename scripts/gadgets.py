"""Render the Future Gadget Lab project cards as SVG."""

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "gadgets"

LANGUAGE_COLORS = {
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "Java": "#b07219",
    "CSS": "#663399",
}

GADGETS = [
    {
        "slug": "cursor-board",
        "name": "Cursor Board",
        "desc": "AI 研发流水线看板：贴一张任务卡，开发、测试、提交、部署自动跑完。",
        "language": "JavaScript",
    },
    {
        "slug": "excel-process",
        "name": "Excel Process",
        "desc": "面向财务人员的 Excel 批量处理工具。",
        "language": "Python",
    },
    {
        "slug": "amadeus-blog",
        "name": "Amadeus Blog",
        "desc": "个人博客，记录这条世界线上的实验笔记。建设中。",
        "language": "CSS",
    },
]

_WIDTH = 860
_HEIGHT = 128
_MONO = "'Courier New',Consolas,monospace"
_SANS = "'PingFang SC','Microsoft YaHei','Noto Sans CJK SC','Segoe UI',sans-serif"


def card_filename(index, gadget):
    return f"{index:02d}-{gadget['slug']}.svg"


def render_card(index, gadget):
    name = html.escape(gadget["name"])
    desc = html.escape(gadget["desc"])
    language = html.escape(gadget["language"])
    dot = LANGUAGE_COLORS.get(gadget["language"], "#8b949e")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_WIDTH}" height="{_HEIGHT}" '
        f'viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" aria-label="Future Gadget No.{index:02d} {name}">'
        "<defs>"
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="3" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#ffffff" opacity=".025"/>'
        "</pattern>"
        '<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#FF8C1A" stop-opacity=".9"/>'
        '<stop offset="1" stop-color="#FF8C1A" stop-opacity="0"/>'
        "</linearGradient>"
        "</defs>"
        "<style>"
        f".no{{fill:#FF8C1A;font:700 52px {_MONO};text-anchor:middle}}"
        f".nolabel{{fill:#8a7562;font:600 11px {_MONO};letter-spacing:3px;text-anchor:middle}}"
        f".tag{{fill:#FF8C1A;font:600 12px {_SANS};letter-spacing:2px}}"
        f".name{{fill:#f3e9dc;font:700 26px {_SANS}}}"
        f".desc{{fill:#b5a594;font:400 16px {_SANS}}}"
        f".lang{{fill:#b5a594;font:500 13px {_SANS}}}"
        "</style>"
        f'<rect x="1" y="1" width="{_WIDTH - 2}" height="{_HEIGHT - 2}" rx="16" fill="#0b0b0d" stroke="#3a2f25" stroke-width="1.5"/>'
        f'<rect x="1" y="1" width="{_WIDTH - 2}" height="{_HEIGHT - 2}" rx="16" fill="url(#scan)"/>'
        f'<rect x="24" y="1" width="320" height="2" fill="url(#edge)"/>'
        '<text x="80" y="42" class="nolabel">NO.</text>'
        f'<text x="80" y="96" class="no" filter="url(#glow)">{index:02d}</text>'
        f'<line x1="148" y1="26" x2="148" y2="{_HEIGHT - 26}" stroke="#3a2f25" stroke-width="1.5"/>'
        f'<text x="176" y="40" class="tag">未来ガジェット {index}号機</text>'
        f'<text x="176" y="74" class="name">{name}</text>'
        f'<text x="176" y="104" class="desc">{desc}</text>'
        f'<circle cx="{_WIDTH - 132}" cy="36.5" r="5.5" fill="{dot}"/>'
        f'<text x="{_WIDTH - 120}" y="41" class="lang">{language}</text>'
        "</svg>\n"
    )


def render_all(out_dir=OUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, gadget in enumerate(GADGETS, start=1):
        path = out_dir / card_filename(index, gadget)
        path.write_text(render_card(index, gadget), encoding="utf-8")
        paths.append(path)
    return paths


if __name__ == "__main__":
    for path in render_all():
        print(path.relative_to(ROOT))
