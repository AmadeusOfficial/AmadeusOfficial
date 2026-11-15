"""Entry point for the D-Mail GitHub Action and for re-rendering the profile."""

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from scripts import worldline

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = Path("state") / "worldline.json"
SVG_PATH = Path("assets") / "divergence-meter.svg"
README_PATH = Path("README.md")


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_state(root):
    path = root / STATE_PATH
    if not path.exists():
        return worldline.initial_state()
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(root, state):
    path = root / STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_all(root, state):
    svg = root / SVG_PATH
    svg.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text(worldline.render_svg(state["divergence"], state["field"]), encoding="utf-8")

    readme = root / README_PATH
    text = readme.read_text(encoding="utf-8")
    text = worldline.replace_block(text, "WORLDLINE", worldline.render_status(state["divergence"], state["field"]))
    text = worldline.replace_block(text, "DMAIL", worldline.render_history(state["history"]))
    readme.write_text(text, encoding="utf-8")


def build_reply(result):
    if result["accepted"]:
        lines = [
            "📨 **D-Mail received.**",
            "",
            f"> {worldline.escape_inline(result['message'])}",
            "",
            f"Worldline shifted: `{result['from']}` → `{result['to']}` · {worldline.FIELD_LABELS[result['field']]}",
        ]
        if result["field"] == "steins_gate":
            lines += ["", "🎉 **You reached the Steins;Gate worldline** — a future no one has observed yet."]
        lines += ["", "The profile has been rewritten. El Psy Kongroo."]
        return "\n".join(lines)

    reason = result["reason"]
    if reason == "empty":
        return "⚠️ The D-Mail is empty. Write your message after `D-Mail:` in the issue title."
    if reason == "rate_limited":
        retry = parse_time(result["retry_at"]).strftime("%Y-%m-%d %H:%M")
        return f"⏳ The PhoneWave is still cooling down. You can send your next D-Mail after {retry} UTC."
    return "⚠️ This doesn't look like a D-Mail. Use a title such as `D-Mail: your message`."


def run(root, title, sender, number, now):
    state, result = worldline.process(load_state(root), title, sender, number, now)
    if result["accepted"]:
        save_state(root, state)
        render_all(root, state)
    return result, build_reply(result)


def write_outputs(result, reply):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        print(reply)
        return
    delimiter = f"EOF_{uuid.uuid4().hex}"
    with open(path, "a", encoding="utf-8") as out:
        out.write(f"accepted={'true' if result['accepted'] else 'false'}\n")
        out.write(f"from={result.get('from', '')}\n")
        out.write(f"to={result.get('to', '')}\n")
        out.write(f"reply<<{delimiter}\n{reply}\n{delimiter}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only", action="store_true", help="rebuild SVG and README from the saved state")
    args = parser.parse_args(argv)

    if args.render_only:
        render_all(ROOT, load_state(ROOT))
        return

    result, reply = run(
        ROOT,
        os.environ["ISSUE_TITLE"],
        os.environ["ISSUE_USER"],
        int(os.environ["ISSUE_NUMBER"]),
        parse_time(os.environ["ISSUE_CREATED_AT"]),
    )
    write_outputs(result, reply)


if __name__ == "__main__":
    main()
