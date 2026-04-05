"""
Cache en mémoire pour les données statiques DDragon (champions).
TTL : 24h. Chargement lazy au premier appel.
"""

import time
import httpx

_DDRAGON_BASE = "https://ddragon.leagueoflegends.com"
_TTL = 86400  # 24h en secondes

_cache: dict = {}
_fetched_at: float = 0.0


async def _fetch_latest_version() -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_DDRAGON_BASE}/api/versions.json")
        resp.raise_for_status()
        return resp.json()[0]


async def _fetch_champions(version: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{_DDRAGON_BASE}/cdn/{version}/data/fr_FR/champion.json"
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def get_champion_data() -> dict:
    """
    Retourne les données DDragon champions (version + data).
    Rafraîchit automatiquement après 24h.
    """
    global _cache, _fetched_at

    if _cache and (time.monotonic() - _fetched_at) < _TTL:
        return _cache

    version = await _fetch_latest_version()
    data = await _fetch_champions(version)

    _cache = {
        "version": version,
        "champions": data.get("data", {}),
    }
    _fetched_at = time.monotonic()
    return _cache


def invalidate() -> None:
    """Force le rechargement au prochain appel (utile pour les tests)."""
    global _fetched_at
    _fetched_at = 0.0
