"""The one-time snapshot in pipeline/seed/snapshot.json. Free and offline, but it never changes,
so use it for development or until a live provider is set up."""
import json
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "seed" / "snapshot.json"


def fetch(config):
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
