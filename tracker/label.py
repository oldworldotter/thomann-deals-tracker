"""Prints the last check's time (as stored in data/state.json), for the commit message."""
import json
from pathlib import Path

import yaml

from .report import human_ts, set_display_tz

root = Path(__file__).resolve().parent.parent
try:
    set_display_tz(yaml.safe_load((root / "config.yml").read_text(encoding="utf-8")) or {})
    print(human_ts(json.loads((root / "data" / "state.json").read_text())["last_result"]["ts"]))
except Exception:
    print("(time unknown)")
