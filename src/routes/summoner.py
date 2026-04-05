import asyncio

from fastapi import APIRouter, Header, HTTPException
import httpx

from ..riot_client import (
    get_account_by_riot_id,
    get_summoner_by_puuid,
    get_ranked_by_puuid,
    get_mastery_by_puuid,
)

router = APIRouter(prefix="/summoner", tags=["summoner"])


def _require_key(x_riot_token: str | None) -> str:
    if not x_riot_token:
        raise HTTPException(status_code=401, detail="Header X-Riot-Token manquant.")
    return x_riot_token


@router.get("/{region}/{game_name}/{tag_line}")
async def summoner_by_riot_id(
    region: str,
    game_name: str,
    tag_line: str,
    x_riot_token: str | None = Header(default=None),
):
    """
    Résout gameName#tagLine → PUUID + summoner + ranked + top 50 masteries.
    Requiert le header X-Riot-Token avec la clé Riot de l'app appelante.
    """
    api_key = _require_key(x_riot_token)
    try:
        account = await get_account_by_riot_id(game_name, tag_line, region, api_key)
        puuid = account["puuid"]

        summoner, ranked, mastery = await asyncio.gather(
            get_summoner_by_puuid(puuid, region, api_key),
            get_ranked_by_puuid(puuid, region, api_key),
            get_mastery_by_puuid(puuid, region, api_key, count=50),
        )

        return {
            "puuid": puuid,
            "gameName": account.get("gameName", game_name),
            "tagLine": account.get("tagLine", tag_line),
            "summonerId": summoner.get("id"),
            "summonerLevel": summoner.get("summonerLevel"),
            "profileIconId": summoner.get("profileIconId"),
            "ranked": ranked,
            "mastery": mastery,
        }
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{region}/{puuid}/rank")
async def summoner_rank(
    region: str,
    puuid: str,
    x_riot_token: str | None = Header(default=None),
):
    api_key = _require_key(x_riot_token)
    try:
        return await get_ranked_by_puuid(puuid, region, api_key)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{region}/{puuid}/mastery")
async def summoner_mastery(
    region: str,
    puuid: str,
    count: int = 20,
    x_riot_token: str | None = Header(default=None),
):
    api_key = _require_key(x_riot_token)
    try:
        return await get_mastery_by_puuid(puuid, region, api_key, count=min(count, 50))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
