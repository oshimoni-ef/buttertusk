"""Showtimes providers. Each module exposes fetch(config) -> normalized dict (see schema.py)."""
from . import internationalshowtimes, seed

PROVIDERS = {"seed": seed, "internationalshowtimes": internationalshowtimes}


def get(name):
    if name not in PROVIDERS:
        raise ValueError(f"unknown provider '{name}'; choose one of {', '.join(PROVIDERS)}")
    return PROVIDERS[name]
