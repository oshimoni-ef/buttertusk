"""The normalized showtimes shape every provider returns, and a check for it.

{
  "meta":     {"source": str, ...},
  "dates":    ["YYYY-MM-DD", ...],                       # days covered, in order
  "cinemas":  [{"name", "short", "town", "lat", "lng", "url", "page"}],
  "films":    [{"title", "rating", "runtime", "genres": [str]}],
  "showings": [[date, cinema_index, film_index, start_minutes, format, link, access_flags]],
  "zips":     {"01701": [lat, lng], ...}                 # added by build.py
}

start_minutes is minutes past local midnight at the theater. format is "" for a standard
showing, else a short label such as "IMAX" or "Open caption". access_flags is any of
"C" (closed captions), "A" (accessibility devices), "O" (open captions).
"""
import re

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SchemaError(ValueError):
    pass


def validate(data):
    """Raise SchemaError if data doesn't match the shape above. Returns data for chaining."""
    for key in ("meta", "dates", "cinemas", "films", "showings"):
        if key not in data:
            raise SchemaError(f"missing '{key}'")
    if not data["dates"] or not all(DATE_RE.match(d) for d in data["dates"]):
        raise SchemaError("dates must be a non-empty list of YYYY-MM-DD")
    for i, c in enumerate(data["cinemas"]):
        if not c.get("name") or not isinstance(c.get("lat"), (int, float)) or not isinstance(c.get("lng"), (int, float)):
            raise SchemaError(f"cinema {i} needs name, lat and lng")
    for i, f in enumerate(data["films"]):
        if not f.get("title"):
            raise SchemaError(f"film {i} needs a title")
    dates, nc, nf = set(data["dates"]), len(data["cinemas"]), len(data["films"])
    for i, s in enumerate(data["showings"]):
        if len(s) != 7:
            raise SchemaError(f"showing {i} must have 7 fields, has {len(s)}")
        date, ci, fi, start = s[:4]
        if date not in dates or not (0 <= ci < nc) or not (0 <= fi < nf) or not (0 <= start < 1440 + 360):
            raise SchemaError(f"showing {i} is out of range: {s[:4]}")
    if not data["showings"]:
        raise SchemaError("no showings")
    return data
