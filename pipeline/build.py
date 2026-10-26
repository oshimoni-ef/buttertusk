"""Fetch showtimes from the configured provider and build the site into dist/.

    python pipeline/build.py                      # provider from config.json (or SHOWTIMES_PROVIDER)
    python pipeline/build.py --provider seed      # force one

Writes dist/index.html (the page with data inlined) and dist/showtimes.json.
Exits non-zero, without writing anything, if the provider fails or returns bad data,
so a failed refresh leaves the last good site in place.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import providers  # noqa: E402
import schema  # noqa: E402
import zips  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "site" / "template.html"
DIST = ROOT / "dist"
SLOT = "/*@@DATA@@*/null"


def build(provider_name=None, config_path=None, dist=DIST):
    config = json.loads(Path(config_path or ROOT / "pipeline" / "config.json").read_text(encoding="utf-8"))
    name = provider_name or os.environ.get("SHOWTIMES_PROVIDER") or config["provider"]
    data = providers.get(name).fetch(config)

    try:
        data["zips"] = zips.near(config["centers"], config.get("zip_radius_mi", 45))
    except OSError as e:   # offline: keep what the provider sent, else the snapshot's short list
        print(f"zip download failed ({e}); using a fallback zip list", file=sys.stderr)
        data["zips"] = data.get("zips") or providers.get("seed").fetch(config)["zips"]
    data["meta"]["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
    data["meta"]["default_zip"] = config.get("default_zip")
    schema.validate(data)

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    if page.count(SLOT) != 1:
        raise RuntimeError(f"template must contain {SLOT} exactly once")
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(page.replace(SLOT, blob), encoding="utf-8")
    (dist / "showtimes.json").write_text(blob, encoding="utf-8")
    (dist / ".nojekyll").write_text("", encoding="utf-8")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", help="seed or internationalshowtimes (default: config / SHOWTIMES_PROVIDER)")
    ap.add_argument("--config", help="path to config.json")
    args = ap.parse_args()
    d = build(args.provider, args.config)
    print(f"{d['meta']['source']}: {len(d['cinemas'])} theaters, {len(d['films'])} movies, "
          f"{len(d['showings'])} showings, {len(d['zips'])} zips, {d['dates'][0]} to {d['dates'][-1]} -> dist/")
