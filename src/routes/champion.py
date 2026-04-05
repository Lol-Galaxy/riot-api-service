from fastapi import APIRouter, HTTPException

from ..ddragon_cache import get_champion_data, invalidate

router = APIRouter(prefix="/champion", tags=["champion"])


@router.get("/static")
async def champion_static():
    """
    Données statiques DDragon : version du patch + tous les champions.
    Cache mémoire 24h, rechargement automatique.
    """
    try:
        return await get_champion_data()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur DDragon : {e}")


@router.post("/static/invalidate")
async def champion_static_invalidate():
    """Force le rechargement du cache DDragon au prochain appel."""
    invalidate()
    return {"status": "cache invalidé"}
