"""Zip code centers for the covered area, from the US Census ZCTA gazetteer (public domain).

The site measures "within N miles" from the center of the visitor's zip, so it needs a center
for every zip they might type. The national file is ~33,000 zips; only those near the
configured centers are kept, which keeps the page small.
"""
import io
import math
import urllib.request
import zipfile
from pathlib import Path

GAZETTEER = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_zcta_national.zip"
CACHE = Path(__file__).resolve().parent / ".cache" / "zcta.txt"


def miles(a, b):
    r = math.radians
    h = math.sin(r(b[0] - a[0]) / 2) ** 2 + math.cos(r(a[0])) * math.cos(r(b[0])) * math.sin(r(b[1] - a[1]) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def _load():
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(GAZETTEER, timeout=120) as resp:
            z = zipfile.ZipFile(io.BytesIO(resp.read()))
            CACHE.write_bytes(z.read(z.namelist()[0]))
    rows = {}
    lines = CACHE.read_text(encoding="utf-8").splitlines()
    head = [h.strip() for h in lines[0].split("\t")]
    gi, lat, lng = head.index("GEOID"), head.index("INTPTLAT"), head.index("INTPTLONG")
    for line in lines[1:]:
        f = line.split("\t")
        rows[f[gi].strip()] = [round(float(f[lat]), 4), round(float(f[lng]), 4)]
    return rows


def near(centers, radius_mi):
    """{zip: [lat, lng]} for every zip within radius_mi of any center."""
    pts = [(c["lat"], c["lng"]) for c in centers]
    return {z: ll for z, ll in _load().items() if any(miles(ll, p) <= radius_mi for p in pts)}
