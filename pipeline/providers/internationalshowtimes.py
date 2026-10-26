"""International Showtimes API (internationalshowtimes.com). Needs ISHOWTIMES_API_KEY.

UNTESTED against the live API: written from the public v4 docs (showtimes searched by
location and distance, with movies and cinemas appended). Run `python pipeline/build.py
--provider internationalshowtimes` once with a trial key and adjust normalize() if a field
name differs. normalize() is unit-tested with a fixture in test_pipeline.py.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

PER_PAGE = 500
LANGS = {"es": "Spanish", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "ko": "Korean", "ja": "Japanese", "zh": "Mandarin",
         "fr": "French", "pt": "Portuguese", "ne": "Nepali", "mr": "Marathi"}


def _get(base, path, params, key):
    url = f"{base}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-API-Key": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch(config):
    key = os.environ.get("ISHOWTIMES_API_KEY")
    if not key:
        raise RuntimeError("ISHOWTIMES_API_KEY is not set")
    opts = config.get("providers", {}).get("internationalshowtimes", {})
    base = opts.get("base_url", "https://api.internationalshowtimes.com/v4").rstrip("/")
    start = date.today()
    end = start + timedelta(days=config.get("days", 7))
    raw = {"showtimes": [], "movies": [], "cinemas": []}
    for center in config["centers"]:
        page = 1
        while True:
            body = _get(base, "showtimes", {
                "location": f"{center['lat']},{center['lng']}",
                "distance": round(config.get("radius_mi", 25) * 1.609),   # km
                "time_from": f"{start.isoformat()}T05:00:00",
                "time_to": f"{end.isoformat()}T05:00:00",
                "append": "movies,cinemas",
                "per_page": PER_PAGE,
                "page": page,
            }, key)
            for k in raw:
                raw[k].extend(body.get(k, []))
            if len(body.get("showtimes", [])) < PER_PAGE:
                break
            page += 1
    return normalize(raw, start, config.get("days", 7))


def _rating(movie):
    lim = movie.get("age_limits") or movie.get("age_limit") or {}
    if isinstance(lim, dict):
        return lim.get("US") or next(iter(lim.values()), "NR")
    return lim or "NR"


def _format(st):
    tags = []
    if st.get("is_imax"):
        tags.append("IMAX")
    if st.get("is_3d"):
        tags.append("3D")
    lang = (st.get("language") or "").split("-")[0]
    if lang and lang != "en":
        tags.append(LANGS.get(lang, lang.upper()))
    return " ".join(tags)


def normalize(raw, start, days):
    """Turn the API's showtimes/movies/cinemas into the shape in schema.py."""
    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    movies = {str(m["id"]): m for m in raw["movies"]}
    cinemas_raw = {str(c["id"]): c for c in raw["cinemas"]}
    cinemas, films, cidx, fidx, seen, showings = [], [], {}, {}, set(), []
    for st in raw["showtimes"]:
        cid, mid = str(st.get("cinema_id")), str(st.get("movie_id"))
        if cid not in cinemas_raw or mid not in movies or not st.get("start_at"):
            continue
        local = datetime.fromisoformat(st["start_at"].replace("Z", "+00:00"))   # keeps the theater's own offset
        day, minutes = local.date(), local.hour * 60 + local.minute
        if minutes < 5 * 60:                       # after-midnight shows belong to the evening before
            day, minutes = day - timedelta(days=1), minutes + 1440
        if day.isoformat() not in dates:
            continue
        if cid not in cidx:
            c = cinemas_raw[cid]
            loc = c.get("location", {})
            cidx[cid] = len(cinemas)
            cinemas.append({"name": c.get("name", "Cinema"), "short": c.get("name", "Cinema"),
                            "town": (loc.get("address") or {}).get("city", ""), "lat": loc.get("lat"), "lng": loc.get("lon"),
                            "url": c.get("website"), "page": c.get("website")})
        if mid not in fidx:
            m = movies[mid]
            fidx[mid] = len(films)
            films.append({"title": m.get("title") or m.get("original_title") or "Untitled", "rating": _rating(m),
                          "runtime": m.get("runtime"), "genres": [g.get("name", g) if isinstance(g, dict) else g for g in m.get("genres", [])]})
        row = [day.isoformat(), cidx[cid], fidx[mid], minutes, _format(st), st.get("booking_link") or "", ""]
        key = tuple(row[:5])
        if key not in seen:
            seen.add(key)
            showings.append(row)
    return {"meta": {"source": "International Showtimes"}, "dates": dates, "cinemas": cinemas, "films": films, "showings": showings}
