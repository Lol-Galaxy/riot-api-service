from fastapi import APIRouter, Header, HTTPException
import httpx

from ..riot_client import get_match

router = APIRouter(prefix="/match", tags=["match"])


def _require_key(x_riot_token: str | None) -> str:
    if not x_riot_token:
        raise HTTPException(status_code=401, detail="Header X-Riot-Token manquant.")
    return x_riot_token


@router.get("/{region}/{match_id}")
async def match_detail(
    region: str,
    match_id: str,
    x_riot_token: str | None = Header(default=None),
):
    api_key = _require_key(x_riot_token)
    try:
        return await get_match(match_id, region, api_key)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
