"""
Client HTTP asynchrone vers l'API Riot Games.
La clé API est passée par l'appelant (header X-Riot-Token) — le service est stateless.
Rate limiting par clé : chaque app a son propre compteur (19 req/s, 95 req/2min).
"""

import asyncio
import time
import httpx

# ---------------------------------------------------------------------------
# Routing Riot API
# ---------------------------------------------------------------------------

PLATFORM_MAP: dict[str, str] = {
    "EUW1": "euw1", "EUN1": "eun1", "TR1": "tr1", "RU": "ru", "ME1": "me1",
    "NA1": "na1", "BR1": "br1", "LA1": "la1", "LA2": "la2",
    "KR": "kr", "JP1": "jp1",
    "OC1": "oc1", "SG2": "sg2", "TH2": "th2", "TW2": "tw2", "VN2": "vn2",
}

REGIONAL_MAP: dict[str, str] = {
    "EUW1": "europe", "EUN1": "europe", "TR1": "europe", "RU": "europe", "ME1": "europe",
    "NA1": "americas", "BR1": "americas", "LA1": "americas", "LA2": "americas",
    "KR": "asia", "JP1": "asia",
    "OC1": "sea", "SG2": "sea", "TH2": "sea", "TW2": "sea", "VN2": "sea",
}


def platform_host(region: str) -> str:
    key = region.upper()
    if key not in PLATFORM_MAP:
        raise ValueError(f"Région inconnue : {region}")
    return f"https://{PLATFORM_MAP[key]}.api.riotgames.com"


def regional_host(region: str) -> str:
    key = region.upper()
    if key not in REGIONAL_MAP:
        raise ValueError(f"Région inconnue : {region}")
    return f"https://{REGIONAL_MAP[key]}.api.riotgames.com"


# ---------------------------------------------------------------------------
# Rate limiter par clé API
# ---------------------------------------------------------------------------

class RateLimiter:
    """Double fenêtre glissante : 19 req/s et 95 req/2min."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._timestamps: list[float] = []

    async def acquire(self) -> None:
        # Lock released during sleep so other coroutines can check — no deadlock on large batches
        while True:
            wait = 0.0
            async with self._lock:
                now = time.monotonic()
                self._timestamps = [t for t in self._timestamps if now - t < 120.0]

                in_short = sum(1 for t in self._timestamps if now - t < 1.0)
                in_long = len(self._timestamps)

                if in_short < 19 and in_long < 95:
                    self._timestamps.append(now)
                    return  # slot acquired, lock released

                if in_short >= 19:
                    oldest = sorted(t for t in self._timestamps if now - t < 1.0)[0]
                    wait = 1.0 - (now - oldest)
                else:
                    wait = 120.0 - (now - sorted(self._timestamps)[0])

            # Sleep OUTSIDE the lock so other tasks can try concurrently
            await asyncio.sleep(max(wait, 0.05))


# Un RateLimiter par clé API (chaque app a le sien)
_limiters: dict[str, RateLimiter] = {}
_limiters_lock = asyncio.Lock()


async def _get_limiter(api_key: str) -> RateLimiter:
    async with _limiters_lock:
        if api_key not in _limiters:
            _limiters[api_key] = RateLimiter()
        return _limiters[api_key]


# ---------------------------------------------------------------------------
# Client HTTP
# ---------------------------------------------------------------------------

_TIMEOUT = httpx.Timeout(10.0)
_MAX_RETRIES = 3


async def riot_get(url: str, api_key: str) -> dict | list:
    limiter = await _get_limiter(api_key)
    headers = {"X-Riot-Token": api_key}

    for attempt in range(_MAX_RETRIES):
        await limiter.acquire()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            await asyncio.sleep(retry_after + 0.5)
            continue

        if resp.status_code >= 500 and attempt < _MAX_RETRIES - 1:
            await asyncio.sleep(2 ** attempt)
            continue

        resp.raise_for_status()

    raise RuntimeError(f"Échec après {_MAX_RETRIES} tentatives : {url}")


# ---------------------------------------------------------------------------
# Appels Riot API
# ---------------------------------------------------------------------------

async def get_account_by_riot_id(game_name: str, tag_line: str, region: str, api_key: str) -> dict:
    host = regional_host(region)
    url = f"{host}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    return await riot_get(url, api_key)  # type: ignore[return-value]


async def get_summoner_by_puuid(puuid: str, region: str, api_key: str) -> dict:
    host = platform_host(region)
    url = f"{host}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    return await riot_get(url, api_key)  # type: ignore[return-value]


async def get_ranked_by_puuid(puuid: str, region: str, api_key: str) -> list[dict]:
    host = platform_host(region)
    url = f"{host}/lol/league/v4/entries/by-puuid/{puuid}"
    return await riot_get(url, api_key)  # type: ignore[return-value]


async def get_mastery_by_puuid(puuid: str, region: str, api_key: str, count: int = 50) -> list[dict]:
    host = platform_host(region)
    url = f"{host}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={count}"
    return await riot_get(url, api_key)  # type: ignore[return-value]


async def get_match_ids(
    puuid: str,
    region: str,
    api_key: str,
    count: int = 20,
    queue: int | None = None,
    end_time: int | None = None,
) -> list[str]:
    host = regional_host(region)
    params = f"start=0&count={count}"
    if queue is not None:
        params += f"&queue={queue}"
    if end_time is not None:
        params += f"&endTime={end_time}"
    url = f"{host}/lol/match/v5/matches/by-puuid/{puuid}/ids?{params}"
    return await riot_get(url, api_key)  # type: ignore[return-value]


async def get_match(match_id: str, region: str, api_key: str) -> dict:
    host = regional_host(region)
    url = f"{host}/lol/match/v5/matches/{match_id}"
    return await riot_get(url, api_key)  # type: ignore[return-value]


async def get_matches_bulk(match_ids: list[str], region: str, api_key: str) -> list[dict]:
    tasks = [get_match(mid, region, api_key) for mid in match_ids]
    return await asyncio.gather(*tasks)
