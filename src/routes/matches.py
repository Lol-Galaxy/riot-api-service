from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
import httpx

from ..riot_client import get_match_ids, get_match, get_matches_bulk

router = APIRouter(prefix="/summoner", tags=["matches"])


def _require_key(x_riot_token: str | None) -> str:
    if not x_riot_token:
        raise HTTPException(status_code=401, detail="Header X-Riot-Token manquant.")
    return x_riot_token


@router.get("/{region}/{puuid}/matches")
async def matches_ids(
    region: str,
    puuid: str,
    count: int = Query(default=20, ge=1, le=100),
    queue: int | None = Query(default=None),
    end_time: int | None = Query(default=None),
    x_riot_token: str | None = Header(default=None),
):
    api_key = _require_key(x_riot_token)
    try:
        return await get_match_ids(puuid, region, api_key, count=count, queue=queue, end_time=end_time)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class BulkMatchRequest(BaseModel):
    match_ids: list[str]
    region: str


@router.post("/matches/bulk")
async def matches_bulk(
    body: BulkMatchRequest,
    x_riot_token: str | None = Header(default=None),
):
    api_key = _require_key(x_riot_token)
    if len(body.match_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 matchs par appel.")
    try:
        return await get_matches_bulk(body.match_ids, body.region, api_key)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
